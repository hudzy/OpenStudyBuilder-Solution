from clinical_mdr_api.domain.biomedical_concepts.activity_item_class import (
    ActivityItemClassAR,
    ActivityItemClassVO,
)
from clinical_mdr_api.domain.versioned_object_aggregate import LibraryVO
from clinical_mdr_api.domain_repositories.library_item_repository import (
    LibraryItemRepositoryImplBase,
    _AggregateRootType,
)
from clinical_mdr_api.domain_repositories.models._utils import (
    LATEST_VERSION_ORDER_BY,
    CustomNodeSet,
)
from clinical_mdr_api.domain_repositories.models.biomedical_concepts import (
    ActivityInstanceClassRoot,
    ActivityItemClassRoot,
    ActivityItemClassValue,
)
from clinical_mdr_api.domain_repositories.models.generic import (
    Library,
    VersionRelationship,
)
from clinical_mdr_api.domain_repositories.neomodel_ext_item_repository import (
    NeomodelExtBaseRepository,
)
from clinical_mdr_api.models.biomedical_concepts.activity_item_class import (
    ActivityItemClass,
)


class ActivityItemClassRepository(
    NeomodelExtBaseRepository, LibraryItemRepositoryImplBase[_AggregateRootType]
):
    root_class = ActivityItemClassRoot
    value_class = ActivityItemClassValue
    return_model = ActivityItemClass

    def get_neomodel_extension_query(self) -> CustomNodeSet:
        return (
            ActivityItemClassRoot.nodes.fetch_relations(
                "has_latest_value",
                "has_library",
            )
            .fetch_optional_relations_and_collect(
                "has_activity_instance_class__has_latest_value",
            )
            .fetch_optional_single_relation_of_type(
                {
                    "has_version": ("latest_version", LATEST_VERSION_ORDER_BY),
                }
            )
        )

    def _has_data_changed(
        self, ar: ActivityItemClassAR, value: ActivityItemClassValue
    ) -> bool:
        activity_instance_class_uids = [
            node.uid
            for node in value.has_latest_value.get().has_activity_instance_class.all()
        ]
        return (
            ar.activity_item_class_vo.name != value.name
            or ar.activity_item_class_vo.order != value.order
            or ar.activity_item_class_vo.mandatory != value.mandatory
            or sorted(ar.activity_item_class_vo.activity_instance_class_uids)
            != sorted(activity_instance_class_uids)
        )

    def _get_or_create_value(
        self, root: ActivityItemClassRoot, ar: ActivityItemClassAR
    ) -> ActivityItemClassValue:
        for itm in root.has_version.all():
            if not self._has_data_changed(ar, itm):
                return itm
        latest_draft = root.latest_draft.get_or_none()
        if latest_draft and not self._has_data_changed(ar, latest_draft):
            return latest_draft
        latest_final = root.latest_final.get_or_none()
        if latest_final and not self._has_data_changed(ar, latest_final):
            return latest_final
        latest_retired = root.latest_retired.get_or_none()
        if latest_retired and not self._has_data_changed(ar, latest_retired):
            return latest_retired
        new_value = ActivityItemClassValue(
            name=ar.activity_item_class_vo.name,
            order=ar.activity_item_class_vo.order,
            mandatory=ar.activity_item_class_vo.mandatory,
        )
        self._db_save_node(new_value)
        for (
            activity_instance_class_uid
        ) in ar.activity_item_class_vo.activity_instance_class_uids:
            activity_instance_class = ActivityInstanceClassRoot.nodes.get_or_none(
                uid=activity_instance_class_uid
            )
            root.has_activity_instance_class.connect(activity_instance_class)
        return new_value

    def generate_uid(self) -> str:
        return ActivityItemClassRoot.get_next_free_uid_and_increment_counter()

    def _create_aggregate_root_instance_from_version_root_relationship_and_value(
        self,
        *,
        root: ActivityItemClassRoot,
        library: Library,
        relationship: VersionRelationship,
        value: ActivityItemClassValue,
    ) -> ActivityItemClassAR:
        activity_instance_class_uids = [
            node.uid for node in root.has_activity_instance_class.all()
        ]
        return ActivityItemClassAR.from_repository_values(
            uid=root.uid,
            activity_item_class_vo=ActivityItemClassVO.from_repository_values(
                name=value.name,
                order=value.order,
                mandatory=value.mandatory,
                activity_instance_class_uids=activity_instance_class_uids,
            ),
            library=LibraryVO.from_input_values_2(
                library_name=library.name,
                is_library_editable_callback=(lambda _: library.is_editable),
            ),
            item_metadata=self._library_item_metadata_vo_from_relation(relationship),
        )

    def _maintain_parameters(
        self,
        versioned_object: _AggregateRootType,
        root: ActivityItemClassRoot,
        value: ActivityItemClassValue,
    ) -> None:
        pass