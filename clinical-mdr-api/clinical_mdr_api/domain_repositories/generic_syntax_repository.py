import abc
from typing import Dict, Sequence, TypeVar

from clinical_mdr_api.domain.library.parameter_term import (
    ComplexParameterTerm,
    NumericParameterTermVO,
    ParameterTermEntryVO,
    SimpleParameterTermVO,
)
from clinical_mdr_api.domain.versioned_object_aggregate import (
    LibraryItemAggregateRootBase,
)
from clinical_mdr_api.domain_repositories.library_item_repository import (
    LibraryItemRepositoryImplBase,
)
from clinical_mdr_api.domain_repositories.models.activities import (
    ActivityGroupRoot,
    ActivityRoot,
    ActivitySubGroupRoot,
)
from clinical_mdr_api.domain_repositories.models.concepts import (
    NumericValue,
    NumericValueRoot,
)
from clinical_mdr_api.domain_repositories.models.controlled_terminology import (
    CTTermRoot,
)
from clinical_mdr_api.domain_repositories.models.dictionary import DictionaryTermRoot
from clinical_mdr_api.domain_repositories.models.template_parameter import (
    ParameterTemplateRoot,
    TemplateParameterComplexRoot,
    TemplateParameterComplexValue,
    TemplateParameterTermRoot,
)

_AggregateRootType = TypeVar("_AggregateRootType", bound=LibraryItemAggregateRootBase)


class GenericSyntaxRepository(
    LibraryItemRepositoryImplBase[_AggregateRootType], abc.ABC
):
    def _maintain_complex_parameter(self, parameter_config: ComplexParameterTerm):
        complex_value = TemplateParameterComplexValue.nodes.get_or_none(
            name=parameter_config.value
        )
        if complex_value is None:
            root: TemplateParameterComplexRoot = TemplateParameterComplexRoot(
                is_active_parameter=True
            )
            root.save()
            complex_value = TemplateParameterComplexValue(name=parameter_config.value)
            complex_value.save()
            root.latest_final.connect(complex_value)
            root.has_latest_value.connect(complex_value)
            parameter_root = ParameterTemplateRoot.get(uid=parameter_config.uid)
            root.has_complex_value.connect(parameter_root)
            template_root = ParameterTemplateRoot.nodes.get(uid=parameter_config.uid)
            tp = template_root.has_definition.get()
            root.has_parameter_term.connect(tp)
        else:
            root_uid = complex_value.get_root_uid_by_latest()
            root = TemplateParameterComplexRoot.nodes.get(uid=root_uid)
        for i, param in enumerate(parameter_config.parameters):
            param_uid = param.uid
            if isinstance(param, NumericParameterTermVO):
                v = NumericValue.nodes.get_or_none(name=param.value)
                if not v:
                    r = NumericValueRoot(uid="NumericValue_" + str(param.value))
                    r.save()
                    v = NumericValue(name=param.value)
                    v.save()
                    r.latest_final.connect(v, {})
                    r.has_latest_value.connect(v)
                    r = r.uid
                else:
                    r = v.get_root_uid_by_latest()
                param_uid = r
            tptr = TemplateParameterTermRoot.nodes.get(uid=param_uid)
            complex_value.uses_parameter.connect(tptr, {"position": i + 1})
        return root.id

    def _parse_parameter_terms(
        self, instance_parameters
    ) -> Dict[int, Sequence[ParameterTermEntryVO]]:
        # Note that this method is used both by templates for default values and instances for values
        # Hence the checks we have to make on the existence of the set_number property
        parameter_strings = []
        # First, parse results from the database
        for position_parameters in instance_parameters:
            position, param_name, param_terms, _ = position_parameters
            if len(param_terms) == 0:
                # If we find an empty (NA) parameter term, temporary save a none object that will be replaced later
                parameter_strings.append(
                    {
                        "set_number": 0,
                        "position": position,
                        "index": None,
                        "definition": None,
                        "template": None,
                        "parameter_uid": None,
                        "parameter_term": None,
                        "parameter_name": param_name,
                    }
                )

            for parameter in param_terms:
                parameter_strings.append(
                    {
                        "set_number": parameter["set_number"]
                        if "set_number" in parameter
                        else 0,
                        "position": parameter["position"],
                        "index": parameter["index"],
                        "parameter_name": parameter["parameter_name"],
                        "parameter_term": parameter["parameter_term"],
                        "parameter_uid": parameter["parameter_uid"],
                        "definition": parameter["definition"],
                        "template": parameter["template"],
                    }
                )

        # Then, start building the nested dictionary to group parameter terms in a list
        data_dict = {}
        # Create the first two levels, like
        # set_number
        # --> position
        for param in parameter_strings:
            if param["set_number"] not in data_dict:
                data_dict[param["set_number"]] = {}
            data_dict[param["set_number"]][param["position"]] = {
                "parameter_name": param["parameter_name"],
                "definition": param["definition"],
                "template": param["template"],
                "parameter_uids": [],
                "conjunction": next(
                    filter(
                        lambda x, param=param: x[0] == param["position"]
                        and (
                            len(x[2]) == 0
                            or (
                                "set_number" in x[2][0]
                                and x[2][0]["set_number"] == param["set_number"]
                            )
                        ),
                        instance_parameters,
                    )
                )[3],
            }

        # Then, unwind to create the third level, like:
        # set_number
        # --> position
        # -----> [parameter_uids]
        for param in parameter_strings:
            data_dict[param["set_number"]][param["position"]]["parameter_uids"].append(
                {
                    "index": param["index"],
                    "parameter_uid": param["parameter_uid"],
                    "parameter_name": param["parameter_name"],
                    "parameter_term": param["parameter_term"],
                }
            )

        # Finally, convert the nested dictionary to a list of ParameterTermEntryVO objects, grouped by value set
        return_dict = {}
        for set_number, term_set in data_dict.items():
            term_set = [x[1] for x in sorted(term_set.items(), key=lambda x: x[0])]
            parameter_list = []
            for item in term_set:
                term_list = []
                if item.get("definition"):
                    tpcr = TemplateParameterComplexRoot.nodes.get(
                        uid=item["parameter_uids"][0]["parameter_uid"]
                    )
                    defr: ParameterTemplateRoot = tpcr.has_complex_value.get()
                    tpcv: TemplateParameterComplexValue = tpcr.latest_final.get()
                    items = tpcv.get_all()
                    cpx_params = []
                    param_terms = []
                    for itemp in items:
                        param_terms.append(
                            {
                                "position": itemp[2],
                                "value": itemp[3],
                                "vv": itemp[4],
                                "item": itemp[1],
                            }
                        )
                    param_terms = sorted(param_terms, key=lambda x: x["position"])
                    for param in param_terms:
                        if param["value"] is not None:
                            tp = NumericParameterTermVO(
                                uid=param["item"], value=param["value"]
                            )
                        else:
                            tp = SimpleParameterTermVO(
                                uid=param["item"], value=param["vv"]
                            )
                        cpx_params.append(tp)
                    parameter_list.append(
                        ComplexParameterTerm(
                            uid=defr.uid,
                            parameter_template=item["template"],
                            parameters=cpx_params,
                        )
                    )
                else:
                    for value in sorted(
                        item["parameter_uids"],
                        key=lambda x: x["index"] or 0,
                    ):
                        if value["parameter_uid"]:
                            pv = self._parameter_from_repository_values(value)
                            term_list.append(pv)
                    pve = ParameterTermEntryVO.from_repository_values(
                        parameters=term_list,
                        parameter_name=item["parameter_name"],
                        conjunction=item.get("conjunction", ""),
                    )
                    parameter_list.append(pve)
            return_dict[set_number] = parameter_list
        return return_dict

    def _parameter_from_repository_values(self, value):
        pv = SimpleParameterTermVO.from_repository_values(
            uid=value["parameter_uid"], value=value["parameter_term"]
        )
        return pv

    def _get_indication(self, uid: str) -> DictionaryTermRoot:
        # Finds indication in database based on root node uid
        return DictionaryTermRoot.nodes.get(uid=uid)

    def _get_category(self, uid: str) -> CTTermRoot:
        # Finds category in database based on root node uid
        return CTTermRoot.nodes.get(uid=uid)

    def _get_activity(self, uid: str) -> ActivityRoot:
        # Finds activity in database based on root node uid
        return ActivityRoot.nodes.get(uid=uid)

    def _get_activity_group(self, uid: str) -> ActivityGroupRoot:
        # Finds activity group in database based on root node uid
        return ActivityGroupRoot.nodes.get(uid=uid)

    def _get_activity_subgroup(self, uid: str) -> ActivitySubGroupRoot:
        # Finds activity sub group in database based on root node uid
        return ActivitySubGroupRoot.nodes.get(uid=uid)

    def _get_criteria_type(self, uid: str) -> CTTermRoot:
        # Finds criteria type in database based on root node uid
        return CTTermRoot.nodes.get(uid=uid)

    def patch_indications(self, uid: str, indication_uids: Sequence[str]) -> None:
        root = self.root_class.nodes.get(uid=uid)
        root.has_indication.disconnect_all()
        for indication in indication_uids:
            indication = self._get_indication(indication)
            root.has_indication.connect(indication)

    def patch_categories(self, uid: str, category_uids: Sequence[str]) -> None:
        root = self.root_class.nodes.get(uid=uid)
        root.has_category.disconnect_all()
        for category in category_uids:
            category = self._get_category(category)
            root.has_category.connect(category)

    def patch_subcategories(self, uid: str, sub_category_uids: Sequence[str]) -> None:
        root = self.root_class.nodes.get(uid=uid)
        root.has_subcategory.disconnect_all()
        for sub_category in sub_category_uids:
            sub_category = self._get_category(sub_category)
            root.has_subcategory.connect(sub_category)

    def patch_activities(self, uid: str, activity_uids: Sequence[str]) -> None:
        root = self.root_class.nodes.get(uid=uid)
        root.has_activity.disconnect_all()
        for activity in activity_uids:
            activity = self._get_activity(activity)
            root.has_activity.connect(activity)

    def patch_activity_groups(
        self, uid: str, activity_group_uids: Sequence[str]
    ) -> None:
        root = self.root_class.nodes.get(uid=uid)
        root.has_activity_group.disconnect_all()
        for group in activity_group_uids:
            group = self._get_activity_group(group)
            root.has_activity_group.connect(group)

    def patch_activity_subgroups(
        self, uid: str, activity_subgroup_uids: Sequence[str]
    ) -> None:
        root = self.root_class.nodes.get(uid=uid)
        root.has_activity_subgroup.disconnect_all()
        for group in activity_subgroup_uids:
            sub_group = self._get_activity_subgroup(group)
            root.has_activity_subgroup.connect(sub_group)