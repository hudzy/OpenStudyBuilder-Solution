from typing import Optional, Sequence, Tuple

from neomodel import db
from pydantic.main import BaseModel

from clinical_mdr_api.domain.controlled_terminology.ct_term_attributes import (
    CTTermAttributesAR,
)
from clinical_mdr_api.domain.controlled_terminology.ct_term_name import CTTermNameAR
from clinical_mdr_api.domain.dictionaries.dictionary_term import DictionaryTermAR
from clinical_mdr_api.domain.syntax_templates.objective_template import (
    ObjectiveTemplateAR,
)
from clinical_mdr_api.domain.syntax_templates.template import TemplateVO
from clinical_mdr_api.domain_repositories.models.syntax import ObjectiveTemplateRoot
from clinical_mdr_api.domain_repositories.syntax_instances.objective_repository import (
    ObjectiveRepository,
)
from clinical_mdr_api.domain_repositories.syntax_templates.objective_template_repository import (
    ObjectiveTemplateRepository,
)
from clinical_mdr_api.exceptions import ValidationException
from clinical_mdr_api.models.ct_term import CTTermNameAndAttributes
from clinical_mdr_api.models.dictionary_term import DictionaryTerm
from clinical_mdr_api.models.syntax_templates.objective_template import (
    ObjectiveTemplate,
    ObjectiveTemplateCreateInput,
    ObjectiveTemplateEditIndexingsInput,
    ObjectiveTemplateVersion,
    ObjectiveTemplateWithCount,
)
from clinical_mdr_api.models.utils import GenericFilteringReturn
from clinical_mdr_api.repositories._utils import FilterOperator
from clinical_mdr_api.services._utils import service_level_generic_filtering
from clinical_mdr_api.services.syntax_templates.generic_syntax_template_service import (
    GenericSyntaxTemplateService,
)


class ObjectiveTemplateService(GenericSyntaxTemplateService[ObjectiveTemplateAR]):
    aggregate_class = ObjectiveTemplateAR
    version_class = ObjectiveTemplateVersion
    repository_interface = ObjectiveTemplateRepository
    object_repository_interface = ObjectiveRepository
    root_node_class = ObjectiveTemplateRoot

    def _transform_aggregate_root_to_pydantic_model(
        self, item_ar: ObjectiveTemplateAR
    ) -> ObjectiveTemplate:
        item_ar = self._set_default_parameter_terms(item_ar)
        cls = (
            ObjectiveTemplateWithCount
            if item_ar.counts is not None
            else ObjectiveTemplate
        )
        return cls.from_objective_template_ar(item_ar)

    def get_all(
        self,
        status: Optional[str] = None,
        return_study_count: bool = True,
        sort_by: Optional[dict] = None,
        page_number: int = 1,
        page_size: int = 0,
        filter_by: Optional[dict] = None,
        filter_operator: Optional[FilterOperator] = FilterOperator.AND,
        total_count: bool = False,
    ) -> GenericFilteringReturn[ObjectiveTemplate]:
        all_items = super().get_all(status, return_study_count)

        # The get_all method is only using neomodel, without Cypher query
        # Therefore, the filtering will be done in this service layer
        filtered_items = service_level_generic_filtering(
            items=all_items,
            filter_by=filter_by,
            filter_operator=filter_operator,
            sort_by=sort_by,
            total_count=total_count,
            page_number=page_number,
            page_size=page_size,
        )

        return filtered_items

    def _create_ar_from_input_values(
        self, template: ObjectiveTemplateCreateInput
    ) -> ObjectiveTemplateAR:
        default_parameter_terms = self._create_default_parameter_entries(
            template_name=template.name,
            default_parameter_terms=template.default_parameter_terms,
        )

        template_vo, library_vo = self._create_template_vo(
            template, default_parameter_terms
        )

        # Get indexings for templates from database
        indications, categories = self._get_indexings(template)

        # Process item to save
        try:
            item = ObjectiveTemplateAR.from_input_values(
                template_value_exists_callback=self.get_check_exists_callback(
                    template=template
                ),
                author=self.user_initials,
                template=template_vo,
                library=library_vo,
                generate_uid_callback=self.repository.generate_uid_callback,
                is_confirmatory_testing=template.is_confirmatory_testing,
                indications=indications,
                categories=categories,
            )
        except ValueError as e:
            raise ValidationException(e.args[0]) from e

        return item

    @db.transaction
    def patch_indexings(
        self, uid: str, indexings: ObjectiveTemplateEditIndexingsInput
    ) -> ObjectiveTemplate:
        try:
            if indexings.indication_uids is not None:
                self.repository.patch_indications(uid, indexings.indication_uids)
            if indexings.category_uids is not None:
                self.repository.patch_categories(uid, indexings.category_uids)
            self.repository.patch_is_confirmatory_testing(
                uid, indexings.is_confirmatory_testing
            )
        finally:
            self.repository.close()

        return self.get_by_uid(uid)

    def _set_default_parameter_terms(
        self, item: ObjectiveTemplateAR
    ) -> ObjectiveTemplateAR:
        """This method fetches and sets the default parameter terms for the template

        Args:
            item (ObjectiveTemplateAR): The template for which to fetch default parameter terms
        """
        # Get default parameter terms
        default_parameter_terms = self.repository.get_default_parameter_terms(item.uid)

        return ObjectiveTemplateAR(
            _uid=item.uid,
            _library=item.library,
            _item_metadata=item.item_metadata,
            _counts=item.counts,
            _study_count=item.study_count,
            _indications=item.indications,
            _categories=item.categories,
            _is_confirmatory_testing=item.is_confirmatory_testing,
            _template=TemplateVO(
                name=item.template_value.name,
                name_plain=item.template_value.name_plain,
                default_parameter_terms=default_parameter_terms,
                guidance_text=item.template_value.guidance_text,
            ),
        )

    def _set_indexings(self, item: ObjectiveTemplate) -> None:
        """
        This method fetches and sets the indexing properties to a template.
        """
        # Get indications
        indications = (
            self._repos.dictionary_term_generic_repository.get_syntax_indications(
                self.root_node_class, item.uid
            )
        )
        if indications:
            item.indications = [
                DictionaryTerm.from_dictionary_term_ar(indication)
                for indication in indications
            ]
        # Get categories
        category_names = self._repos.ct_term_name_repository.get_syntax_categories(
            self.root_node_class, item.uid
        )
        category_attributes = (
            self._repos.ct_term_attributes_repository.get_syntax_categories(
                self.root_node_class, item.uid
            )
        )
        if category_names and category_attributes:
            item.categories = [
                CTTermNameAndAttributes.from_ct_term_ars(
                    ct_term_name_ar=category_name,
                    ct_term_attributes_ar=category_attribute,
                )
                for category_name, category_attribute in zip(
                    category_names, category_attributes
                )
            ]

    def _get_indexings(
        self, template: BaseModel
    ) -> Tuple[
        Sequence[DictionaryTermAR], Sequence[Tuple[CTTermNameAR, CTTermAttributesAR]]
    ]:
        indications: Sequence[DictionaryTermAR] = []
        categories: Sequence[Tuple[CTTermNameAR, CTTermAttributesAR]] = []

        # Fetch the indication objects with corresponding uid from the database
        # It will be needed to save the template, and in the return model
        if template.indication_uids and len(template.indication_uids) > 0:
            for uid in template.indication_uids:
                indication = self._repos.dictionary_term_generic_repository.find_by_uid(
                    term_uid=uid
                )
                indications.append(indication)

        # Fetch the category objects with corresponding uid from the database
        # It will be needed to save the template, and in the return model
        if template.category_uids and len(template.category_uids) > 0:
            for uid in template.category_uids:
                category_name = self._repos.ct_term_name_repository.find_by_uid(
                    term_uid=uid
                )
                category_attributes = (
                    self._repos.ct_term_attributes_repository.find_by_uid(term_uid=uid)
                )
                category = (category_name, category_attributes)
                categories.append(category)

        return indications, categories