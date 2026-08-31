from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.report_service import generate_report

router = APIRouter(tags=["Reports"])


@router.get("/api/projects/{project_id}/report")
def get_project_report(project_id: int, db: Session = Depends(get_db)):
    """
    Return a complete structured report for the project.

    Includes: project info, climate, shelter, materials, latest simulation
    results, latest optimization results, winning configuration, and
    optimization reasoning.
    """
    return generate_report(project_id, db)
