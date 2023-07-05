"""class variables router."""
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, Path, Query
from pydantic.types import Json
from starlette.requests import Request

from clinical_mdr_api import config
from clinical_mdr_api.models.error import ErrorResponse
from clinical_mdr_api.models.standard_data_models.variable_class import VariableClass
from clinical_mdr_api.models.utils import CustomPage
from clinical_mdr_api.oauth import get_current_user_id
from clinical_mdr_api.repositories._utils import FilterOperator
from clinical_mdr_api.routers import _generic_descriptions, decorators
from clinical_mdr_api.services.standard_data_models.variable_class import (
    VariableClassService,
)

router = APIRouter()

ClassVariableUID = Path(None, description="The unique id of the VariableClass")


@router.get(
    "/class-variables",
    summary="List all class-variables",
    description=f"""
State before:

Business logic:
 - List all class variables in their latest version.

State after:
 - No change

{_generic_descriptions.DATA_EXPORTS_HEADER}

""",
    response_model=CustomPage[VariableClass],
    status_code=200,
    responses={
        404: _generic_descriptions.ERROR_404,
        500: _generic_descriptions.ERROR_500,
    },
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
def get_class_variables(
    request: Request,  # request is actually required by the allow_exports decorator
    data_model_name: str = Query(
        ...,
        description="The name of the selected Data model, for instance 'SDTM'",
    ),
    data_model_version: str = Query(
        ...,
        description="The version of the selected Data model, for instance '1.4'",
    ),
    sort_by: Json = Query(None, description=_generic_descriptions.SORT_BY),
    page_number: Optional[int] = Query(
        1, ge=1, description=_generic_descriptions.PAGE_NUMBER
    ),
    page_size: Optional[int] = Query(
        config.DEFAULT_PAGE_SIZE,
        ge=0,
        le=config.MAX_PAGE_SIZE,
        description=_generic_descriptions.PAGE_SIZE,
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
    class_variable_service = VariableClassService(user=current_user_id)
    results = class_variable_service.get_all_items(
        sort_by=sort_by,
        page_number=page_number,
        page_size=page_size,
        total_count=total_count,
        filter_by=filters,
        filter_operator=FilterOperator.from_str(operator),
        data_model_name=data_model_name,
        data_model_version=data_model_version,
    )
    return CustomPage.create(
        items=results.items, total=results.total_count, page=page_number, size=page_size
    )


@router.get(
    "/class-variables/headers",
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
        500: _generic_descriptions.ERROR_500,
    },
)
def get_distinct_values_for_header(
    data_model_name: str = Query(
        ...,
        description="The name of the selected Data model, for instance 'SDTM'",
    ),
    data_model_version: str = Query(
        ...,
        description="The version of the selected Data model, for instance '1.4'",
    ),
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
    class_variable_service = VariableClassService(user=current_user_id)
    return class_variable_service.get_distinct_values_for_header(
        data_model_name=data_model_name,
        data_model_version=data_model_version,
        field_name=field_name,
        search_string=search_string,
        filter_by=filters,
        filter_operator=FilterOperator.from_str(operator),
        result_count=result_count,
    )


@router.get(
    "/class-variables/{uid}",
    summary="Get details on a specific class variable",
    description="""
State before:
 - a class variable with uid must exist.

Business logic:

State after:
 - No change

Possible errors:
 - Invalid uid.
 """,
    response_model=VariableClass,
    status_code=200,
    responses={
        404: _generic_descriptions.ERROR_404,
        500: _generic_descriptions.ERROR_500,
    },
)
def get_class_variable(
    uid: str = ClassVariableUID,
    current_user_id: str = Depends(get_current_user_id),
    data_model_name: str = Query(
        ...,
        description="The name of the selected Data model, for instance 'SDTM'",
    ),
    data_model_version: str = Query(
        ...,
        description="The version of the selected Data model, for instance '1.4'",
    ),
):
    class_variable_service = VariableClassService(user=current_user_id)
    return class_variable_service.get_by_uid(
        uid=uid,
        data_model_name=data_model_name,
        data_model_version=data_model_version,
    )