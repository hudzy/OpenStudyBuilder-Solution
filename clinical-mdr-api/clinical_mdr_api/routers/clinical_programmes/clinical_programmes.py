from typing import Sequence

from fastapi import APIRouter, Body, Depends

from clinical_mdr_api import models
from clinical_mdr_api.oauth import get_current_user_id
from clinical_mdr_api.routers import _generic_descriptions
from clinical_mdr_api.services.clinical_programmes import (
    clinical_programme as clinical_programme_service,
)

router = APIRouter()


@router.get(
    "",
    summary="Returns all clinical programmes.",
    response_model=Sequence[models.ClinicalProgramme],
    status_code=200,
    responses={
        404: _generic_descriptions.ERROR_404,
        500: _generic_descriptions.ERROR_500,
    },
)
def get_projects() -> Sequence[models.ClinicalProgramme]:
    return clinical_programme_service.get_all_clinical_programmes()


@router.post(
    "",
    summary="Creates a new clinical programme.",
    response_model=models.ClinicalProgramme,
    status_code=201,
    responses={
        201: {
            "description": "Created - The clinical programme was successfully created."
        },
        500: _generic_descriptions.ERROR_500,
    },
)
# pylint: disable=unused-argument
def create(
    clinical_programme_create_input: models.ClinicalProgrammeInput = Body(
        description="Related parameters of the clinical programme that shall be created.",
    ),
    current_user_id: str = Depends(get_current_user_id),
) -> models.ClinicalProgramme:
    return clinical_programme_service.create(clinical_programme_create_input)