"""API-слой модуля вариаций. Только HTTP."""

from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import get_current_user
from app.modules.variations import service
from app.modules.variations.schemas import VariationAxesIn, VariationPreviewOut

router = APIRouter()


@router.post("/preview", response_model=VariationPreviewOut)
def preview(data: VariationAxesIn, _=Depends(get_current_user)) -> VariationPreviewOut:
    """Предпросмотр SKU по осям: цвет × размер × пол × комплектность."""
    return service.preview_variations(data)
