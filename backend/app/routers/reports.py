from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.report_service import generate_report
from app.schemas.report import ProjectReport

router = APIRouter(tags=["Reports"])


@router.get(
    "/api/projects/{project_id}/report",
    response_model=ProjectReport,
)
def get_project_report(project_id: int, db: Session = Depends(get_db)):
    """
    Return a complete structured v2 report for the project.

    Includes: project info, climate, shelter, materials,
    latest simulation results, latest optimization results,
    baseline vs optimized comparison, recommendation, and metadata.
    """
    return generate_report(project_id, db)


@router.get(
    "/api/projects/{project_id}/report/pdf",
)
def get_project_report_pdf(project_id: int, db: Session = Depends(get_db)):
    """
    Return a PDF project report.

    ⚠️  PDF generation via ReportLab is not yet implemented.
    Returns 501 until integrated.
    """
    raise HTTPException(
        status_code=501,
        detail=(
            "PDF report generation is not yet implemented. "
            "Use GET /api/projects/{id}/report for the JSON report. "
            "To implement: integrate ReportLab in app/services/report_service.py."
        ),
    )
