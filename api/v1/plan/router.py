from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.v1.plan import schemas, service
from core.database import get_db
from core.dependencies import get_current_active_user

router = APIRouter(prefix="/plan", tags=["plan"])


@router.post("/job-analysis", response_model=schemas.JobAnalysisResponse)
async def create_job_analysis(
    data: schemas.JobAnalysisCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.create_job_analysis(db, current_user, data.user_id, data.jd_text)


@router.get("/job-analysis/{analysis_id}", response_model=schemas.JobAnalysisResponse)
async def get_job_analysis(
    analysis_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.get_job_analysis(db, analysis_id)


@router.get("/job-analysis", response_model=list[schemas.JobAnalysisResponse])
async def list_job_analyses(
    user_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.list_job_analyses(db, current_user, user_id)


@router.get("/prototypes", response_model=list[schemas.PrototypeResponse])
async def list_prototypes(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.list_prototypes(db)


@router.get("/prototypes/{prototype_id}", response_model=schemas.PrototypeResponse)
async def get_prototype(
    prototype_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.get_prototype_by_id(db, prototype_id)


@router.put("/prototypes/{prototype_id}", response_model=schemas.PrototypeResponse)
async def update_prototype(
    prototype_id: str,
    data: schemas.PrototypeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.update_prototype(db, current_user, prototype_id, data.model_dump(exclude_unset=True))


@router.delete("/prototypes/{prototype_id}")
async def delete_prototype(
    prototype_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    await service.delete_prototype(db, current_user, prototype_id)
    return {"message": "Prototype deleted successfully"}


@router.post("/contracts/generate", response_model=schemas.ContractResponse)
async def generate_contract(
    data: schemas.ContractGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.generate_contract(db, current_user, data.period_id, data.user_id, data.job_analysis_id, data.feedback)


@router.get("/contracts/{contract_id}", response_model=schemas.ContractResponse)
async def get_contract(
    contract_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.get_contract(db, contract_id)


@router.post("/contracts/{contract_id}/confirm", response_model=schemas.ContractResponse)
async def confirm_contract(
    contract_id: str,
    data: schemas.ContractConfirmRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.confirm_contract(db, current_user, contract_id, data.confirmed_by)


@router.get("/templates", response_model=list[schemas.TemplateResponse])
async def list_templates(
    prototype_code: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return await service.list_templates(db, prototype_code)
