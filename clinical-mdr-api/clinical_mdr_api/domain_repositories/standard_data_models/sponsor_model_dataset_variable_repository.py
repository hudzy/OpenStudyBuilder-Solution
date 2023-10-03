from clinical_mdr_api.domain_repositories.library_item_repository import (
    LibraryItemRepositoryImplBase,
)
from clinical_mdr_api.domain_repositories.models._utils import (
    CustomNodeSet,
    to_relation_trees,
)
from clinical_mdr_api.domain_repositories.models.generic import (
    Library,
    VersionRelationship,
)
from clinical_mdr_api.domain_repositories.models.standard_data_model import (
    Dataset,
    DatasetVariable,
    SponsorModelDatasetInstance,
    SponsorModelDatasetVariableInstance,
)
from clinical_mdr_api.domain_repositories.neomodel_ext_item_repository import (
    NeomodelExtBaseRepository,
)
from clinical_mdr_api.domains.standard_data_models.sponsor_model_dataset_variable import (
    SponsorModelDatasetVariableAR,
    SponsorModelDatasetVariableVO,
)
from clinical_mdr_api.domains.versioned_object_aggregate import LibraryVO
from clinical_mdr_api.exceptions import BusinessLogicException
from clinical_mdr_api.models.standard_data_models.sponsor_model_dataset_variable import (
    SponsorModelDatasetVariable,
)


class SponsorModelDatasetVariableRepository(
    NeomodelExtBaseRepository,
    LibraryItemRepositoryImplBase[SponsorModelDatasetVariableAR],
):
    root_class = DatasetVariable
    value_class = SponsorModelDatasetVariableInstance
    return_model = SponsorModelDatasetVariable

    def get_neomodel_extension_query(self) -> CustomNodeSet:
        return (
            DatasetVariable.nodes.fetch_relations(
                "has_sponsor_model_instance__has_variable",
                "has_dataset_variable__has_library",
            )
            # .fetch_optional_relations(
            #     "has_latest_sponsor_model_value__has_activity_item_class"
            # )
            # .fetch_optional_single_relation_of_type(
            #     {
            #         "has_sponsor_model_version": (
            #             "latest_version",
            #             LATEST_VERSION_ORDER_BY,
            #         ),
            #     }
            # )
        )

    def _has_data_changed(
        self,
        ar: SponsorModelDatasetVariableAR,
        value: SponsorModelDatasetVariableInstance,
    ) -> bool:
        return (
            ar.sponsor_model_dataset_variable_vo.is_basic_std != value.is_basic_std
            or ar.sponsor_model_dataset_variable_vo.label != value.label
            # TODO : Get order from relationship because there are re-used instances with only order changing
            # or ar.sponsor_model_dataset_variable_vo.order != value.order
            or ar.sponsor_model_dataset_variable_vo.variable_type != value.variable_type
            or ar.sponsor_model_dataset_variable_vo.length != value.length
            or ar.sponsor_model_dataset_variable_vo.display_format
            != value.display_format
            or ar.sponsor_model_dataset_variable_vo.xml_datatype != value.xml_datatype
            or ar.sponsor_model_dataset_variable_vo.xml_codelist != value.xml_codelist
            or ar.sponsor_model_dataset_variable_vo.xml_codelist_multi
            != value.xml_codelist_multi
            or ar.sponsor_model_dataset_variable_vo.core != value.core
            or ar.sponsor_model_dataset_variable_vo.origin != value.origin
            or ar.sponsor_model_dataset_variable_vo.role != value.role
            or ar.sponsor_model_dataset_variable_vo.term != value.term
            or ar.sponsor_model_dataset_variable_vo.algorithm != value.algorithm
            or ar.sponsor_model_dataset_variable_vo.qualifiers != value.qualifiers
            or ar.sponsor_model_dataset_variable_vo.comment != value.comment
            or ar.sponsor_model_dataset_variable_vo.ig_comment != value.ig_comment
            or ar.sponsor_model_dataset_variable_vo.class_table != value.class_table
            or ar.sponsor_model_dataset_variable_vo.class_column != value.class_column
            or ar.sponsor_model_dataset_variable_vo.map_var_flag != value.map_var_flag
            or ar.sponsor_model_dataset_variable_vo.fixed_mapping != value.fixed_mapping
            or ar.sponsor_model_dataset_variable_vo.include_in_raw
            != value.include_in_raw
            or ar.sponsor_model_dataset_variable_vo.nn_internal != value.nn_internal
            or ar.sponsor_model_dataset_variable_vo.value_lvl_where_cols
            != value.value_lvl_where_cols
            or ar.sponsor_model_dataset_variable_vo.value_lvl_label_col
            != value.value_lvl_label_col
            or ar.sponsor_model_dataset_variable_vo.value_lvl_collect_ct_val
            != value.value_lvl_collect_ct_val
            or ar.sponsor_model_dataset_variable_vo.value_lvl_ct_codelist_id_col
            != value.value_lvl_ct_codelist_id_col
            or ar.sponsor_model_dataset_variable_vo.enrich_build_order
            != value.enrich_build_order
            or ar.sponsor_model_dataset_variable_vo.enrich_rule != value.enrich_rule
            or ar.sponsor_model_dataset_variable_vo.xml_codelist_values
            != value.xml_codelist_values
        )

    def _create(
        self, item: SponsorModelDatasetVariableAR
    ) -> SponsorModelDatasetVariableAR:
        """
        Overrides generic LibraryItemRepository method
        """
        root = DatasetVariable.nodes.get_or_none(uid=item.uid)

        if root is None:
            root = DatasetVariable(uid=item.uid).save()

        instance = self._get_or_create_instance(root=root, ar=item)

        # Connect with SponsorModelDatasetInstance
        parent_dataset_instance = to_relation_trees(
            SponsorModelDatasetInstance.nodes.filter(
                is_instance_of__uid=item.sponsor_model_dataset_variable_vo.dataset_uid,
                has_dataset__name=item.sponsor_model_dataset_variable_vo.sponsor_model_name,
            )
        )
        if parent_dataset_instance:
            instance.has_variable.connect(
                parent_dataset_instance[0],
                {
                    "ordinal": item.sponsor_model_dataset_variable_vo.order,
                    "version_number": item.sponsor_model_dataset_variable_vo.sponsor_model_version_number,
                },
            )
        else:
            raise BusinessLogicException(
                f"The Dataset {item.sponsor_model_dataset_variable_vo.dataset_uid} is not instantiated in this version of the sponsor model."
            )

        return item

    def _get_or_create_instance(
        self, root: DatasetVariable, ar: SponsorModelDatasetVariableAR
    ) -> SponsorModelDatasetVariableInstance:
        for itm in root.has_sponsor_model_instance.all():
            if not self._has_data_changed(ar, itm):
                return itm

        new_instance = SponsorModelDatasetVariableInstance(
            is_basic_std=ar.sponsor_model_dataset_variable_vo.is_basic_std,
            label=ar.sponsor_model_dataset_variable_vo.label,
            variable_type=ar.sponsor_model_dataset_variable_vo.variable_type,
            length=ar.sponsor_model_dataset_variable_vo.length,
            display_format=ar.sponsor_model_dataset_variable_vo.display_format,
            xml_datatype=ar.sponsor_model_dataset_variable_vo.xml_datatype,
            xml_codelist=ar.sponsor_model_dataset_variable_vo.xml_codelist,
            xml_codelist_multi=ar.sponsor_model_dataset_variable_vo.xml_codelist_multi,
            core=ar.sponsor_model_dataset_variable_vo.core,
            origin=ar.sponsor_model_dataset_variable_vo.origin,
            role=ar.sponsor_model_dataset_variable_vo.role,
            term=ar.sponsor_model_dataset_variable_vo.term,
            algorithm=ar.sponsor_model_dataset_variable_vo.algorithm,
            qualifiers=ar.sponsor_model_dataset_variable_vo.qualifiers,
            comment=ar.sponsor_model_dataset_variable_vo.comment,
            ig_comment=ar.sponsor_model_dataset_variable_vo.ig_comment,
            class_table=ar.sponsor_model_dataset_variable_vo.class_table,
            class_column=ar.sponsor_model_dataset_variable_vo.class_column,
            map_var_flag=ar.sponsor_model_dataset_variable_vo.map_var_flag,
            fixed_mapping=ar.sponsor_model_dataset_variable_vo.fixed_mapping,
            include_in_raw=ar.sponsor_model_dataset_variable_vo.include_in_raw,
            nn_internal=ar.sponsor_model_dataset_variable_vo.nn_internal,
            value_lvl_where_cols=ar.sponsor_model_dataset_variable_vo.value_lvl_where_cols,
            value_lvl_label_col=ar.sponsor_model_dataset_variable_vo.value_lvl_label_col,
            value_lvl_collect_ct_val=ar.sponsor_model_dataset_variable_vo.value_lvl_collect_ct_val,
            value_lvl_ct_codelist_id_col=ar.sponsor_model_dataset_variable_vo.value_lvl_ct_codelist_id_col,
            enrich_build_order=ar.sponsor_model_dataset_variable_vo.enrich_build_order,
            enrich_rule=ar.sponsor_model_dataset_variable_vo.enrich_rule,
            xml_codelistvalues=ar.sponsor_model_dataset_variable_vo.xml_codelist_values,
        )
        self._db_save_node(new_instance)

        # Connect with root
        root.has_sponsor_model_instance.connect(new_instance)

        return new_instance

    def _create_aggregate_root_instance_from_version_root_relationship_and_value(
        self,
        *,
        root: DatasetVariable,
        library: Library,
        relationship: VersionRelationship,
        value: SponsorModelDatasetVariableInstance,
    ) -> SponsorModelDatasetVariableAR:
        dataset_value: SponsorModelDatasetInstance = value.has_variable.get_or_none()
        dataset_uid = None
        if dataset_value is not None:
            dataset: Dataset = dataset_value.has_sponsor_model_instance.single()
            if dataset is not None:
                dataset_uid = dataset.uid
        return SponsorModelDatasetVariableAR.from_repository_values(
            variable_uid=root.uid,
            sponsor_model_dataset_variable_vo=SponsorModelDatasetVariableVO.from_repository_values(
                dataset_uid=dataset_uid,
                variable_uid=root.uid,
                sponsor_model_name=None,
                sponsor_model_version_number=None,
                is_basic_std=value.is_basic_std,
                label=value.label,
                order=value.order,
                variable_type=value.variable_type,
                length=value.length,
                display_format=value.display_format,
                xml_datatype=value.xml_datatype,
                xml_codelist=value.xml_codelist,
                xml_codelist_multi=value.xml_codelist_multi,
                core=value.core,
                origin=value.origin,
                role=value.role,
                term=value.term,
                algorithm=value.algorithm,
                qualifiers=value.qualifiers,
                comment=value.comment,
                ig_comment=value.ig_comment,
                class_table=value.class_table,
                class_column=value.class_column,
                map_var_flag=value.map_var_flag,
                fixed_mapping=value.fixed_mapping,
                include_in_raw=value.include_in_raw,
                nn_internal=value.nn_internal,
                value_lvl_where_cols=value.value_lvl_where_cols,
                value_lvl_label_col=value.value_lvl_label_col,
                value_lvl_collect_ct_val=value.value_lvl_collect_ct_val,
                value_lvl_ct_codelist_id_col=value.value_lvl_ct_codelist_id_col,
                enrich_build_order=value.enrich_build_order,
                enrich_rule=value.enrich_rule,
                xml_codelist_values=value.xml_codelist_values,
            ),
            library=LibraryVO.from_input_values_2(
                library_name=library.name,
                is_library_editable_callback=(lambda _: library.is_editable),
            ),
            item_metadata=self._library_item_metadata_vo_from_relation(relationship),
        )

    def _maintain_parameters(
        self,
        versioned_object: SponsorModelDatasetVariableAR,
        root: DatasetVariable,
        value: SponsorModelDatasetVariableInstance,
    ) -> None:
        pass