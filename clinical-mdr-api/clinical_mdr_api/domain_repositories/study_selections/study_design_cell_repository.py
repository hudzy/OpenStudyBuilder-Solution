import datetime
from dataclasses import dataclass
from typing import List, Optional, Sequence

from neomodel import db

from clinical_mdr_api import exceptions
from clinical_mdr_api.domain_repositories._utils import helpers
from clinical_mdr_api.domain_repositories.models._utils import (
    convert_to_datetime,
    to_relation_trees,
)
from clinical_mdr_api.domain_repositories.models.generic import ClinicalMdrNodeWithUID
from clinical_mdr_api.domain_repositories.models.study import (
    StudyArm,
    StudyBranchArm,
    StudyElement,
    StudyRoot,
    StudyValue,
)
from clinical_mdr_api.domain_repositories.models.study_audit_trail import (
    Create,
    Delete,
    Edit,
)
from clinical_mdr_api.domain_repositories.models.study_epoch import StudyEpoch
from clinical_mdr_api.domain_repositories.models.study_selections import StudyDesignCell
from clinical_mdr_api.domains.study_selections.study_design_cell import (
    StudyDesignCellVO,
)


@dataclass
class StudyDesignCellHistory:
    """Class for selection history items"""

    study_selection_uid: str
    study_uid: str
    study_arm_uid: str
    study_branch_arm_uid: str
    study_epoch_uid: str
    study_element_uid: str
    user_initials: str
    change_type: str
    start_date: datetime.datetime
    end_date: Optional[datetime.datetime]
    transition_rule: str
    order: int


class StudyDesignCellRepository:
    @staticmethod
    def _acquire_write_lock_study_value(uid: str) -> None:
        db.cypher_query(
            """
                MATCH (sr:StudyRoot {uid: $uid})
                REMOVE sr.__WRITE_LOCK__
                RETURN true
            """,
            {"uid": uid},
        )

    def find_by_uid(self, study_uid: str, uid: str) -> StudyDesignCellVO:
        unique_design_cells = to_relation_trees(
            StudyDesignCell.nodes.fetch_relations(
                "study_epoch__has_epoch__has_name_root__has_latest_value",
                "has_after",
                "study_epoch",
            )
            .fetch_optional_relations(
                "study_arm__study_value",
                "study_branch_arm__study_value",
                "study_element__study_value",
            )
            .filter(
                study_value__study_root__uid=study_uid,
                study_epoch__study_value__study_root__uid=study_uid,
                uid=uid,
            )
            .order_by("order")
        ).distinct()
        if len(unique_design_cells) > 1:
            raise ValueError(
                f"Found more than one StudyDesignCell node with uid='{uid}' in the study='{study_uid}'."
            )
        if len(unique_design_cells) == 0:
            raise ValueError(
                f"The StudyDesignCell with uid='{uid}' could not be found in the study='{study_uid}'."
            )
        return self._from_repository_values(
            study_uid=study_uid, design_cell=unique_design_cells[0]
        )

    def find_all_design_cells_by_study(
        self, study_uid: str
    ) -> Sequence[StudyDesignCellVO]:
        all_design_cells = [
            self._from_repository_values(study_uid=study_uid, design_cell=sas_node)
            for sas_node in to_relation_trees(
                StudyDesignCell.nodes.fetch_relations(
                    "study_epoch__has_epoch__has_name_root__has_latest_value",
                    "has_after",
                    "study_epoch__study_value",
                )
                .fetch_optional_relations(
                    "study_arm__study_value",
                    "study_branch_arm__study_value",
                    "study_element__study_value",
                )
                .filter(study_value__study_root__uid=study_uid)
                .order_by("order")
            ).distinct()
        ]
        return all_design_cells

    def _from_repository_values(
        self, study_uid: str, design_cell: StudyDesignCell
    ) -> StudyDesignCellVO:
        study_action = design_cell.has_after.all()[0]
        study_arm = design_cell.study_arm.single()
        # get study_branch_arms that has study_value
        study_branch_arms = list(
            filter(
                lambda x: x.study_value.get_or_none(),
                design_cell.study_branch_arm.all(),
            )
        )
        if len(study_branch_arms) < 2:
            study_branch_arm = (
                study_branch_arms.pop() if len(study_branch_arms) > 0 else None
            )
        else:
            raise exceptions.BusinessLogicException(
                "Returned multiple branch arms with study_value rel "
            )
        study_epochs = list(
            filter(
                lambda x: x.study_value.get_or_none(),
                design_cell.study_epoch.all(),
            )
        )
        if len(study_epochs) < 2:  # check if it returns multiple values
            study_epoch = study_epochs.pop() if len(study_epochs) > 0 else None
        else:
            raise exceptions.BusinessLogicException(
                "Returned multiple branch arms with study_value rel "
            )
        # study_epoch = design_cell.study_epoch.single()
        study_epoch_name = (
            study_epoch.has_epoch.single()
            .has_name_root.single()
            .has_latest_value.single()
            .name
        )
        study_elements = list(
            filter(
                lambda x: x.study_value.get_or_none(),
                design_cell.study_element.all(),
            )
        )
        if len(study_elements) < 2:  # check if it returns multiple values
            study_element = study_elements.pop() if len(study_elements) > 0 else None
        else:
            raise exceptions.BusinessLogicException(
                "Returned multiple branch arms with study_value rel "
            )
        return StudyDesignCellVO(
            uid=design_cell.uid,
            study_uid=study_uid,
            order=design_cell.order,
            study_arm_uid=study_arm.uid if study_arm is not None else None,
            study_arm_name=study_arm.name if study_arm is not None else None,
            study_branch_arm_uid=study_branch_arm.uid
            if study_branch_arm is not None
            else None,
            study_branch_arm_name=study_branch_arm.name
            if study_branch_arm is not None
            else None,
            study_epoch_uid=study_epoch.uid,
            study_epoch_name=study_epoch_name,
            study_element_uid=study_element.uid,
            study_element_name=study_element.name,
            transition_rule=design_cell.transition_rule,
            start_date=study_action.date,
            user_initials=study_action.user_initials,
        )

    def get_current_outbound_node(
        self,
        node: ClinicalMdrNodeWithUID,
        outbound_rel_name: str,
        study_value_rel_name: str = "study_value",
    ):
        outbound_node = None
        outbound_nodes = getattr(node, outbound_rel_name).all()
        for i_outbound_node in outbound_nodes:
            # if the i_branch_arm is an actual one then carry it to the new node
            if getattr(i_outbound_node, study_value_rel_name).get_or_none() is not None:
                outbound_node = i_outbound_node
        return outbound_node

    # pylint: disable=unused-argument
    def save(
        self,
        design_cell_vo: StudyDesignCellVO,
        author: str,
        create: bool = False,
        allow_none_arm_branch_arm=False,
    ) -> StudyDesignCellVO:
        # Get nodes and check if they can play together
        study_root_node: StudyRoot = StudyRoot.nodes.get_or_none(
            uid=design_cell_vo.study_uid
        )
        if study_root_node is None:
            raise exceptions.NotFoundException(
                f"The study with uid {design_cell_vo.study_uid} was not found"
            )
        latest_study_value_node: StudyValue = study_root_node.latest_value.single()

        # check if something has changed
        if not create:
            # get the previous item
            previous_item: StudyDesignCell = (
                latest_study_value_node.has_study_design_cell.get_or_none(
                    uid=design_cell_vo.uid
                )
            )
            previous_study_epoch: StudyEpoch = self.get_current_outbound_node(
                node=previous_item, outbound_rel_name="study_epoch"
            )
            previous_study_arm: StudyArm = self.get_current_outbound_node(
                node=previous_item, outbound_rel_name="study_arm"
            )
            previous_study_branch_arm: StudyBranchArm = self.get_current_outbound_node(
                node=previous_item, outbound_rel_name="study_branch_arm"
            )
            previous_study_element: StudyElement = self.get_current_outbound_node(
                node=previous_item, outbound_rel_name="study_element"
            )
            to_compare_previous = [
                previous_study_arm.uid
                if not previous_study_branch_arm and previous_study_arm
                else None,
                previous_study_branch_arm.uid if previous_study_branch_arm else None,
                previous_study_epoch.uid if previous_study_epoch else None,
                previous_study_element.uid if previous_study_element else None,
                previous_item.transition_rule,
                previous_item.order,
            ]
            to_compare_post = list(
                map(
                    design_cell_vo.__dict__.get,
                    [
                        "study_arm_uid",
                        "study_branch_arm_uid",
                        "study_epoch_uid",
                        "study_element_uid",
                        "transition_rule",
                        "order",
                    ],
                )
            )

            if (
                not previous_study_arm
                and not previous_study_branch_arm
                and not allow_none_arm_branch_arm
            ):
                raise exceptions.BusinessLogicException(
                    "Broken Existing Design Cell without Arm and BranchArm"
                )
            # check if there's something to change
            if to_compare_previous == to_compare_post:
                return self._from_repository_values(
                    design_cell_vo.study_uid, previous_item
                )

        # check if the study_arm has StudyBranchArms assigned to it
        # get StudyArm only if it's necessary
        if design_cell_vo.study_arm_uid:
            study_arm_node: StudyArm = (
                latest_study_value_node.has_study_arm.get_or_none(
                    uid=design_cell_vo.study_arm_uid
                )
            )
            # if any StudyBranchArms connectect to StudyArm has a study_value
            if (
                sum(
                    i_branch_arm.study_value.all() != []
                    for i_branch_arm in study_arm_node.has_branch_arm.all()
                )
                > 0
            ):
                raise exceptions.BusinessLogicException(
                    f"The Study Arm with uid {study_arm_node.uid} cannot be "
                    "assigned to a Study Design Cell because it has Study Branch Arms assigned to it"
                )
        else:
            study_arm_node = None

        # get StudyBranchArm only if it's necessary
        if design_cell_vo.study_branch_arm_uid:
            study_branch_arm_node = (
                latest_study_value_node.has_study_branch_arm.get_or_none(
                    uid=design_cell_vo.study_branch_arm_uid
                )
            )
        else:
            study_branch_arm_node = None

        # at least one of the two has to be defined
        if study_arm_node is None and study_branch_arm_node is None:
            raise exceptions.NotFoundException(
                f"The study arm {design_cell_vo.study_arm_uid} or the Study Branch Arm {design_cell_vo.study_branch_arm_uid} must exist"
            )

        # get StudyEpoch
        study_epoch_node = latest_study_value_node.has_study_epoch.get_or_none(
            uid=design_cell_vo.study_epoch_uid
        )
        if study_epoch_node is None:
            raise exceptions.NotFoundException(
                f"The study epoch with uid {design_cell_vo.study_epoch_uid} was not found"
            )

        # get StudyElement
        if design_cell_vo.study_element_uid is not None:
            study_element_node = latest_study_value_node.has_study_element.get_or_none(
                uid=design_cell_vo.study_element_uid
            )
            if study_element_node is None:
                raise exceptions.NotFoundException(
                    f"The study element with uid {design_cell_vo.study_element_uid} was not found"
                )
        # Create new node
        design_cell = StudyDesignCell(
            uid=design_cell_vo.uid,
            transition_rule=design_cell_vo.transition_rule,
            order=design_cell_vo.order,
        )
        design_cell.save()

        # Create relations
        # ensure switching
        #       study_branch_arm was defined even if the arm was specified will be connected to study branch arm
        if study_branch_arm_node is not None:
            design_cell.study_branch_arm.connect(study_branch_arm_node)
        #       just arm was defined
        else:
            design_cell.study_arm.connect(study_arm_node)
        design_cell.study_epoch.connect(study_epoch_node)
        design_cell.study_element.connect(study_element_node)

        if create:
            self.manage_versioning_create(
                study_root=study_root_node,
                study_design_cell=design_cell_vo,
                new_item=design_cell,
            )
        else:
            self.manage_versioning_update(
                study_root=study_root_node,
                study_design_cell=design_cell_vo,
                previous_item=previous_item,
                new_item=design_cell,
            )
            self.manage_previous_outbound_relationships(
                previous_item=previous_item,
                latest_study_value_node=latest_study_value_node,
            )

        # check if the new cell already exists
        all_existing = self.get_design_cells_connected_to_epoch(
            design_cell_vo.study_uid, design_cell_vo.study_epoch_uid
        )
        for existing in all_existing:
            arm = existing.study_arm.single()
            branch = existing.study_branch_arm.single()
            arm_uid = arm.uid if arm else None
            branch_uid = branch.uid if branch else None
            if branch_uid and branch_uid == design_cell_vo.study_branch_arm_uid:
                raise exceptions.ForbiddenException(
                    "A study design cell already exists for the given combination study branch arm and study epoch."
                )
            if not branch_uid and arm_uid == design_cell_vo.study_arm_uid:
                raise exceptions.ForbiddenException(
                    "A study design cell already exists for the given combination of study arm and study epoch."
                )
        design_cell.study_value.connect(latest_study_value_node)
        # return the json response model
        return self._from_repository_values(design_cell_vo.study_uid, design_cell)

    def manage_previous_outbound_relationships(
        self, previous_item: StudyDesignCell, latest_study_value_node: StudyValue
    ):
        # DROP StudyValue relationship
        previous_item.study_value.disconnect(latest_study_value_node)

    def manage_versioning_update(
        self,
        study_root: StudyRoot,
        study_design_cell: StudyDesignCellVO,
        previous_item: StudyDesignCell,
        new_item: StudyDesignCell,
    ):
        # Record StudyAction
        action = Edit(
            date=datetime.datetime.now(datetime.timezone.utc),
            user_initials=study_design_cell.user_initials,
        )
        action.save()
        previous_item.has_before.connect(action)
        new_item.has_after.connect(action)
        study_root.audit_trail.connect(action)

    def manage_versioning_create(
        self,
        study_root: StudyRoot,
        study_design_cell: StudyDesignCellVO,
        new_item: StudyDesignCell,
    ):
        # create StudyAction node
        action = Create(
            date=datetime.datetime.now(datetime.timezone.utc),
            user_initials=study_design_cell.user_initials,
        )
        action.save()
        # connect the new item to the newly StudyAction
        new_item.has_after.connect(action)
        # connect the audit trail to the study_root node
        study_root.audit_trail.connect(action)

    def _remove_old_selection_if_exists(self, design_cell: StudyDesignCell):
        return db.cypher_query(
            """
            MATCH (:StudyRoot {uid: $study_uid})-[:LATEST]->(:StudyValue)-[rel:HAS_STUDY_DESIGN_CELL]->(:StudyDesignCell {uid: $design_cell_uid})
            DELETE rel
            """,
            {
                "study_uid": design_cell.study_uid,
                "design_cell_uid": design_cell.uid,
            },
        )

    def patch_study_arm(
        self,
        study_uid: str,
        design_cell_uid: str,
        study_arm_uid: str,
        author: str,
        allow_none_arm_branch_arm=False,
    ):
        study_design_cell = self.find_by_uid(study_uid=study_uid, uid=design_cell_uid)
        study_design_cell.study_arm_uid = study_arm_uid
        study_design_cell.study_branch_arm_uid = None

        self.save(
            study_design_cell,
            author,
            create=False,
            allow_none_arm_branch_arm=allow_none_arm_branch_arm,
        )

    def get_design_cells_connected_to_branch_arm(
        self, study_uid: str, study_branch_arm_uid: str
    ):
        sdc_node = to_relation_trees(
            StudyDesignCell.nodes.fetch_relations(
                "study_epoch__has_epoch__has_name_root__has_latest_value",
                "has_after",
                "study_epoch__study_value",
            )
            .fetch_optional_relations(
                "study_branch_arm__study_value", "study_element__study_value"
            )
            .filter(
                study_value__study_root__uid=study_uid,
                study_branch_arm__uid=study_branch_arm_uid,
                study_branch_arm__study_value__study_root__uid=study_uid,
            )
            .order_by("order")
        ).distinct()
        return sdc_node

    def get_design_cells_connected_to_epoch(self, study_uid: str, study_epoch_uid: str):
        sdc_node = to_relation_trees(
            StudyDesignCell.nodes.fetch_relations(
                "study_epoch__has_epoch__has_name_root__has_latest_value",
                "has_after",
                "study_epoch",
            )
            .fetch_optional_relations(
                "study_arm__study_value",
                "study_branch_arm__study_value",
                "study_element__study_value",
            )
            .filter(
                study_value__study_root__uid=study_uid,
                study_epoch__uid=study_epoch_uid,
                study_epoch__study_value__study_root__uid=study_uid,
            )
            .order_by("order")
        )

        return sdc_node

    def get_design_cells_connected_to_arm(self, study_uid: str, study_arm_uid: str):
        sdc_node = to_relation_trees(
            StudyDesignCell.nodes.fetch_relations(
                "study_epoch__has_epoch__has_name_root__has_latest_value",
                "study_arm",
                "has_after",
                "study_epoch__study_value",
            )
            .fetch_optional_relations("study_element__study_value")
            .filter(
                study_value__study_root__uid=study_uid,
                study_arm__uid=study_arm_uid,
                study_arm__study_value__study_root__uid=study_uid,
            )
            .order_by("order")
        ).distinct()

        return sdc_node

    def get_design_cells_connected_to_element(
        self, study_uid: str, study_element_uid: str
    ):
        sdc_node = to_relation_trees(
            StudyDesignCell.nodes.fetch_relations(
                "study_element",
                "has_after",
            )
            .filter(
                study_value__study_root__uid=study_uid,
                study_element__uid=study_element_uid,
                study_element__study_value__study_root__uid=study_uid,
            )
            .order_by("order")
        )
        return sdc_node

    def delete(self, study_uid: str, design_cell_uid: str, author: str):
        study_root_node = StudyRoot.nodes.get_or_none(uid=study_uid)
        if study_root_node is None:
            raise exceptions.NotFoundException(
                f"The study with uid {study_uid} was not found"
            )
        latest_study_value_node = study_root_node.latest_value.single()
        design_cell = latest_study_value_node.has_study_design_cell.get_or_none(
            uid=design_cell_uid
        )
        if design_cell is None:
            raise exceptions.NotFoundException(
                f"The study design cell with uid {design_cell_uid} was not found"
            )

        # create delete version
        new_design_cell = StudyDesignCell(
            uid=design_cell.uid,
            transition_rule=design_cell.transition_rule,
            order=design_cell.order,
        )
        new_design_cell.save()

        study_arm_node = design_cell.study_arm.single()
        study_branch_arm_node = design_cell.study_branch_arm.single()
        # at least one of the two has to be defined
        if study_arm_node:
            new_design_cell.study_arm.connect(study_arm_node)
        elif study_branch_arm_node:
            new_design_cell.study_branch_arm.connect(study_branch_arm_node)
        else:
            raise exceptions.NotFoundException(
                "Study arm or Study Branch Arm must exist"
            )

        # get StudyEpoch
        study_epoch_node = design_cell.study_epoch.single()
        if study_epoch_node:
            new_design_cell.study_epoch.connect(study_epoch_node)
        else:
            raise exceptions.NotFoundException("Study epoch must exists")

        # gest StudyElement
        study_element_node = design_cell.study_element.single()
        if study_element_node:
            new_design_cell.study_element.connect(study_element_node)
        else:
            raise exceptions.NotFoundException("Study element must exists")

        # Audit trail
        audit_node = Delete(
            user_initials=author, date=datetime.datetime.now(datetime.timezone.utc)
        )
        audit_node.save()
        study_root_node.audit_trail.connect(audit_node)
        design_cell.has_before.connect(audit_node)
        new_design_cell.has_after.connect(audit_node)
        self.manage_previous_outbound_relationships(
            previous_item=design_cell, latest_study_value_node=latest_study_value_node
        )

    def generate_uid(self) -> str:
        return StudyDesignCell.get_next_free_uid_and_increment_counter()

    def _get_selection_with_history(self, study_uid: str, design_cell_uid: str = None):
        """
        returns the audit trail for study design cell either for a
        specific selection or for all study design cells for the study.
        """
        # if some DesignCell is specified
        if design_cell_uid:
            # then query just that specific design cell
            cypher = """
            MATCH (sr:StudyRoot { uid: $study_uid})-[:AUDIT_TRAIL]->(:StudyAction)-[:BEFORE|AFTER]->(sdc:StudyDesignCell {uid: $design_cell_uid})
            WITH sdc
            MATCH (sdc)-[:AFTER|BEFORE*0..]-(all_sdc:StudyDesignCell)
            WITH distinct(all_sdc)
            """
        # if get all study design cells history is called
        else:
            # then query all the design cells
            cypher = """
            MATCH (sr:StudyRoot { uid: $study_uid})-[:AUDIT_TRAIL]->(:StudyAction)-[:BEFORE|AFTER]->(all_sdc:StudyDesignCell)
            WITH DISTINCT all_sdc
            """
        specific_design_cells_audit_trail = db.cypher_query(
            cypher
            + """
            OPTIONAL MATCH (all_sdc)<-[:STUDY_BRANCH_ARM_HAS_DESIGN_CELL]-(sba:StudyBranchArm)
            OPTIONAL MATCH (all_sdc)<-[:STUDY_ARM_HAS_DESIGN_CELL]-(sa:StudyArm)
            MATCH (all_sdc)<-[:STUDY_EPOCH_HAS_DESIGN_CELL]-(se:StudyEpoch)
            OPTIONAL MATCH (all_sdc)<-[:STUDY_ELEMENT_HAS_DESIGN_CELL]-(sel:StudyElement)
            MATCH (all_sdc)<-[:AFTER]-(asa:StudyAction)
            OPTIONAL MATCH (all_sdc)<-[:BEFORE]-(bsa:StudyAction)
            WITH all_sdc, sa, se, sel, asa, bsa, sba
            ORDER BY all_sdc.uid, asa.date DESC
            RETURN DISTINCT
                all_sdc.uid AS uid,
                all_sdc.transition_rule AS transition_rule,
                all_sdc.order AS order,
                sa.uid AS study_arm_uid, 
                sba.uid AS study_branch_arm_uid,
                se.uid AS study_epoch_uid,
                sel.uid AS study_element_uid,
                labels(asa) AS change_type,
                asa.date AS start_date,
                bsa.date AS end_date,
                asa.user_initials AS user_initials
            """,
            {"study_uid": study_uid, "design_cell_uid": design_cell_uid},
        )
        result = []
        for res in helpers.db_result_to_list(specific_design_cells_audit_trail):
            for action in res["change_type"]:
                if "StudyAction" not in action:
                    change_type = action
            end_date = (
                convert_to_datetime(value=res["end_date"]) if res["end_date"] else None
            )
            result.append(
                StudyDesignCellHistory(
                    study_uid=study_uid,
                    study_selection_uid=res["uid"],
                    study_arm_uid=res["study_arm_uid"],
                    study_branch_arm_uid=res["study_branch_arm_uid"],
                    study_epoch_uid=res["study_epoch_uid"],
                    study_element_uid=res["study_element_uid"],
                    user_initials=res["user_initials"],
                    change_type=change_type,
                    start_date=convert_to_datetime(value=res["start_date"]),
                    transition_rule=res["transition_rule"],
                    order=res["order"],
                    end_date=end_date,
                )
            )
        return result

    def find_selection_history(
        self, study_uid: str, design_cell_uid: str = None
    ) -> List[Optional[dict]]:
        if design_cell_uid:
            return self._get_selection_with_history(
                study_uid=study_uid, design_cell_uid=design_cell_uid
            )
        return self._get_selection_with_history(study_uid=study_uid)

    def close(self) -> None:
        pass