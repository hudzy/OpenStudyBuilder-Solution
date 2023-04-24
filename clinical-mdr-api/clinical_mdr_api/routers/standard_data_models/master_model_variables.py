"""Master Model Variables router"""
from typing import Any, List, Optional

from fastapi import APIRouter, Body, Depends, Path, Query
from pydantic.types import Json
from starlette.requests import Request

from clinical_mdr_api import config
from clinical_mdr_api.models.error import ErrorResponse
from clinical_mdr_api.models.standard_data_models.master_model_variable import (
    MasterModelVariable,
    MasterModelVariableInput,
)
from clinical_mdr_api.models.utils import CustomPage
from clinical_mdr_api.oauth import get_current_user_id
from clinical_mdr_api.repositories._utils import FilterOperator
from clinical_mdr_api.routers import _generic_descriptions, decorators
from clinical_mdr_api.services.standard_data_models.master_model_variable import (
    MasterModelVariableService,
)

router = APIRouter()

MasterModelVariableUID = Path(
    None, description="The unique id of the MasterModelVariable"
)


@router.get(
    "",
    summary="List all sponsor master model variables",
    description="""
State before:

Business logic:
 - List all master model variables in their latest version.

State after:
 - No change

Possible errors:
""",
    response_model=CustomPage[MasterModelVariable],
    status_code=200,
    responses={500: {"model": ErrorResponse, "description": "Internal Server Error"}},
)
@decorators.allow_exports(
    {
        "defaults": ["uid", "name", "start_date", "status", "version"],
        "formats": [
            "text/csv",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "text/xml",
            "application/json",
        ],
    }
)
# pylint: disable=unused-argument
def get_master_model_variables(
    request: Request,  # request is actually required by the allow_exports decorator
    sort_by: Json = Query(None, description=_generic_descriptions.SORT_BY),
    page_number: Optional[int] = Query(
        1, ge=1, description=_generic_descriptions.PAGE_NUMBER
    ),
    page_size: Optional[int] = Query(
        config.DEFAULT_PAGE_SIZE, description=_generic_descriptions.PAGE_SIZE
    ),
    filters: Optional[Json] = Query(
        None,
        description=_generic_descriptions.FILTERS,
        example=_generic_descriptions.FILTERS_EXAMPLE,
    ),
    operator: Optional[str] = Query("and", description=_generic_descriptions.OPERATOR),
    total_count: Optional[bool] = Query(
        False, description=_generic_descriptions.TOTAL_COUNT
    ),
    current_user_id: str = Depends(get_current_user_id),
):
    master_model_variable_service = MasterModelVariableService(user=current_user_id)
    results = master_model_variable_service.get_all_items(
        sort_by=sort_by,
        page_number=page_number,
        page_size=page_size,
        total_count=total_count,
        filter_by=filters,
        filter_operator=FilterOperator.from_str(operator),
    )
    return CustomPage.create(
        items=results.items, total=results.total_count, page=page_number, size=page_size
    )


@router.get(
    "/headers",
    summary="Returns possible values from the database for a given header",
    description="Allowed parameters include : field name for which to get possible values, "
    "search string to provide filtering for the field name, additional filters to apply on other fields",
    response_model=List[Any],
    status_code=200,
    responses={
        404: {
            "model": ErrorResponse,
            "description": "Not Found - Invalid field name specified",
        },
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
)
def get_distinct_values_for_header(
    current_user_id: str = Depends(get_current_user_id),
    field_name: str = Query(..., description=_generic_descriptions.HEADER_FIELD_NAME),
    search_string: Optional[str] = Query(
        "", description=_generic_descriptions.HEADER_SEARCH_STRING
    ),
    filters: Optional[Json] = Query(
        None,
        description=_generic_descriptions.FILTERS,
        example=_generic_descriptions.FILTERS_EXAMPLE,
    ),
    operator: Optional[str] = Query("and", description=_generic_descriptions.OPERATOR),
    result_count: Optional[int] = Query(
        10, description=_generic_descriptions.HEADER_RESULT_COUNT
    ),
):
    master_model_variable_service = MasterModelVariableService(user=current_user_id)
    return master_model_variable_service.get_distinct_values_for_header(
        field_name=field_name,
        search_string=search_string,
        filter_by=filters,
        filter_operator=FilterOperator.from_str(operator),
        result_count=result_count,
    )


@router.post(
    "",
    summary="Create a new version of the master model variable.",
    description="""
    State before:
    - The specified Variable must exist.

    Business logic :
    - New version is created for the Variable.
    - The status of the new created version will be automatically set to 'Draft'.
    - The 'version' property of the new version will be automatically set to 1.
    - The 'change_description' property will be set automatically to 'Imported new version'.

    State after:
    - MasterModelVariableValue node is created, assigned a version, and linked with the VariableRoot node.

    Possible errors:
    - Missing Variable.
    """,
    response_model=MasterModelVariable,
    response_model_exclude_unset=True,
    status_code=201,
    responses={
        201: {
            "description": "Created - a new version of the master model variable was successfully created."
        },
        400: {
            "model": ErrorResponse,
            "description": "BusinessLogicException - Reasons include e.g.: \n"
            "- The target Variable *variable_uid* does not exist in the database.\n",
        },
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
)
# pylint: disable=unused-argument
def create(
    master_model: MasterModelVariableInput = Body(
        None,
        description="Parameters of the Master Model Variable that shall be created.",
    ),
    current_user_id: str = Depends(get_current_user_id),
) -> MasterModelVariable:
    master_model_variable_service = MasterModelVariableService(user=current_user_id)
    return master_model_variable_service.create(item_input=master_model)


@router.post(
    "/{uid}/approvals",
    summary="Approve draft version of master model variable",
    description="""
State before:
 - uid must exist and master model variable must be in status Draft.

Business logic:
 - The latest 'Draft' version will remain the same as before.
 - The status of the new approved version will be automatically set to 'Final'.
 - No change to the version number
 - The 'change_description' property will be set automatically 'Approved version'.

State after:
 - MasterModelVariable changed status to Final.

Possible errors:
 - Invalid uid or status not Draft.
    """,
    response_model=MasterModelVariable,
    response_model_exclude_unset=True,
    status_code=201,
    responses={
        201: {"description": "OK."},
        403: {
            "model": ErrorResponse,
            "description": "Forbidden - Reasons include e.g.: \n"
            "- The variable is not in draft status.\n",
        },
        404: {
            "model": ErrorResponse,
            "description": "Not Found - The variable with the specified 'uid' wasn't found.",
        },
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
)
def approve(
    uid: str = MasterModelVariableUID,
    current_user_id: str = Depends(get_current_user_id),
):
    master_model_variable_service = MasterModelVariableService(user=current_user_id)
    return master_model_variable_service.approve(uid=uid)


@router.post(
    "/{uid}/versions",
    summary=" Create a new version of variable",
    description="""
State before:
 - uid must exist and the variable must be in status Final.

Business logic:
- The variable is changed to a draft state.

State after:
 - The variable changed status to Draft and assigned a new version number.

Possible errors:
 - Invalid uid or status not Final.
""",
    response_model=MasterModelVariable,
    response_model_exclude_unset=True,
    status_code=201,
    responses={
        201: {"description": "OK."},
        403: {
            "model": ErrorResponse,
            "description": "Forbidden - Reasons include e.g.: \n"
            "- The variable is not in final status.\n",
        },
        404: {
            "model": ErrorResponse,
            "description": "Not Found - The variable with the specified 'uid' wasn't found.",
        },
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
)
def new_version(
    uid: str = MasterModelVariableUID,
    current_user_id: str = Depends(get_current_user_id),
):
    master_model_variable_service = MasterModelVariableService(user=current_user_id)
    return master_model_variable_service.create_new_version(uid=uid)