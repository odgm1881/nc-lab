from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.exceptions import AuthError
from app.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.pilot_metrics import service
from app.modules.pilot_metrics.schemas import PilotMetricsOut

router = APIRouter()


def _client_id(user: User) -> str:
    if not user.client_id:
        raise AuthError("Пользователь не привязан к клиенту.")
    return user.client_id


@router.get("/metrics", response_model=PilotMetricsOut)
def metrics(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PilotMetricsOut:
    return service.calculate(db, _client_id(user))


@router.get("/metrics.csv")
def metrics_csv(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    content = service.export_csv(service.calculate(db, _client_id(user)))
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="pilot-metrics.csv"'},
    )
