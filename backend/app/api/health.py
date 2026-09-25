from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from tortoise.exceptions import DoesNotExist

from app.api.auth import get_current_user
from app.api.pets import _get_owned_pet
from app.models.models import MedicalExam, MedicationRecord, Pet, User
from app.schemas.schemas import MedicalExamIn, MedicalExamOut, MedicationIn, MedicationOut

router = APIRouter(prefix="/api/pets/{pet_id}/health", tags=["health"])


def _parse_date(value: str | None, field: str) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"{field} 格式应为 YYYY-MM-DD")


# ---------------------------------------------------------------------------
# 体检记录
# ---------------------------------------------------------------------------


@router.get("/exams", response_model=list[MedicalExamOut])
async def list_exams(pet_id: int, user: User = Depends(get_current_user)):
    pet = await _get_owned_pet(pet_id, user)
    return await MedicalExam.filter(pet=pet).order_by("-exam_date")


@router.post("/exams", response_model=MedicalExamOut)
async def add_exam(pet_id: int, data: MedicalExamIn, user: User = Depends(get_current_user)):
    pet = await _get_owned_pet(pet_id, user)
    exam = await MedicalExam.create(
        pet=pet,
        exam_date=_parse_date(data.exam_date, "exam_date") or date.today(),
        hospital=data.hospital,
        items=data.items,
        result=data.result,
        vet_name=data.vet_name,
    )
    return exam


@router.delete("/exams/{exam_id}")
async def delete_exam(pet_id: int, exam_id: int, user: User = Depends(get_current_user)):
    pet = await _get_owned_pet(pet_id, user)
    try:
        exam = await MedicalExam.get(id=exam_id, pet=pet)
    except DoesNotExist:
        raise HTTPException(status_code=404, detail="体检记录不存在")
    await exam.delete()
    return {"detail": "已删除"}


# ---------------------------------------------------------------------------
# 用药记录
# ---------------------------------------------------------------------------


@router.get("/medications", response_model=list[MedicationOut])
async def list_medications(pet_id: int, user: User = Depends(get_current_user)):
    pet = await _get_owned_pet(pet_id, user)
    return await MedicationRecord.filter(pet=pet).order_by("-start_date")


@router.post("/medications", response_model=MedicationOut)
async def add_medication(
    pet_id: int, data: MedicationIn, user: User = Depends(get_current_user)
):
    pet = await _get_owned_pet(pet_id, user)
    med = await MedicationRecord.create(
        pet=pet,
        drug_name=data.drug_name,
        start_date=_parse_date(data.start_date, "start_date"),
        end_date=_parse_date(data.end_date, "end_date"),
        dosage=data.dosage,
        reason=data.reason,
        notes=data.notes,
    )
    return med


@router.delete("/medications/{med_id}")
async def delete_medication(pet_id: int, med_id: int, user: User = Depends(get_current_user)):
    pet = await _get_owned_pet(pet_id, user)
    try:
        med = await MedicationRecord.get(id=med_id, pet=pet)
    except DoesNotExist:
        raise HTTPException(status_code=404, detail="用药记录不存在")
    await med.delete()
    return {"detail": "已删除"}
