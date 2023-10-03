from typing import Callable

from neomodel import db

from clinical_mdr_api import exceptions
from clinical_mdr_api.domain_repositories.study_selections.study_soa_footnote_repository import (
    StudySoAFootnoteRepository,
)
from clinical_mdr_api.domains.study_definition_aggregates.study_metadata import (
    StudyStatus,
)
from clinical_mdr_api.domains.study_selections.study_soa_footnote import (
    ReferencedItemVO,
    StudySoAFootnoteVO,
    StudySoAFootnoteVOHistory,
)
from clinical_mdr_api.domains.syntax_instances.footnote import FootnoteAR
from clinical_mdr_api.exceptions import NotFoundException
from clinical_mdr_api.models import FootnoteCreateInput
from clinical_mdr_api.models.study_selections.study_soa_footnote import (
    ReferencedItem,
    StudySoAFootnote,
    StudySoAFootnoteCreateFootnoteInput,
    StudySoAFootnoteCreateInput,
    StudySoAFootnoteEditInput,
    StudySoAFootnoteHistory,
    StudySoAFootnoteVersion,
)
from clinical_mdr_api.models.utils import GenericFilteringReturn
from clinical_mdr_api.repositories._utils import FilterOperator
from clinical_mdr_api.services._meta_repository import MetaRepository
from clinical_mdr_api.services._utils import (
    calculate_diffs,
    calculate_diffs_history,
    normalize_string,
    service_level_generic_filtering,
    service_level_generic_header_filtering,
)
from clinical_mdr_api.services.studies.study_flowchart import StudyFlowchartService
from clinical_mdr_api.services.syntax_instances.footnotes import FootnoteService


class StudySoAFootnoteService:
    def __init__(self, author="TODO Initials"):
        self.author = author
        self._repos = MetaRepository()
        self.repository_interface = StudySoAFootnoteRepository

    @property
    def repository(self) -> StudySoAFootnoteRepository:
        return self.repository_interface()

    def _transform_vo_to_pydantic_model(
        self,
        study_soa_footnote_vo: StudySoAFootnoteVO,
        find_footnote_by_uid: Callable[[str], FootnoteAR | None] = None,
    ) -> StudySoAFootnote:
        return StudySoAFootnote.from_study_soa_footnote_vo(
            study_soa_footnote_vo=study_soa_footnote_vo,
            find_footnote_by_uid=self._repos.footnote_repository.find_by_uid_2
            if not find_footnote_by_uid
            else find_footnote_by_uid,
            find_footnote_template_by_uid=self._repos.footnote_template_repository.find_by_uid_2,
            find_activity_group_by_uid=self._repos.activity_group_repository.find_by_uid_2,
            find_activity_subgroup_by_uid=self._repos.activity_subgroup_repository.find_by_uid_2,
        )

    def _transform_vo_to_pydantic_history_model(
        self, study_soa_footnote_vo: StudySoAFootnoteVOHistory
    ) -> StudySoAFootnote:
        return StudySoAFootnoteHistory.from_study_soa_footnote_vo_history(
            study_soa_footnote_vo=study_soa_footnote_vo,
            find_footnote_by_uid=self._repos.footnote_repository.find_by_uid_2,
            find_footnote_template_by_uid=self._repos.footnote_template_repository.find_by_uid_2,
            find_activity_group_by_uid=self._repos.activity_group_repository.find_by_uid_2,
            find_activity_subgroup_by_uid=self._repos.activity_subgroup_repository.find_by_uid_2,
        )

    def get_all(
        self,
        sort_by: dict | None = None,
        page_number: int = 1,
        page_size: int = 10,
        filter_by: dict | None = None,
        filter_operator: FilterOperator | None = FilterOperator.AND,
        total_count: bool = False,
    ) -> GenericFilteringReturn[StudySoAFootnote]:
        items = self.repository.find_all_footnotes()
        items = [
            self._transform_vo_to_pydantic_model(study_soa_footnote_vo=item)
            for item in items
        ]
        filtered_items = service_level_generic_filtering(
            items=items,
            filter_by=filter_by,
            filter_operator=filter_operator,
            sort_by=sort_by,
            total_count=total_count,
            page_number=page_number,
            page_size=page_size,
        )
        all_items = GenericFilteringReturn.create(
            filtered_items.items, filtered_items.total
        )
        return all_items

    def get_all_by_study_uid(
        self,
        study_uid: str,
        sort_by: dict | None = None,
        page_number: int = 1,
        page_size: int = 10,
        filter_by: dict | None = None,
        filter_operator: FilterOperator | None = FilterOperator.AND,
        total_count: bool = False,
    ) -> GenericFilteringReturn[StudySoAFootnote]:
        items = self.repository.find_all_footnotes(
            study_uid=study_uid,
        )
        items = [
            self._transform_vo_to_pydantic_model(study_soa_footnote_vo=item)
            for item in items
        ]
        filtered_items = service_level_generic_filtering(
            items=items,
            filter_by=filter_by,
            filter_operator=filter_operator,
            sort_by=sort_by,
            total_count=total_count,
            page_number=page_number,
            page_size=page_size,
        )
        all_items = GenericFilteringReturn.create(
            filtered_items.items, filtered_items.total
        )
        return all_items

    def get_distinct_values_for_header(
        self,
        study_uid: str | None,
        field_name: str,
        search_string: str | None = "",
        filter_by: dict | None = None,
        filter_operator: FilterOperator | None = FilterOperator.AND,
        result_count: int = 10,
    ) -> list:
        if study_uid:
            all_items = self.get_all_by_study_uid(study_uid=study_uid)
        else:
            all_items = self.get_all()
        header_values = service_level_generic_header_filtering(
            items=all_items.items,
            field_name=field_name,
            search_string=search_string,
            filter_by=filter_by,
            filter_operator=filter_operator,
            result_count=result_count,
        )
        # Return values for field_name
        return header_values

    def get_by_uid(
        self,
        uid: str,
    ):
        item = self.repository.find_by_uid(uid=uid)
        return self._transform_vo_to_pydantic_model(study_soa_footnote_vo=item)

    def derive_footnote_number(
        self,
        study_uid: str,
        referenced_items: list[ReferencedItem],
        all_soa_footnotes: list[StudySoAFootnoteVO],
    ):
        flowchart_matrix = StudyFlowchartService(current_user_id="test").get_table(
            study_uid=study_uid,
            time_unit="day",
            use_uid_instead_of_name=True,
        )
        matrix = (
            [flowchart_matrix.headers[0].data]
            + [flowchart_matrix.headers[1].data]
            + flowchart_matrix.data
        )
        footnote_orders = []
        new_footnote = "new_footnote"
        for row in matrix:
            for elem in row:
                for footnote in all_soa_footnotes:
                    if any(item.item_uid == elem for item in footnote.referenced_items):
                        if footnote.uid not in footnote_orders:
                            footnote_orders.append(footnote.uid)
                if any(item.item_uid == elem for item in referenced_items):
                    if new_footnote not in footnote_orders:
                        footnote_orders.append(new_footnote)
        # if soa footnote referenced item is found in flowchart, assign a footnote order
        if new_footnote in footnote_orders:
            footnote_number = footnote_orders.index(new_footnote) + 1
        # if soa footnote referenced item is not found in flowchart, assign footnote order to the end
        elif len(referenced_items) == 0:
            footnote_number = len(all_soa_footnotes) + 1
        # The item from referenced items wasn't found in the flowchart
        else:
            raise exceptions.ValidationException(
                f"Some of the referenced items {(referenced_items)} were not found in the flowchart"
            )
        return footnote_number

    def instantiate_study_soa_vo(
        self,
        study_uid: str,
        footnote_uid: str,
        footnote_template_uid: str,
        referenced_items: list[ReferencedItem],
        footnote_number: int,
        uid: str = None,
    ):
        footnote_vo = StudySoAFootnoteVO.from_input_values(
            study_uid=study_uid,
            footnote_uid=footnote_uid,
            footnote_template_uid=footnote_template_uid,
            referenced_items=[
                ReferencedItemVO(
                    item_type=ref_item.item_type,
                    item_uid=ref_item.item_uid,
                    item_name=None,
                )
                for ref_item in referenced_items
            ],
            footnote_number=footnote_number,
            generate_uid_callback=self.repository.generate_soa_footnote_uid
            if not uid
            else lambda: uid,
            status=StudyStatus.DRAFT,
            author=self.author,
        )
        return footnote_vo

    def synchronize_footnotes(self, footnotes_to_fix: list[StudySoAFootnoteVO]):
        for footnote_number, footnote_to_fix in enumerate(footnotes_to_fix, start=1):
            if footnote_to_fix.footnote_number != footnote_number:
                footnote_to_fix.footnote_number = footnote_number
                self.repository.save(footnote_to_fix, create=False)

    def create_with_underlying_footnote(
        self, study_uid: str, footnote_input: StudySoAFootnoteCreateFootnoteInput
    ) -> StudySoAFootnote:
        footnote_template = self._repos.footnote_template_repository.find_by_uid_2(
            uid=footnote_input.footnote_data.footnote_template_uid
        )
        if footnote_template is None:
            raise exceptions.NotFoundException(
                f"Footnote template with uid {footnote_input.footnote_data.footnote_template_uid} does not exist"
            )

        if (
            footnote_template.template_value.parameter_names is not None
            and len(footnote_template.template_value.parameter_names) > 0
            and (
                footnote_input.footnote_data.parameter_terms is None
                or len(footnote_input.footnote_data.parameter_terms) == 0
            )
        ):
            soa_footnote = self.manage_create(
                study_uid=study_uid,
                footnote_input=StudySoAFootnoteCreateInput(
                    footnote_template_uid=footnote_template.uid,
                    referenced_items=footnote_input.referenced_items,
                ),
            )
        else:
            parameter_terms = (
                footnote_input.footnote_data.parameter_terms
                if footnote_input.footnote_data.parameter_terms is not None
                else []
            )
            footnote_create_input = FootnoteCreateInput(
                footnote_template_uid=footnote_input.footnote_data.footnote_template_uid,
                parameter_terms=parameter_terms,
                library_name=footnote_input.footnote_data.library_name,
            )
            footnote_service = FootnoteService()
            footnote_ar = footnote_service.create_ar_from_input_values(
                footnote_create_input,
                study_uid=study_uid,
            )
            footnote_uid = footnote_ar.uid
            if not footnote_service.repository.check_exists_by_name(footnote_ar.name):
                footnote_ar.approve(author=self.author)
                footnote_service.repository.save(footnote_ar)
            else:
                footnote_uid = footnote_service.repository.find_uid_by_name(
                    name=footnote_ar.name
                )
                if footnote_uid is None:
                    raise NotFoundException(
                        f"Could not find node with label FootnoteValue and name {footnote_ar.name}"
                    )
            footnote_ar = footnote_service.repository.find_by_uid_2(
                footnote_uid, for_update=True
            )
            soa_footnote = self.manage_create(
                study_uid=study_uid,
                footnote_input=StudySoAFootnoteCreateInput(
                    footnote_uid=footnote_ar.uid,
                    referenced_items=footnote_input.referenced_items,
                ),
            )
        return soa_footnote

    def manage_create(
        self, study_uid: str, footnote_input: StudySoAFootnoteCreateInput
    ) -> StudySoAFootnote:
        all_soa_footnotes = self.repository.find_all_footnotes(study_uid=study_uid)

        footnote_number = self.derive_footnote_number(
            study_uid=study_uid,
            referenced_items=footnote_input.referenced_items,
            all_soa_footnotes=all_soa_footnotes,
        )
        footnote_vo = self.instantiate_study_soa_vo(
            study_uid=study_uid,
            footnote_uid=footnote_input.footnote_uid,
            footnote_template_uid=footnote_input.footnote_template_uid,
            referenced_items=footnote_input.referenced_items,
            footnote_number=footnote_number,
        )
        self.validate(
            footnote_uid=footnote_input.footnote_uid,
            footnote_template_uid=footnote_input.footnote_template_uid,
            all_soa_footnotes=all_soa_footnotes,
            soa_footnote_uid=footnote_vo.uid,
        )
        self.repository.save(footnote_vo)
        all_soa_footnotes.insert(footnote_vo.footnote_number - 1, footnote_vo)
        self.synchronize_footnotes(
            footnotes_to_fix=all_soa_footnotes,
        )
        return self._transform_vo_to_pydantic_model(footnote_vo)

    @db.transaction
    def create(
        self,
        study_uid: str,
        footnote_input: StudySoAFootnoteCreateInput
        | StudySoAFootnoteCreateFootnoteInput,
        create_footnote: bool,
    ) -> StudySoAFootnote:
        if create_footnote:
            return self.create_with_underlying_footnote(
                study_uid=study_uid, footnote_input=footnote_input
            )
        return self.manage_create(study_uid=study_uid, footnote_input=footnote_input)

    @db.transaction
    def batch_create(
        self, study_uid: str, footnote_input: list[StudySoAFootnoteCreateFootnoteInput]
    ) -> list[StudySoAFootnote]:
        soa_footnotes = []
        for soa_footnote_input in footnote_input:
            soa_footnote = self.create_with_underlying_footnote(
                study_uid=study_uid, footnote_input=soa_footnote_input
            )
            soa_footnotes.append(soa_footnote)
        return soa_footnotes

    @db.transaction
    def delete(self, study_uid: str, study_soa_footnote_uid: str):
        soa_footnote_vo = self.repository.find_by_uid(uid=study_soa_footnote_uid)
        soa_footnote_vo.is_deleted = True
        self.repository.save(soa_footnote_vo, create=False)

        all_soa_footnotes = self.repository.find_all_footnotes(study_uid=study_uid)
        self.synchronize_footnotes(footnotes_to_fix=all_soa_footnotes)

    def validate(
        self,
        footnote_uid: str | None,
        footnote_template_uid: str | None,
        all_soa_footnotes: list,
        soa_footnote_uid: str,
    ):
        if (
            footnote_template_uid
            and not self._repos.footnote_template_repository.check_exists_final_version(
                normalize_string(footnote_template_uid)
            )
        ):
            raise exceptions.ValidationException(
                f"There is no Final footnote template identified by provided uid ({footnote_template_uid})"
            )
        if (
            footnote_uid
            and not self._repos.footnote_repository.check_exists_final_version(
                normalize_string(footnote_uid)
            )
        ):
            raise exceptions.ValidationException(
                f"There is no Final footnote identified by provided uid ({footnote_uid})"
            )
        if footnote_uid:
            footnote_service = FootnoteService()
            footnote_ar = footnote_service.repository.find_by_uid_2(footnote_uid)
            for soa_footnote in all_soa_footnotes:
                if (
                    soa_footnote.footnote_uid
                    and soa_footnote_uid != soa_footnote.uid
                    and footnote_ar.uid == soa_footnote.footnote_uid
                ):
                    raise exceptions.ValidationException(
                        f"The SoaFootnote already exists for a Footnote with the following instantiation ({footnote_ar.name_plain})"
                    )

    @db.transaction
    def edit(
        self,
        study_uid: str,
        study_soa_footnote_uid: str,
        footnote_edit_input: StudySoAFootnoteEditInput,
    ):
        soa_footnote = self.repository.find_by_uid(uid=study_soa_footnote_uid)
        footnote_number = soa_footnote.footnote_number
        all_soa_footnotes = self.repository.find_all_footnotes(study_uid=study_uid)
        # remove footnote that is being edited from calculations as it will be added in the end
        all_soa_footnotes = [
            soa_footnote
            for soa_footnote in all_soa_footnotes
            if soa_footnote.uid != study_soa_footnote_uid
        ]
        if footnote_edit_input.referenced_items is not None and sorted(
            ref_item.item_uid for ref_item in footnote_edit_input.referenced_items
        ) != sorted(ref_item.item_uid for ref_item in soa_footnote.referenced_items):
            footnote_number = self.derive_footnote_number(
                study_uid=study_uid,
                referenced_items=footnote_edit_input.referenced_items,
                all_soa_footnotes=all_soa_footnotes,
            )
        if (
            footnote_edit_input.referenced_items == soa_footnote.referenced_items
            or footnote_edit_input is None
        ) and (
            footnote_edit_input.footnote_uid == soa_footnote.footnote_uid
            or footnote_edit_input.footnote_uid is None
        ):
            raise exceptions.ValidationException("Nothing is changed")
        footnote_uid = None
        if footnote_edit_input.footnote_uid:
            footnote_uid = footnote_edit_input.footnote_uid
        elif soa_footnote.footnote_uid:
            footnote_uid = soa_footnote.footnote_uid
        footnote_template_uid = None
        if footnote_edit_input.footnote_template_uid:
            footnote_template_uid = footnote_edit_input.footnote_template_uid
        elif soa_footnote.footnote_template_uid:
            footnote_template_uid = soa_footnote.footnote_template_uid
        new_footnote_vo = self.instantiate_study_soa_vo(
            study_uid=study_uid,
            footnote_uid=footnote_uid,
            footnote_template_uid=footnote_template_uid,
            referenced_items=footnote_edit_input.referenced_items
            if footnote_edit_input.referenced_items is not None
            else soa_footnote.referenced_items,
            footnote_number=footnote_number,
            uid=study_soa_footnote_uid,
        )
        self.validate(
            footnote_uid=footnote_uid,
            footnote_template_uid=footnote_template_uid,
            all_soa_footnotes=all_soa_footnotes,
            soa_footnote_uid=new_footnote_vo.uid,
        )
        self.repository.save(new_footnote_vo, create=False)
        all_soa_footnotes.insert(new_footnote_vo.footnote_number - 1, new_footnote_vo)
        self.synchronize_footnotes(footnotes_to_fix=all_soa_footnotes)
        return self._transform_vo_to_pydantic_model(new_footnote_vo)

    def preview_soa_footnote(
        self, study_uid: str, footnote_create_input: StudySoAFootnoteCreateFootnoteInput
    ) -> StudySoAFootnote:
        footnote_service = FootnoteService()
        footnote_ar = footnote_service.create_ar_from_input_values(
            footnote_create_input.footnote_data,
            generate_uid_callback=(lambda: "preview"),
            study_uid=study_uid,
        )
        footnote_ar.approve(self.author)
        all_soa_footnotes = self.repository.find_all_footnotes(study_uid=study_uid)
        footnote_number = self.derive_footnote_number(
            study_uid=study_uid,
            referenced_items=footnote_create_input.referenced_items,
            all_soa_footnotes=all_soa_footnotes,
        )
        footnote_input = StudySoAFootnoteCreateInput(
            footnote_uid=footnote_ar.uid,
            referenced_items=footnote_create_input.referenced_items,
        )
        footnote_vo = self.instantiate_study_soa_vo(
            study_uid=study_uid,
            footnote_uid=footnote_input.footnote_uid,
            footnote_template_uid=footnote_input.footnote_template_uid,
            referenced_items=footnote_input.referenced_items,
            footnote_number=footnote_number,
        )

        # pass footnote_ar as parameter as it doesn't really exist in db and we are calling find_by_uid later on
        return self._transform_vo_to_pydantic_model(
            footnote_vo, find_footnote_by_uid=lambda _: footnote_ar
        )

    def audit_trail_specific_soa_footnote(
        self,
        study_soa_footnote_uid: str,
        study_uid: str,
    ) -> list[StudySoAFootnoteVersion]:
        all_versions = self.repository.get_all_versions_for_specific_visit(
            uid=study_soa_footnote_uid, study_uid=study_uid
        )
        versions = [
            self._transform_vo_to_pydantic_history_model(_).dict() for _ in all_versions
        ]
        data = calculate_diffs(versions, StudySoAFootnoteVersion)
        return data

    def audit_trail_all_soa_footnotes(
        self,
        study_uid: str,
    ) -> list[StudySoAFootnoteVersion]:
        data = calculate_diffs_history(
            get_all_object_versions=self.repository.get_all_versions,
            transform_all_to_history_model=self._transform_vo_to_pydantic_history_model,
            study_uid=study_uid,
            version_object_class=StudySoAFootnoteVersion,
        )
        return data