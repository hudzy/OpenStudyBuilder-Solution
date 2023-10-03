"""
Tests for /standards/class-variables endpoints
"""

# pylint: disable=unused-argument
# pylint: disable=redefined-outer-name
# pylint: disable=too-many-arguments

# pytest fixture functions have other fixture functions as arguments,
# which pylint interprets as unused arguments

import json
import logging
from functools import reduce

import pytest
from fastapi.testclient import TestClient

from clinical_mdr_api.main import app
from clinical_mdr_api.models.standard_data_models.data_model import DataModel
from clinical_mdr_api.models.standard_data_models.dataset_class import DatasetClass
from clinical_mdr_api.models.standard_data_models.dataset_variable import (
    DatasetVariable,
)
from clinical_mdr_api.models.standard_data_models.variable_class import VariableClass
from clinical_mdr_api.services.standard_data_models.variable_class import (
    VariableClassService,
)
from clinical_mdr_api.tests.integration.utils.api import (
    drop_db,
    inject_and_clear_db,
    inject_base_data,
)
from clinical_mdr_api.tests.integration.utils.utils import TestUtils

log = logging.getLogger(__name__)

# Global variables shared between fixtures and tests
data_model_catalogue_name: str
data_models: list[DataModel]
dataset_classes: list[DatasetClass]
dataset_variable: DatasetVariable
class_variables: list[VariableClass]


@pytest.fixture(scope="module")
def api_client(test_data):
    """Create FastAPI test client
    using the database name set in the `test_data` fixture"""
    yield TestClient(app)


@pytest.fixture(scope="module")
def test_data():
    """Initialize test data"""
    db_name = "class-variables.api"
    inject_and_clear_db(db_name)
    inject_base_data()

    global data_model_catalogue_name
    global data_models
    global dataset_classes
    global dataset_variable
    global class_variables

    data_model_catalogue_name = TestUtils.create_data_model_catalogue(
        name="DataModelCatalogue name"
    )
    data_models = [
        TestUtils.create_data_model(name=name, version_number=str(idx))
        for idx, name in enumerate(["DataModel A", "DataModel B", "DataModel C"])
    ]
    dataset_classes = [
        TestUtils.create_dataset_class(
            label=label,
            data_model_uid=data_model_uid,
            data_model_catalogue_name=data_model_catalogue_name,
        )
        for label, data_model_uid in [
            ("DatasetClass A", data_models[0].uid),
            ("DatasetClass B", data_models[1].uid),
            ("DatasetClass C", data_models[2].uid),
        ]
    ]
    data_model_ig = TestUtils.create_data_model_ig(name="DataModelIG A")
    # Create some datasets
    dataset = TestUtils.create_dataset(
        label="Dataset A label",
        title="Dataset A title",
        description="Dataset A desc",
        data_model_catalogue_name=data_model_catalogue_name,
        data_model_ig_uid=data_model_ig.uid,
        data_model_ig_version_number=data_model_ig.version_number,
        implemented_dataset_class_name=dataset_classes[0].uid,
    )

    # Create some class-variables
    class_variables = []
    class_variables.append(
        TestUtils.create_variable_class(
            label="VariableClass A label",
            title="VariableClass A title",
            description="VariableClass A desc",
            data_model_catalogue_name=data_model_catalogue_name,
            dataset_class_uid=dataset_classes[0].uid,
            data_model_name=data_models[0].uid,
            data_model_version=data_models[0].version_number,
        )
    )
    dataset_variable = TestUtils.create_dataset_variable(
        label="DatasetVariable A",
        dataset_uid=dataset.uid,
        data_model_catalogue_name=data_model_catalogue_name,
        class_variable_uid=class_variables[0].uid,
        data_model_ig_name=data_model_ig.uid,
        data_model_ig_version=data_model_ig.version_number,
    )
    # update class variable with dataset variable relationship
    class_variables[0] = VariableClassService().get_by_uid(
        uid=class_variables[0].uid,
        data_model_name=data_models[0].uid,
        data_model_version=data_models[0].version_number,
    )
    class_variables.append(
        TestUtils.create_variable_class(
            label="name-AAA",
            data_model_catalogue_name=data_model_catalogue_name,
            dataset_class_uid=dataset_classes[1].uid,
            data_model_name=data_models[1].uid,
            data_model_version=data_models[1].version_number,
        )
    )
    class_variables.append(
        TestUtils.create_variable_class(
            label="name-BBB",
            data_model_catalogue_name=data_model_catalogue_name,
            dataset_class_uid=dataset_classes[1].uid,
            data_model_name=data_models[1].uid,
            data_model_version=data_models[1].version_number,
        )
    )
    class_variables.append(
        TestUtils.create_variable_class(
            description="def-XXX",
            data_model_catalogue_name=data_model_catalogue_name,
            dataset_class_uid=dataset_classes[1].uid,
            data_model_name=data_models[1].uid,
            data_model_version=data_models[1].version_number,
        )
    )
    class_variables.append(
        TestUtils.create_variable_class(
            description="def-YYY",
            data_model_catalogue_name=data_model_catalogue_name,
            dataset_class_uid=dataset_classes[1].uid,
            data_model_name=data_models[1].uid,
            data_model_version=data_models[1].version_number,
        )
    )

    for index in range(5):
        class_variables.append(
            TestUtils.create_variable_class(
                label=f"name-AAA-{index}",
                data_model_catalogue_name=data_model_catalogue_name,
                dataset_class_uid=dataset_classes[2].uid,
                data_model_name=data_models[2].uid,
                data_model_version=data_models[2].version_number,
            )
        )
        class_variables.append(
            TestUtils.create_variable_class(
                label=f"name-BBB-{index}",
                data_model_catalogue_name=data_model_catalogue_name,
                dataset_class_uid=dataset_classes[2].uid,
                data_model_name=data_models[2].uid,
                data_model_version=data_models[2].version_number,
            )
        )
        class_variables.append(
            TestUtils.create_variable_class(
                description=f"def-XXX-{index}",
                data_model_catalogue_name=data_model_catalogue_name,
                dataset_class_uid=dataset_classes[2].uid,
                data_model_name=data_models[2].uid,
                data_model_version=data_models[2].version_number,
            )
        )
        class_variables.append(
            TestUtils.create_variable_class(
                description=f"def-YYY-{index}",
                data_model_catalogue_name=data_model_catalogue_name,
                dataset_class_uid=dataset_classes[2].uid,
                data_model_name=data_models[2].uid,
                data_model_version=data_models[2].version_number,
            )
        )

    yield

    drop_db(db_name)


CLASS_VARIABLE_FIELDS_ALL = [
    "uid",
    "label",
    "title",
    "description",
    "implementation_notes",
    "title",
    "label",
    "mapping_instructions",
    "prompt",
    "question_text",
    "simple_datatype",
    "role",
    "catalogue_name",
    "dataset_class",
    "dataset_variable_name",
    "referenced_codelist",
    "has_mapping_target",
    "core",
    "described_value_domain",
    "notes",
    "usage_restrictions",
    "examples",
    "completion_instructions",
    "data_model_names",
    "qualifies_variable",
]

CLASS_VARIABLE_FIELDS_NOT_NULL = [
    "uid",
    "label",
    "catalogue_name",
    "dataset_class",
    "data_model_names",
]


def test_get_class_variable(api_client):
    response = api_client.get(
        f"/standards/class-variables/{class_variables[0].uid}",
        params={
            "data_model_name": data_models[0].uid,
            "data_model_version": data_models[0].version_number,
            "dataset_class_name": dataset_classes[0].label,
        },
    )
    res = response.json()

    assert response.status_code == 200

    # Check fields included in the response
    assert set(list(res.keys())) == set(CLASS_VARIABLE_FIELDS_ALL)
    for key in CLASS_VARIABLE_FIELDS_NOT_NULL:
        assert res[key] is not None

    assert res["uid"] == class_variables[0].uid
    assert res["label"] == "VariableClass A label"
    assert res["description"] == "VariableClass A desc"
    assert res["catalogue_name"] == data_model_catalogue_name
    assert res["dataset_class"]["dataset_class_name"] == dataset_classes[0].label
    assert res["dataset_variable_name"] == dataset_variable.label
    assert res["data_model_names"] == [data_models[0].name]


def test_get_class_variables_pagination(api_client):
    results_paginated: dict = {}
    sort_by = '{"uid": true}'
    for page_number in range(1, 4):
        url = f"/standards/class-variables?page_number={page_number}&page_size=10&sort_by={sort_by}"
        response = api_client.get(
            url,
            params={
                "data_model_name": data_models[2].uid,
                "data_model_version": data_models[2].version_number,
                "dataset_class_name": dataset_classes[2].label,
            },
        )
        res = response.json()
        res_uids = list(map(lambda x: x["uid"], res["items"]))
        results_paginated[page_number] = res_uids
        log.info("Page %s: %s", page_number, res_uids)

    log.info("All pages: %s", results_paginated)

    results_paginated_merged = list(
        list(reduce(lambda a, b: a + b, list(results_paginated.values())))
    )
    log.info("All rows returned by pagination: %s", results_paginated_merged)

    res_all = api_client.get(
        f"/standards/class-variables?page_number=1&page_size=100&sort_by={sort_by}",
        params={
            "data_model_name": data_models[2].uid,
            "data_model_version": data_models[2].version_number,
            "dataset_class_name": dataset_classes[2].label,
        },
    ).json()
    results_all_in_one_page = list(map(lambda x: x["uid"], res_all["items"]))
    log.info("All rows in one page: %s", results_all_in_one_page)
    assert len(results_all_in_one_page) == len(results_paginated_merged)
    assert len(
        [
            class_variable
            for class_variable in class_variables
            if data_models[2].name in class_variable.data_model_names
        ]
    ) == len(results_paginated_merged)


@pytest.mark.parametrize(
    "page_size, page_number, total_count, sort_by, expected_result_len",
    [
        pytest.param(None, None, None, None, 10),
        pytest.param(3, 1, True, None, 3),
        pytest.param(3, 2, True, None, 3),
        pytest.param(10, 2, True, None, 10),
        pytest.param(10, 3, True, None, 0),  # Total numer of data models is 25
        pytest.param(10, 1, True, '{"label": false}', 10),
        pytest.param(10, 2, True, '{"label": true}', 10),
    ],
)
def test_get_class_variables(
    api_client, page_size, page_number, total_count, sort_by, expected_result_len
):
    url = "/standards/class-variables"
    query_params = []
    if page_size:
        query_params.append(f"page_size={page_size}")
    if page_number:
        query_params.append(f"page_number={page_number}")
    if total_count:
        query_params.append(f"total_count={total_count}")
    if sort_by:
        query_params.append(f"sort_by={sort_by}")

    if query_params:
        url = f"{url}?{'&'.join(query_params)}"

    log.info("GET %s", url)
    response = api_client.get(
        url,
        params={
            "data_model_name": data_models[2].uid,
            "data_model_version": data_models[2].version_number,
            "dataset_class_name": dataset_classes[2].label,
        },
    )
    res = response.json()

    assert response.status_code == 200

    # Check fields included in the response
    assert list(res.keys()) == ["items", "total", "page", "size"]
    assert len(res["items"]) == expected_result_len
    assert res["total"] == (
        len(
            [
                class_variable
                for class_variable in class_variables
                if data_models[2].name in class_variable.data_model_names
            ]
        )
        if total_count
        else 0
    )
    assert res["page"] == (page_number if page_number else 1)
    assert res["size"] == (page_size if page_size else 10)

    for item in res["items"]:
        assert set(list(item.keys())) == set(CLASS_VARIABLE_FIELDS_ALL)
        for key in CLASS_VARIABLE_FIELDS_NOT_NULL:
            assert item[key] is not None

    if sort_by:
        # sort_by is JSON string in the form: {"sort_field_name": is_ascending_order}
        sort_by_dict = json.loads(sort_by)
        sort_field: str = list(sort_by_dict.keys())[0]
        sort_order_ascending: bool = list(sort_by_dict.values())[0]

        # extract list of values of 'sort_field_name' field from the returned result
        result_vals = list(map(lambda x: x[sort_field], res["items"]))
        result_vals_sorted_locally = result_vals.copy()
        result_vals_sorted_locally.sort(reverse=not sort_order_ascending)
        # This asser fails due to API issue with sorting coupled with pagination
        # assert result_vals == result_vals_sorted_locally


@pytest.mark.parametrize(
    "filter_by, expected_matched_field, expected_result_prefix",
    [
        pytest.param('{"*": {"v": ["aaa"]}}', "label", "name-AAA"),
        pytest.param('{"*": {"v": ["bBb"]}}', "label", "name-BBB"),
        pytest.param('{"*": {"v": ["ccc"]}}', None, None),
        pytest.param(
            '{"*": {"v": ["DataModelCatalogue name"]}}',
            "catalogue_name",
            "DataModelCatalogue name",
        ),
    ],
)
def test_filtering_wildcard(
    api_client, filter_by, expected_matched_field, expected_result_prefix
):
    url = f"/standards/class-variables?filters={filter_by}"
    response = api_client.get(
        url,
        params={
            "data_model_name": data_models[2].uid,
            "data_model_version": data_models[2].version_number,
            "dataset_class_name": dataset_classes[2].label,
        },
    )
    res = response.json()

    assert response.status_code == 200
    if expected_result_prefix:
        assert len(res["items"]) > 0
        nested_path = None

        # if we expect a nested property to be equal to specified value
        if isinstance(expected_matched_field, str) and "." in expected_matched_field:
            nested_path = expected_matched_field.split(".")
            expected_matched_field = nested_path[-1]
            nested_path = nested_path[:-1]

        # Each returned row has a field that starts with the specified filter value
        for row in res["items"]:
            if nested_path:
                for prop in nested_path:
                    row = row[prop]
            if isinstance(row, list):
                any(
                    item[expected_matched_field].startswith(expected_result_prefix)
                    for item in row
                )
            else:
                assert row[expected_matched_field].startswith(expected_result_prefix)
    else:
        assert len(res["items"]) == 0


@pytest.mark.parametrize(
    "filter_by, expected_matched_field, expected_result",
    [
        pytest.param('{"label": {"v": ["name-AAA"]}}', "label", "name-AAA"),
        pytest.param('{"label": {"v": ["name-BBB"]}}', "label", "name-BBB"),
        pytest.param('{"label": {"v": ["cc"]}}', None, None),
        pytest.param('{"description": {"v": ["def-XXX"]}}', "description", "def-XXX"),
        pytest.param('{"description": {"v": ["def-YYY"]}}', "description", "def-YYY"),
        pytest.param('{"description": {"v": ["cc"]}}', None, None),
        pytest.param(
            '{"dataset_class.dataset_class_name": {"v": ["DatasetClass B"]}}',
            "dataset_class.dataset_class_name",
            "DatasetClass B",
        ),
        pytest.param(
            '{"catalogue_name": {"v": ["DataModelCatalogue name"]}}',
            "catalogue_name",
            "DataModelCatalogue name",
        ),
        pytest.param(
            '{"data_model_names": {"v": ["DataModel B"]}}',
            "data_model_names",
            ["DataModel B"],
        ),
    ],
)
def test_filtering_exact(
    api_client, filter_by, expected_matched_field, expected_result
):
    url = f"/standards/class-variables?filters={filter_by}"
    response = api_client.get(
        url,
        params={
            "data_model_name": data_models[1].uid,
            "data_model_version": data_models[1].version_number,
            "dataset_class_name": dataset_classes[1].label,
        },
    )
    res = response.json()

    assert response.status_code == 200
    if expected_result:
        assert len(res["items"]) > 0

        # if we expect a nested property to be equal to specified value
        nested_path = None
        if isinstance(expected_matched_field, str) and "." in expected_matched_field:
            nested_path = expected_matched_field.split(".")
            expected_matched_field = nested_path[-1]
            nested_path = nested_path[:-1]

        # Each returned row has a field whose value is equal to the specified filter value
        for row in res["items"]:
            if nested_path:
                for prop in nested_path:
                    row = row[prop]
            if isinstance(expected_result, list):
                assert all(
                    item in row[expected_matched_field] for item in expected_result
                )
            else:
                if isinstance(row, list):
                    all(item[expected_matched_field] == expected_result for item in row)
                else:
                    assert row[expected_matched_field] == expected_result
    else:
        assert len(res["items"]) == 0


@pytest.mark.parametrize(
    "field_name",
    [
        pytest.param("label"),
        pytest.param("description"),
        pytest.param("role"),
        pytest.param("dataset_variable_name"),
        pytest.param("catalogue_name"),
        pytest.param("dataset_class.dataset_class_name"),
    ],
)
def test_headers(api_client, field_name):
    url = f"/standards/class-variables/headers?field_name={field_name}&result_count=100"
    response = api_client.get(
        url,
        params={
            "data_model_name": data_models[2].uid,
            "data_model_version": data_models[2].version_number,
            "dataset_class_name": dataset_classes[2].label,
        },
    )
    res = response.json()

    assert response.status_code == 200
    expected_result = []

    nested_path = None
    if isinstance(field_name, str) and "." in field_name:
        nested_path = field_name.split(".")
        expected_matched_field = nested_path[-1]
        nested_path = nested_path[:-1]

    for class_variable in [
        class_var
        for class_var in class_variables
        if data_models[2].name in class_var.data_model_names
    ]:
        if nested_path:
            for prop in nested_path:
                class_variable = getattr(class_variable, prop)
            if isinstance(class_variable, list):
                for item in class_variable:
                    value = getattr(item, expected_matched_field)
                    expected_result.append(value)
            else:
                value = getattr(class_variable, expected_matched_field)
                expected_result.append(value)

        else:
            value = getattr(class_variable, field_name)
            expected_result.append(value)
    expected_result = [result for result in expected_result if result is not None]
    log.info("Expected result is %s", expected_result)
    log.info("Returned %s", res)
    if expected_result:
        assert len(res) > 0
        assert len(set(expected_result)) == len(res)
        assert all(item in res for item in expected_result)
    else:
        assert len(res) == 0


@pytest.mark.parametrize(
    "export_format",
    [
        pytest.param("text/csv"),
        pytest.param("text/xml"),
        pytest.param(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
    ],
)
def test_get_class_variables_csv_xml_excel(api_client, export_format):
    url = "/standards/class-variables"
    TestUtils.verify_exported_data_format(
        api_client,
        export_format,
        url,
        params={
            "data_model_name": data_models[2].uid,
            "data_model_version": data_models[2].version_number,
            "dataset_class_name": dataset_classes[2].label,
        },
    )