"""CT stats router."""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from clinical_mdr_api import models
from clinical_mdr_api.oauth import get_current_user_id
from clinical_mdr_api.routers import _generic_descriptions
from clinical_mdr_api.services.controlled_terminologies.ct_codelist import (
    CTCodelistService,
)
from clinical_mdr_api.services.controlled_terminologies.ct_stats import CTStatsService

router = APIRouter()


@router.get(
    "/stats",
    summary="Returns stats about Catalogues, Packages and Terms",
    response_model=models.CTStats,
    status_code=200,
    responses={
        404: _generic_descriptions.ERROR_404,
        500: _generic_descriptions.ERROR_500,
    },
)
def get_stats(
    latest_count: Optional[int] = Query(
        3, description="Optional, number of latest codelists to return"
    ),
    current_user_id: str = Depends(get_current_user_id),
):
    ct_stats_service = CTStatsService()

    # Get latest codelists from codelist service
    # Use get_all method from codelist repo with order by start_date desc and page_size = latest_count
    ct_codelist_service = CTCodelistService(user=current_user_id)
    latest_codelists = ct_codelist_service.get_all_codelists(
        sort_by={"name.start_date": False, "codelist_uid": True},
        page_number=1,
        page_size=latest_count,
    )

    return ct_stats_service.get_stats(latest_codelists=latest_codelists.items)