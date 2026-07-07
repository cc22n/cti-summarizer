"""Categories API endpoint."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.category import AlertCategory

router = APIRouter(prefix="/categories", tags=["categories"])


class CategoryResponse(BaseModel):
    id: int
    name: str
    description: str | None = None

    model_config = {"from_attributes": True}


@router.get("", response_model=list[CategoryResponse])
def list_categories(db: Session = Depends(get_db)):
    """Return all threat categories."""
    categories = (
        db.query(AlertCategory)
        .order_by(AlertCategory.name)
        .all()
    )
    return [CategoryResponse.model_validate(c) for c in categories]
