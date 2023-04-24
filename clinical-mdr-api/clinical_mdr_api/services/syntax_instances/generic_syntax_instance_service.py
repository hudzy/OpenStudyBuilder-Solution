import abc
from typing import Optional, Sequence, TypeVar, cast

from neomodel import core, db
from pydantic import BaseModel

from clinical_mdr_api.domain._utils import extract_parameters
from clinical_mdr_api.domain.library.library_ar import LibraryAR
from clinical_mdr_api.domain.library.object import (
    ParametrizedTemplateARBase,
    ParametrizedTemplateVO,
)
from clinical_mdr_api.domain.library.parameter_term import (
    ComplexParameterTerm,
    NumericParameterTermVO,
    ParameterTermEntryVO,
    SimpleParameterTermVO,
)
from clinical_mdr_api.domain.syntax_templates.template import TemplateVO
from clinical_mdr_api.domain.versioned_object_aggregate import (
    LibraryItemStatus,
    LibraryVO,
    VersioningException,
)
from clinical_mdr_api.domain_repositories._generic_repository_interface import (
    GenericRepository,
)
from clinical_mdr_api.domain_repositories.syntax_instances.template_parameters_repository import (
    TemplateParameterRepository,
)
from clinical_mdr_api.exceptions import (
    BusinessLogicException,
    NotFoundException,
    ValidationException,
)
from clinical_mdr_api.models.study import Study
from clinical_mdr_api.models.template_parameter_multi_select_input import (
    TemplateParameterMultiSelectInput,
)
from clinical_mdr_api.services._utils import process_complex_parameters
from clinical_mdr_api.services.generic_syntax_service import GenericSyntaxService
from clinical_mdr_api.services.study import StudyService

_AggregateRootType = TypeVar("_AggregateRootType")


class GenericSyntaxInstanceService(GenericSyntaxService[_AggregateRootType], abc.ABC):
    """
    This class is generic library object service. It can provide services for any type
    of object derived from templates. Supports generic versioning proces with exception that
    it not allows to create new version after it is approved.

    Configuration options:
    aggregate_class - a class of Aggregate root that supports selected object
    repository_interface - repository interface for selected object
    template_repository_interface - repository for template object that selected object is created from
    template_uid_property - name of template uid property from pydantic models supporting selected object
    template_name_property - template name property that service is supposed to return with pydantic object
    """

    aggregate_class: type
    repository_interface: type
    template_repository_interface: type
    template_uid_property: str
    template_name_property: str
    parametrized_template_vo_class: type = ParametrizedTemplateVO
    _allowed_parameters = None

    @property
    def template_repository(self) -> GenericRepository:
        """
        gets template object repository based on interface
        """
        return self.template_repository_interface()

    def _get_parameter_term(self, uid: str) -> str:
        """
        Return parameter term based on uid
        """
        params = []
        for p in self._allowed_parameters:
            params.extend(p["terms"])
        params_dict = {item["uid"]: item for item in params}
        return params_dict.get(uid, {}).get("name")

    def create_ar_from_input_values(
        self,
        template,
        generate_uid_callback=None,
        study_uid: Optional[str] = None,
        template_uid: Optional[str] = None,
        include_study_endpoints: Optional[bool] = False,
    ) -> _AggregateRootType:
        parameter_terms = self._create_parameter_entries(
            template,
            template_uid=template_uid,
            study_uid=study_uid,
            include_study_endpoints=include_study_endpoints,
        )

        template_uid = template_uid or getattr(template, self.template_uid_property)

        template_vo = self.parametrized_template_vo_class.from_input_values_2(
            template_uid=template_uid,
            parameter_terms=parameter_terms,
            get_final_template_vo_by_template_uid_callback=self._get_template_vo_by_template_uid,
        )

        try:
            library_vo = LibraryVO.from_input_values_2(
                library_name=template.library_name,
                is_library_editable_callback=(
                    lambda name: (
                        cast(
                            LibraryAR, self._repos.library_repository.find_by_name(name)
                        ).is_editable
                        if self._repos.library_repository.find_by_name(name) is not None
                        else None
                    )
                ),
            )
        except ValueError as exc:
            raise NotFoundException(
                f"The library with the name='{template.library_name}' could not be found."
            ) from exc

        item = self.aggregate_class.from_input_values(
            author=self.user_initials,
            template=template_vo,
            library=library_vo,
            generate_uid_callback=self.repository.generate_uid_callback
            if generate_uid_callback is None
            else generate_uid_callback,
        )
        return item

    def create(
        self, template: BaseModel, preview=False, template_uid: Optional[str] = None
    ) -> BaseModel:
        """
        Supports create object action.
        When the preview parameter is set to true, don't create the object, just preview it.
        """
        item = None
        try:
            # Transaction that is performing initial save
            with db.transaction:
                item = self.create_ar_from_input_values(
                    template, template_uid=template_uid
                )
                rep = self.repository

                if (
                    "PreInstance" not in item.__class__.__name__
                    and rep.check_exists_by_name(item.name)
                ):
                    raise BusinessLogicException("The specified object already exists.")
                if not preview:
                    self.repository.save(item)

            return self._transform_aggregate_root_to_pydantic_model(item_ar=item)
        except core.DoesNotExist as exc:
            raise NotFoundException(
                f"The library with the name='{template.library_name}' could not be found."
            ) from exc
        except ValueError as e:
            raise ValidationException(e.args[0]) from e

    def _get_template_vo_by_template_uid(
        self, template_uid: str
    ) -> Optional[TemplateVO]:
        """
        Helper function getting template for given template uid.
        """
        template_ar = self.template_repository.find_by_uid_2(
            template_uid, status=LibraryItemStatus.FINAL
        )
        return template_ar.template_value if template_ar is not None else None

    @db.transaction
    def find_by(self, name: str):
        item = self.repository.find_by(name=name)
        return self._transform_aggregate_root_to_pydantic_model(item)

    @db.transaction
    def edit_draft(self, uid, template: BaseModel):
        """
        Supports edit draft action
        """
        try:
            item: ParametrizedTemplateARBase = self._find_by_uid_or_raise_not_found(
                uid, for_update=True
            )
            parameter_terms = self._create_parameter_entries(
                template, template_uid=item.template_uid
            )

            try:
                template_vo = self.parametrized_template_vo_class.from_input_values_2(
                    template_uid=item.template_uid,
                    parameter_terms=parameter_terms,
                    get_final_template_vo_by_template_uid_callback=self._get_template_vo_by_template_uid,
                )
            except ValueError as e:
                raise ValidationException(e.args[0]) from e
            item.edit_draft(
                author=self.user_initials,
                change_description=template.change_description,
                template=template_vo,
            )
            self.repository.save(item)
            return self._transform_aggregate_root_to_pydantic_model(item)
        except VersioningException as e:
            raise BusinessLogicException(e.msg) from e

    def create_new_version(self, uid: str, template: BaseModel) -> BaseModel:
        """
        Create new version is not allowed for objects derived from templates.
        Only cascading update can do that
        """
        raise NotImplementedError("You cannot create new version")

    @db.transaction
    def get_parameters(
        self,
        uid: str,
        study_uid: Optional[str] = None,
        include_study_endpoints: Optional[bool] = False,
    ):
        try:
            parameter_repository = TemplateParameterRepository()
            item = self._find_by_uid_or_raise_not_found(uid)
            parameters = self.template_repository.get_parameters_including_terms(
                item.template_uid,
                study_uid=study_uid,
                include_study_endpoints=include_study_endpoints,
            )
            return process_complex_parameters(parameters, parameter_repository)
        except core.DoesNotExist as exc:
            raise NotFoundException(
                f"The object  with uid='{uid}' could not be found."
            ) from exc

    def _create_parameter_entries(
        self,
        template,
        template_uid: Optional[str] = None,
        study_uid: Optional[str] = None,
        include_study_endpoints: Optional[bool] = False,
    ) -> Sequence[ParameterTermEntryVO]:
        """
        Creates sequence of Parameter Term Entries that is used in aggregate. These contain:
        parameter name, conjunctions, uids, and terms of parameters
        """
        if template_uid is None:
            template_uid = getattr(template, self.template_uid_property)
        parameter_terms = []
        self._allowed_parameters = (
            self.template_repository.get_parameters_including_terms(
                template_uid,
                study_uid=study_uid,
                include_study_endpoints=include_study_endpoints,
            )
        )
        parameter: TemplateParameterMultiSelectInput
        idx = 0
        for _, allowed_parameter in enumerate(self._allowed_parameters):
            if allowed_parameter.get(
                "definition"
            ):  # What is this check? Is this a different way of writing allowed_parameter != CTTerm?
                param_names = extract_parameters(allowed_parameter["template"])
                params = []
                for param_name in param_names:
                    parameter = template.parameter_terms[idx]
                    if param_name != "NumericValue":
                        tp = SimpleParameterTermVO(
                            uid=parameter.terms[0].uid, value=parameter.terms[0].name
                        )
                    else:
                        tp = NumericParameterTermVO(
                            uid="", value=template.parameter_terms[idx].value
                        )
                    idx += 1
                    params.append(tp)
                parameter_terms.append(
                    ComplexParameterTerm(
                        uid=allowed_parameter.get("definition"),
                        parameter_template=allowed_parameter["template"],
                        parameters=params,
                    )
                )
            else:
                parameter = template.parameter_terms[idx]
                uids = []

                if len(parameter.terms) == 0:
                    # If we have an empty paremeter value selection, send an empty list with default type fro the allowed parameters.
                    pve = ParameterTermEntryVO.from_input_values(
                        parameter_exists_callback=self._repos.parameter_repository.parameter_name_exists,
                        conjunction_exists_callback=lambda _: True,  # TODO: provide proper callback here
                        parameter_term_uid_exists_for_parameter_callback=(
                            lambda p_name, v_uid, p_value: (
                                self._repos.parameter_repository.is_parameter_term_uid_valid_for_parameter_name(
                                    parameter_term_uid=v_uid,
                                    parameter_name=p_name,
                                )
                            )
                        ),
                        parameter_name=allowed_parameter[
                            "name"
                        ],  # Item is used out of context of the for-loop
                        conjunction=parameter.conjunction,
                        parameters=uids,
                    )
                    parameter_terms.append(pve)
                    idx += 1
                else:
                    # Else, iterate over the provided values, store them and their type dynamically.
                    for item in parameter.terms:
                        pv = SimpleParameterTermVO.from_input_values(
                            parameter_term_by_uid_lookup_callback=self._get_parameter_term,
                            uid=item.uid,
                        )
                        uids.append(pv)
                    pve = ParameterTermEntryVO.from_input_values(
                        parameter_exists_callback=self._repos.parameter_repository.parameter_name_exists,
                        conjunction_exists_callback=lambda _: True,  # TODO: provide proper callback here
                        parameter_term_uid_exists_for_parameter_callback=(
                            lambda p_name, v_uid, p_value: (
                                self._repos.parameter_repository.is_parameter_term_uid_valid_for_parameter_name(
                                    parameter_term_uid=v_uid,
                                    parameter_name=p_name,
                                )
                            )
                        ),
                        # pylint:disable=undefined-loop-variable
                        parameter_name=item.type,
                        conjunction=parameter.conjunction,
                        parameters=uids,
                    )
                    parameter_terms.append(pve)
                    idx += 1
        return parameter_terms

    @db.transaction
    def get_referencing_studies(
        self, uid: str, node_type: core.NodeMeta, fields: Optional[str] = ""
    ) -> Sequence[Study]:
        studies = self.study_repository.find_all_by_library_item_uid(
            uid=uid, library_item_type=node_type, sort_by={"uid": True}
        ).items

        study_service = StudyService(user=self.user_initials)
        return_items = [
            study_service._models_study_from_study_definition_ar(
                study_definition_ar=item,
                find_project_by_project_number=self._repos.project_repository.find_by_project_number,
                find_clinical_programme_by_uid=self._repos.clinical_programme_repository.find_by_uid,
                find_all_study_time_units=self._repos.unit_definition_repository.find_all,
                fields=fields,
            )
            for item in studies
        ]
        return return_items

    @db.transaction
    def get_releases_referenced_by_any_study(self) -> Sequence[BaseModel]:
        items = self.repository.find_instances_referenced_by_any_study()
        return [
            self._transform_aggregate_root_to_pydantic_model(item) for item in items
        ]