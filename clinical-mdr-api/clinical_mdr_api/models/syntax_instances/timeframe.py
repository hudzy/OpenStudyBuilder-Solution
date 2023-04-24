from datetime import datetime
from typing import Dict, List, Optional

from pydantic import Field

from clinical_mdr_api.domain._utils import extract_parameters
from clinical_mdr_api.domain.syntax_instances.timeframe import TimeframeAR
from clinical_mdr_api.models.library import Library
from clinical_mdr_api.models.syntax_templates.timeframe_template import (
    TimeframeTemplateNameUid,
)
from clinical_mdr_api.models.template_parameter_multi_select_input import (
    TemplateParameterMultiSelectInput,
)
from clinical_mdr_api.models.template_parameter_term import (
    IndexedTemplateParameterTerm,
    MultiTemplateParameterTerm,
    TemplateParameterComplexValue,
)
from clinical_mdr_api.models.utils import BaseModel


class Timeframe(BaseModel):
    uid: Optional[str] = None
    name: Optional[str] = None
    name_plain: Optional[str] = None

    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: Optional[str] = None
    version: Optional[str] = None
    change_description: Optional[str] = None
    user_initials: Optional[str] = None

    possible_actions: Optional[List[str]] = Field(
        None,
        description=(
            "Holds those actions that can be performed on the timeframe. "
            "Actions are: 'approve', 'edit', 'inactivate', 'reactivate' and 'delete'."
        ),
    )

    timeframe_template: Optional[TimeframeTemplateNameUid]
    parameter_terms: Optional[List[MultiTemplateParameterTerm]] = Field(
        None,
        description="Holds the parameter terms that are used within the timeframe. The terms are ordered as they occur in the timeframe name.",
    )
    library: Optional[Library] = None
    study_count: Optional[int] = Field(
        None, description="Count of studies referencing endpoint"
    )

    @classmethod
    def from_timeframe_ar(cls, timeframe_ar: TimeframeAR) -> "Timeframe":
        parameter_terms: List[MultiTemplateParameterTerm] = []
        for position, parameter in enumerate(timeframe_ar.get_parameters()):
            terms: List[IndexedTemplateParameterTerm] = []
            if (
                hasattr(parameter, "parameter_template")
                and parameter.parameter_template is not None
            ):
                # This branch of the code is called if particular parameter of parameter list uses parameter template
                # If yes the abstraction of complex parameter is created to allow UI to recreate ParameterTemplate
                # with related parameter templates. So the definition of parameter template is sent along with parameters.
                param_names = extract_parameters(parameter.parameter_template)
                param_list = []
                for i, param_name in enumerate(param_names):
                    param_term = parameter.parameters[i]
                    pp = IndexedTemplateParameterTerm(
                        name=param_term.value,
                        uid=param_term.uid,
                        index=1,
                        type=param_name,
                    )
                    param_list.append(pp)
                pv = TemplateParameterComplexValue(
                    position=position + 1,
                    conjunction="",
                    terms=param_list,
                    format_string=parameter.parameter_template,
                )
                parameter_terms.append(pv)
            else:
                # Regular way of handling simple parameters for object
                for index, parameter_term in enumerate(parameter.parameters):
                    pv = IndexedTemplateParameterTerm(
                        index=index + 1,
                        uid=parameter_term.uid,
                        name=parameter_term.value,
                        type=parameter.parameter_name,
                    )
                    terms.append(pv)
                conjunction = parameter.conjunction

                parameter_terms.append(
                    MultiTemplateParameterTerm(
                        conjunction=conjunction, position=position + 1, terms=terms
                    )
                )
        return cls(
            uid=timeframe_ar.uid,
            name=timeframe_ar.name,
            name_plain=timeframe_ar.name_plain,
            start_date=timeframe_ar.item_metadata.start_date,
            end_date=timeframe_ar.item_metadata.end_date,
            status=timeframe_ar.item_metadata.status.value,
            version=timeframe_ar.item_metadata.version,
            change_description=timeframe_ar.item_metadata.change_description,
            user_initials=timeframe_ar.item_metadata.user_initials,
            possible_actions=sorted(
                {_.value for _ in timeframe_ar.get_possible_actions()}
            ),
            timeframe_template=TimeframeTemplateNameUid(
                name=timeframe_ar.template_name,
                name_plain=timeframe_ar.template_name_plain,
                uid=timeframe_ar.template_uid,
            ),
            library=Library.from_library_vo(timeframe_ar.library),
            parameter_terms=parameter_terms,
            study_count=timeframe_ar.study_count,
        )


class TimeframeVersion(Timeframe):
    """
    Class for storing Timeframes and calculation of differences
    """

    changes: Dict[str, bool] = Field(
        None,
        description=(
            "Denotes whether or not there was a change in a specific field/property compared to the previous version. "
            "The field names in this object here refer to the field names of the timeframe (e.g. name, start_date, ..)."
        ),
    )


class TimeframeParameterInput(BaseModel):
    parameter_terms: List[TemplateParameterMultiSelectInput] = Field(
        None,
        title="parameter_terms",
        description="An ordered list of selected parameter terms that are used to replace the parameters of the timeframe template.",
    )


class TimeframeEditInput(TimeframeParameterInput):
    change_description: str = Field(
        ...,
        description="A short description about what has changed compared to the previous version.",
    )


class TimeframeCreateInput(TimeframeParameterInput):
    timeframe_template_uid: str = Field(
        ...,
        title="timeframe_template_uid",
        description="The unique id of the timeframe template that is used as the basis for the new timeframe.",
    )
    library_name: str = Field(
        None,
        title="library_name",
        description="If specified: The name of the library to which the timeframe will be linked. The following rules apply: \n"
        "* The library needs to be present, it will not be created with this request. The *[GET] /libraries* endpoint can help. And \n"
        "* The library needs to allow the creation: The 'is_editable' property of the library needs to be true. \n\n"
        "If not specified: The library of the timeframe template will be used.",
    )