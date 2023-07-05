from typing import Callable, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from clinical_mdr_api.domains.concepts.activities.activity import ActivityAR
from clinical_mdr_api.domains.concepts.concept_base import ConceptARBase
from clinical_mdr_api.domains.concepts.odms.alias import OdmAliasAR
from clinical_mdr_api.domains.concepts.odms.description import OdmDescriptionAR
from clinical_mdr_api.domains.concepts.odms.item import (
    OdmItemAR,
    OdmItemRefVO,
    OdmItemTermVO,
    OdmItemUnitDefinitionVO,
)
from clinical_mdr_api.domains.concepts.odms.vendor_attribute import (
    OdmVendorAttributeAR,
    OdmVendorAttributeRelationVO,
    OdmVendorElementAttributeRelationVO,
)
from clinical_mdr_api.domains.concepts.odms.vendor_element import (
    OdmVendorElementRelationVO,
)
from clinical_mdr_api.domains.concepts.unit_definitions.unit_definition import (
    UnitDefinitionAR,
)
from clinical_mdr_api.domains.concepts.utils import RelationType
from clinical_mdr_api.domains.controlled_terminologies.ct_codelist_attributes import (
    CTCodelistAttributesAR,
)
from clinical_mdr_api.domains.controlled_terminologies.ct_term_name import CTTermNameAR
from clinical_mdr_api.domains.dictionaries.dictionary_term import DictionaryTermAR
from clinical_mdr_api.models.concepts.activities.activity import (
    ActivityHierarchySimpleModel,
)
from clinical_mdr_api.models.concepts.concept import (
    ConceptModel,
    ConceptPatchInput,
    ConceptPostInput,
)
from clinical_mdr_api.models.concepts.odms.odm_alias import OdmAliasSimpleModel
from clinical_mdr_api.models.concepts.odms.odm_common_models import (
    OdmRefVendor,
    OdmRefVendorAttributeModel,
)
from clinical_mdr_api.models.concepts.odms.odm_description import (
    OdmDescriptionBatchPatchInput,
    OdmDescriptionPostInput,
    OdmDescriptionSimpleModel,
)
from clinical_mdr_api.models.concepts.odms.odm_vendor_attribute import (
    OdmVendorAttributeRelationModel,
    OdmVendorElementAttributeRelationModel,
)
from clinical_mdr_api.models.concepts.odms.odm_vendor_element import (
    OdmVendorElementRelationModel,
)
from clinical_mdr_api.models.controlled_terminologies.ct_codelist_attributes import (
    CTCodelistAttributesSimpleModel,
)
from clinical_mdr_api.models.controlled_terminologies.ct_term import SimpleTermModel


class OdmItemTermRelationshipModel(BaseModel):
    @classmethod
    def from_odm_item_uid(
        cls,
        uid: str,
        term_uid: str,
        find_term_with_item_relation_by_item_uid: Callable[
            [str], Optional[OdmItemTermVO]
        ],
    ) -> Optional["OdmItemTermRelationshipModel"]:
        simple_term_model = None
        if term_uid is not None:
            term = find_term_with_item_relation_by_item_uid(uid=uid, term_uid=term_uid)

            if term is not None:
                simple_term_model = cls(
                    term_uid=term_uid,
                    name=term.name,
                    mandatory=term.mandatory,
                    order=term.order,
                    display_text=term.display_text,
                    version=term.version,
                )
            else:
                simple_term_model = cls(
                    term_uid=term_uid,
                    name=None,
                    mandatory=None,
                    order=None,
                    display_text=None,
                    version=None,
                )
        else:
            simple_term_model = None
        return simple_term_model

    term_uid: str = Field(..., title="term_uid", description="")
    name: Optional[str] = Field(None, title="name", description="")
    mandatory: Optional[bool] = Field(None, title="mandatory", description="")
    order: Optional[int] = Field(None, title="order", description="")
    display_text: Optional[str] = Field(None, title="display_text", description="")
    version: Optional[str] = Field(None, title="version", description="")


class OdmItemUnitDefinitionWithRelationship(BaseModel):
    @classmethod
    def from_unit_definition_uid(
        cls,
        uid: str,
        unit_definition_uid: str,
        find_unit_definition_by_uid: Callable[[str], Optional[ConceptARBase]],
        find_unit_definition_with_item_relation_by_item_uid: Callable[
            [str, str], Optional[OdmItemUnitDefinitionVO]
        ],
        find_dictionary_term_by_uid: Callable[[str], Optional[DictionaryTermAR]],
        find_term_by_uid: Callable[[str], Optional[CTTermNameAR]],
    ) -> Optional["OdmItemUnitDefinitionWithRelationship"]:
        if uid is not None:
            unit_definition_rel = find_unit_definition_with_item_relation_by_item_uid(
                uid, unit_definition_uid
            )
            unit_definition = find_unit_definition_by_uid(unit_definition_uid)

            if unit_definition is not None and unit_definition_rel is not None:
                if unit_definition.concept_vo.ucum_name is None:
                    ucum = SimpleTermModel.from_ct_code(
                        c_code=unit_definition.concept_vo.ucum_uid,
                        find_term_by_uid=find_dictionary_term_by_uid,
                    )
                else:
                    ucum = SimpleTermModel(
                        term_uid=unit_definition.concept_vo.ucum_uid,
                        name=unit_definition.concept_vo.ucum_name,
                    )

                ct_units = []
                for ct_unit in unit_definition.concept_vo.ct_units:
                    if ct_unit.name is None:
                        controlled_terminology_unit = SimpleTermModel.from_ct_code(
                            c_code=ct_unit.uid, find_term_by_uid=find_term_by_uid
                        )
                    else:
                        controlled_terminology_unit = SimpleTermModel(
                            term_uid=ct_unit.uid, name=ct_unit.name
                        )
                    ct_units.append(controlled_terminology_unit)

                simple_unit_definition_model = cls(
                    uid=unit_definition_uid,
                    name=unit_definition.concept_vo.name,
                    mandatory=unit_definition_rel.mandatory,
                    order=unit_definition_rel.order,
                    ucum=ucum,
                    ct_units=ct_units,
                )
            else:
                simple_unit_definition_model = cls(
                    uid=unit_definition_uid,
                    name=None,
                    mandatory=None,
                    order=None,
                    ucum=None,
                    ct_units=[],
                )
        else:
            simple_unit_definition_model = None
        return simple_unit_definition_model

    uid: str = Field(..., title="uid", description="")
    name: Optional[str] = Field(None, title="name", description="")
    mandatory: Optional[bool] = Field(None, title="mandatory", description="")
    order: Optional[int] = Field(None, title="order", description="")
    ucum: Optional[SimpleTermModel] = Field(None, title="ucum", description="")
    ct_units: List[SimpleTermModel] = Field([], title="ucum_name", description="")


class OdmItem(ConceptModel):
    oid: Optional[str]
    prompt: Optional[str] = Field(None, nullable=True)
    datatype: Optional[str] = Field(None, nullable=True)
    length: Optional[int] = Field(None, nullable=True)
    significant_digits: Optional[int] = Field(None, nullable=True)
    sas_field_name: Optional[str] = Field(None, nullable=True)
    sds_var_name: Optional[str] = Field(None, nullable=True)
    origin: Optional[str] = Field(None, nullable=True)
    comment: Optional[str] = Field(None, nullable=True)
    descriptions: List[OdmDescriptionSimpleModel]
    aliases: List[OdmAliasSimpleModel]
    unit_definitions: List[OdmItemUnitDefinitionWithRelationship]
    codelist: Optional[CTCodelistAttributesSimpleModel] = Field(None, nullable=True)
    terms: List[OdmItemTermRelationshipModel]
    activity: Optional[ActivityHierarchySimpleModel] = Field(None, nullable=True)
    vendor_elements: List[OdmVendorElementRelationModel]
    vendor_attributes: List[OdmVendorAttributeRelationModel]
    vendor_element_attributes: List[OdmVendorElementAttributeRelationModel]
    possible_actions: List[str]

    @classmethod
    def from_odm_item_ar(
        cls,
        odm_item_ar: OdmItemAR,
        find_odm_description_by_uid: Callable[[str], Optional[OdmDescriptionAR]],
        find_odm_alias_by_uid: Callable[[str], Optional[OdmAliasAR]],
        find_unit_definition_by_uid: Callable[[str], Optional[UnitDefinitionAR]],
        find_unit_definition_with_item_relation_by_item_uid: Callable[
            [str, str], Optional[OdmItemUnitDefinitionVO]
        ],
        find_dictionary_term_by_uid: Callable[[str], Optional[DictionaryTermAR]],
        find_term_by_uid: Callable[[str], Optional[CTTermNameAR]],
        find_codelist_attribute_by_codelist_uid: Callable[
            [str], Optional[CTCodelistAttributesAR]
        ],
        find_term_with_item_relation_by_item_uid: Callable[
            [str, str], Optional[OdmItemTermVO]
        ],
        find_activity_by_uid: Callable[[str], Optional[ActivityAR]],
        find_odm_vendor_element_by_uid_with_odm_element_relation: Callable[
            [str, str, RelationType], Optional[OdmVendorElementRelationVO]
        ],
        find_odm_vendor_attribute_by_uid_with_odm_element_relation: Callable[
            [str, str, RelationType, bool],
            Union[
                OdmVendorAttributeRelationVO,
                OdmVendorElementAttributeRelationVO,
                None,
            ],
        ],
    ) -> "OdmItem":
        return cls(
            uid=odm_item_ar._uid,
            oid=odm_item_ar.concept_vo.oid,
            name=odm_item_ar.concept_vo.name,
            prompt=odm_item_ar.concept_vo.prompt,
            datatype=odm_item_ar.concept_vo.datatype,
            length=odm_item_ar.concept_vo.length,
            significant_digits=odm_item_ar.concept_vo.significant_digits,
            sas_field_name=odm_item_ar.concept_vo.sas_field_name,
            sds_var_name=odm_item_ar.concept_vo.sds_var_name,
            origin=odm_item_ar.concept_vo.origin,
            comment=odm_item_ar.concept_vo.comment,
            library_name=odm_item_ar.library.name,
            start_date=odm_item_ar.item_metadata.start_date,
            end_date=odm_item_ar.item_metadata.end_date,
            status=odm_item_ar.item_metadata.status.value,
            version=odm_item_ar.item_metadata.version,
            change_description=odm_item_ar.item_metadata.change_description,
            user_initials=odm_item_ar.item_metadata.user_initials,
            descriptions=sorted(
                [
                    OdmDescriptionSimpleModel.from_odm_description_uid(
                        uid=description_uid,
                        find_odm_description_by_uid=find_odm_description_by_uid,
                    )
                    for description_uid in odm_item_ar.concept_vo.description_uids
                ],
                key=lambda item: item.name,
            ),
            aliases=sorted(
                [
                    OdmAliasSimpleModel.from_odm_alias_uid(
                        uid=alias_uid,
                        find_odm_alias_by_uid=find_odm_alias_by_uid,
                    )
                    for alias_uid in odm_item_ar.concept_vo.alias_uids
                ],
                key=lambda item: item.name,
            ),
            unit_definitions=sorted(
                [
                    OdmItemUnitDefinitionWithRelationship.from_unit_definition_uid(
                        uid=odm_item_ar._uid,
                        unit_definition_uid=unit_definition_uid,
                        find_unit_definition_by_uid=find_unit_definition_by_uid,
                        find_unit_definition_with_item_relation_by_item_uid=find_unit_definition_with_item_relation_by_item_uid,
                        find_dictionary_term_by_uid=find_dictionary_term_by_uid,
                        find_term_by_uid=find_term_by_uid,
                    )
                    for unit_definition_uid in odm_item_ar.concept_vo.unit_definition_uids
                ],
                key=lambda item: item.uid,
            ),
            codelist=CTCodelistAttributesSimpleModel.from_codelist_uid(
                uid=odm_item_ar.concept_vo.codelist_uid,
                find_codelist_attribute_by_codelist_uid=find_codelist_attribute_by_codelist_uid,
            ),
            terms=sorted(
                [
                    OdmItemTermRelationshipModel.from_odm_item_uid(
                        uid=odm_item_ar._uid,
                        term_uid=term_uid,
                        find_term_with_item_relation_by_item_uid=find_term_with_item_relation_by_item_uid,
                    )
                    for term_uid in odm_item_ar.concept_vo.term_uids
                ],
                key=lambda item: (item.order is not None, item.order),
            ),
            activity=ActivityHierarchySimpleModel.from_activity_uid(
                uid=odm_item_ar.concept_vo.activity_uid,
                find_activity_by_uid=find_activity_by_uid,
            ),
            vendor_elements=sorted(
                [
                    OdmVendorElementRelationModel.from_uid(
                        uid=vendor_element_uid,
                        odm_element_uid=odm_item_ar._uid,
                        odm_element_type=RelationType.ITEM,
                        find_by_uid_with_odm_element_relation=find_odm_vendor_element_by_uid_with_odm_element_relation,
                    )
                    for vendor_element_uid in odm_item_ar.concept_vo.vendor_element_uids
                ],
                key=lambda item: item.name,
            ),
            vendor_attributes=sorted(
                [
                    OdmVendorAttributeRelationModel.from_uid(
                        uid=vendor_attribute_uid,
                        odm_element_uid=odm_item_ar._uid,
                        odm_element_type=RelationType.ITEM,
                        find_by_uid_with_odm_element_relation=find_odm_vendor_attribute_by_uid_with_odm_element_relation,
                        vendor_element_attribute=False,
                    )
                    for vendor_attribute_uid in odm_item_ar.concept_vo.vendor_attribute_uids
                ],
                key=lambda item: item.name,
            ),
            vendor_element_attributes=sorted(
                [
                    OdmVendorElementAttributeRelationModel.from_uid(
                        uid=vendor_element_attribute_uid,
                        odm_element_uid=odm_item_ar._uid,
                        odm_element_type=RelationType.ITEM,
                        find_by_uid_with_odm_element_relation=find_odm_vendor_attribute_by_uid_with_odm_element_relation,
                    )
                    for vendor_element_attribute_uid in odm_item_ar.concept_vo.vendor_element_attribute_uids
                ],
                key=lambda item: item.name,
            ),
            possible_actions=sorted(
                [_.value for _ in odm_item_ar.get_possible_actions()]
            ),
        )


class OdmItemRefModel(BaseModel):
    @classmethod
    def from_odm_item_uid(
        cls,
        uid: str,
        item_group_uid: str,
        find_odm_item_by_uid_with_item_group_relation: Callable[
            [str, str], Optional[OdmItemRefVO]
        ],
        find_odm_vendor_attribute_by_uid: Callable[
            [str], Optional[OdmVendorAttributeAR]
        ],
    ) -> Optional["OdmItemRefModel"]:
        if uid is not None:
            odm_item_ref_vo = find_odm_item_by_uid_with_item_group_relation(
                uid, item_group_uid
            )

            if odm_item_ref_vo is not None:
                odm_item_ref_model = cls(
                    uid=uid,
                    oid=odm_item_ref_vo.oid,
                    name=odm_item_ref_vo.name,
                    order_number=odm_item_ref_vo.order_number,
                    mandatory=odm_item_ref_vo.mandatory,
                    key_sequence=odm_item_ref_vo.key_sequence,
                    method_oid=odm_item_ref_vo.method_oid,
                    imputation_method_oid=odm_item_ref_vo.imputation_method_oid,
                    role=odm_item_ref_vo.role,
                    role_codelist_oid=odm_item_ref_vo.role_codelist_oid,
                    collection_exception_condition_oid=odm_item_ref_vo.collection_exception_condition_oid,
                    vendor=OdmRefVendor(
                        attributes=[
                            OdmRefVendorAttributeModel.from_uid(
                                uid=attribute["uid"],
                                value=attribute["value"],
                                find_odm_vendor_attribute_by_uid=find_odm_vendor_attribute_by_uid,
                            )
                            for attribute in odm_item_ref_vo.vendor["attributes"]
                        ]
                        if odm_item_ref_vo.vendor
                        else []
                    ),
                )
            else:
                odm_item_ref_model = cls(
                    uid=uid,
                    oid=None,
                    name=None,
                    order_number=None,
                    mandatory=None,
                    key_sequence=None,
                    method_oid=None,
                    imputation_method_oid=None,
                    role=None,
                    role_codelist_oid=None,
                    collection_exception_condition_oid=None,
                    vendor=OdmRefVendor(attributes=[]),
                )
        else:
            odm_item_ref_model = None
        return odm_item_ref_model

    uid: str = Field(..., title="uid", description="")
    oid: Optional[str] = Field(None, title="oid", description="")
    name: Optional[str] = Field(None, title="name", description="")
    order_number: Optional[int] = Field(None, title="order_number", description="")
    mandatory: Optional[str] = Field(None, title="mandatory", description="")
    key_sequence: Optional[str] = Field(None, title="key_sequence", description="")
    method_oid: Optional[str] = Field(None, title="method_oid", description="")
    imputation_method_oid: Optional[str] = Field(
        None, title="imputation_method_oid", description=""
    )
    role: Optional[str] = Field(None, title="role", description="")
    role_codelist_oid: Optional[str] = Field(
        None, title="role_codelist_oid", description=""
    )
    collection_exception_condition_oid: Optional[str] = Field(
        None, title="collection_exception_condition_oid", description=""
    )
    vendor: OdmRefVendor = Field(title="vendor", description="")


class OdmItemTermRelationshipInput(BaseModel):
    uid: str
    mandatory: bool = True
    order: Optional[int] = 999999
    display_text: Optional[str] = None


class OdmItemUnitDefinitionRelationshipInput(BaseModel):
    uid: str
    mandatory: bool = True
    order: Optional[int] = 999999


class OdmItemPostInput(ConceptPostInput):
    oid: Optional[str]
    datatype: str
    prompt: Optional[str]
    length: Optional[int]
    significant_digits: Optional[int] = None
    sas_field_name: Optional[str]
    sds_var_name: Optional[str]
    origin: Optional[str]
    comment: Optional[str] = None
    descriptions: List[Union[OdmDescriptionPostInput, str]]
    alias_uids: List[str]
    codelist_uid: Optional[str]
    unit_definitions: List[OdmItemUnitDefinitionRelationshipInput] = []
    terms: List[OdmItemTermRelationshipInput] = []


class OdmItemPatchInput(ConceptPatchInput):
    oid: Optional[str]
    datatype: Optional[str]
    prompt: Optional[str]
    length: Optional[int]
    significant_digits: Optional[int]
    sas_field_name: Optional[str]
    sds_var_name: Optional[str]
    origin: Optional[str]
    comment: Optional[str]
    descriptions: List[
        Union[OdmDescriptionBatchPatchInput, OdmDescriptionPostInput, str]
    ]
    alias_uids: List[str]
    unit_definitions: List[OdmItemUnitDefinitionRelationshipInput]
    codelist_uid: Optional[str]
    terms: List[OdmItemTermRelationshipInput]


class OdmItemActivityPostInput(BaseModel):
    uid: str


class OdmItemVersion(OdmItem):
    """
    Class for storing OdmItem and calculation of differences
    """

    changes: Optional[Dict[str, bool]] = Field(
        None,
        description=(
            "Denotes whether or not there was a change in a specific field/property compared to the previous version. "
            "The field names in this object here refer to the field names of the objective (e.g. name, start_date, ..)."
        ),
        nullable=True,
    )