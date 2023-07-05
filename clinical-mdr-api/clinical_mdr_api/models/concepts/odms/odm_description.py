from typing import Callable, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from clinical_mdr_api.domains.concepts.concept_base import ConceptARBase
from clinical_mdr_api.domains.concepts.odms.description import OdmDescriptionAR
from clinical_mdr_api.models.concepts.concept import (
    ConceptModel,
    ConceptPatchInput,
    ConceptPostInput,
)
from clinical_mdr_api.models.error import BatchErrorResponse


class OdmDescription(ConceptModel):
    language: str
    description: Optional[str] = Field(None, nullable=True)
    instruction: Optional[str] = Field(None, nullable=True)
    sponsor_instruction: Optional[str] = Field(None, nullable=True)
    possible_actions: List[str]

    @classmethod
    def from_odm_description_ar(
        cls, odm_description_ar: OdmDescriptionAR
    ) -> "OdmDescription":
        return cls(
            uid=odm_description_ar._uid,
            name=odm_description_ar.name,
            language=odm_description_ar.concept_vo.language,
            description=odm_description_ar.concept_vo.description,
            instruction=odm_description_ar.concept_vo.instruction,
            sponsor_instruction=odm_description_ar.concept_vo.sponsor_instruction,
            library_name=odm_description_ar.library.name,
            start_date=odm_description_ar.item_metadata.start_date,
            end_date=odm_description_ar.item_metadata.end_date,
            status=odm_description_ar.item_metadata.status.value,
            version=odm_description_ar.item_metadata.version,
            change_description=odm_description_ar.item_metadata.change_description,
            user_initials=odm_description_ar.item_metadata.user_initials,
            possible_actions=sorted(
                [_.value for _ in odm_description_ar.get_possible_actions()]
            ),
        )


class OdmDescriptionSimpleModel(BaseModel):
    @classmethod
    def from_odm_description_uid(
        cls,
        uid: str,
        find_odm_description_by_uid: Callable[[str], Optional[ConceptARBase]],
    ) -> Optional["OdmDescriptionSimpleModel"]:
        if uid is not None:
            odm_description = find_odm_description_by_uid(uid)

            if odm_description is not None:
                simple_odm_description_model = cls(
                    uid=uid,
                    name=odm_description.concept_vo.name,
                    language=odm_description.concept_vo.language,
                    description=odm_description.concept_vo.description,
                    instruction=odm_description.concept_vo.instruction,
                    sponsor_instruction=odm_description.concept_vo.sponsor_instruction,
                    version=odm_description.item_metadata.version,
                )
            else:
                simple_odm_description_model = cls(
                    uid=uid,
                    name=None,
                    language=None,
                    description=None,
                    instruction=None,
                    sponsor_instruction=None,
                    version=None,
                )
        else:
            simple_odm_description_model = None
        return simple_odm_description_model

    uid: str = Field(..., title="uid", description="")
    name: Optional[str] = Field(None, title="name", description="", nullable=True)
    language: Optional[str] = Field(
        None, title="language", description="", nullable=True
    )
    description: Optional[str] = Field(
        None, title="description", description="", nullable=True
    )
    instruction: Optional[str] = Field(
        None, title="instruction", description="", nullable=True
    )
    sponsor_instruction: Optional[str] = Field(
        None, title="sponsor_instruction", description="", nullable=True
    )
    version: Optional[str] = Field(None, title="version", description="", nullable=True)


class OdmDescriptionPostInput(ConceptPostInput):
    language: str
    description: Optional[str]
    instruction: Optional[str]
    sponsor_instruction: Optional[str]


class OdmDescriptionPatchInput(ConceptPatchInput):
    language: Optional[str]
    description: Optional[str]
    instruction: Optional[str]
    sponsor_instruction: Optional[str]


class OdmDescriptionBatchPatchInput(OdmDescriptionPatchInput):
    uid: str


class OdmDescriptionBatchInput(BaseModel):
    method: str = Field(
        ..., title="method", description="HTTP method corresponding to operation type"
    )
    content: Union[OdmDescriptionBatchPatchInput, OdmDescriptionPostInput]


class OdmDescriptionBatchOutput(BaseModel):
    response_code: int = Field(
        ...,
        title="response_code",
        description="The HTTP response code related to input operation",
    )
    content: Union[OdmDescription, None, BatchErrorResponse]


class OdmDescriptionVersion(OdmDescription):
    """
    Class for storing OdmDescription and calculation of differences
    """

    changes: Optional[Dict[str, bool]] = Field(
        None,
        description=(
            "Denotes whether or not there was a change in a specific field/property compared to the previous version. "
            "The field names in this object here refer to the field names of the objective (e.g. name, start_date, ..)."
        ),
        nullable=True,
    )