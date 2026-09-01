"""API-слой модуля вариаций. Только HTTP."""

from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import require_editor
from app.modules.variations import service
from app.modules.variations.schemas import VariationAxesIn, VariationPreviewOut

router = APIRouter()


@router.post("/preview", response_model=VariationPreviewOut)
def preview(data: VariationAxesIn, _=Depends(require_editor)) -> VariationPreviewOut:
    """Предпросмотр SKU по осям: цвет × размер × пол × комплектность."""
    return service.preview_variations(data)
