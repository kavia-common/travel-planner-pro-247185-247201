"""
PDF export routes for Travel Planner Pro.

Provides an endpoint to generate a PDF document of a trip itinerary
and return it as a downloadable file.
"""

import io
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors

from src.api.database import get_db
from src.api.models import ItineraryDay, Activity, Budget, Expense, User
from src.api.auth import get_current_user
from src.api.routes_trips import _get_trip_with_access

router = APIRouter(prefix="/api/trips/{trip_id}/export", tags=["Export"])


# PUBLIC_INTERFACE
@router.post(
    "/pdf",
    summary="Export trip as PDF",
    description="Generate and return a PDF document of the trip itinerary.",
    responses={
        200: {
            "description": "PDF file download",
            "content": {"application/pdf": {}},
        }
    },
)
def export_trip_pdf(
    trip_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Export a trip itinerary as a PDF document.

    Generates a formatted PDF with trip details, day-by-day itinerary,
    activities, and budget summary.

    Args:
        trip_id: The trip UUID.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        StreamingResponse with the PDF file.
    """
    trip = _get_trip_with_access(trip_id, current_user, db)

    # Fetch related data
    days = db.query(ItineraryDay).filter(
        ItineraryDay.trip_id == trip_id
    ).order_by(ItineraryDay.day_number).all()

    budget = db.query(Budget).filter(Budget.trip_id == trip_id).first()

    # Build PDF in memory
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.75 * inch)
    styles = getSampleStyleSheet()
    story = []

    # Title
    title_style = ParagraphStyle(
        "TripTitle", parent=styles["Title"], fontSize=20, spaceAfter=12
    )
    story.append(Paragraph(trip.title, title_style))

    # Trip details
    details = f"<b>Destination:</b> {trip.destination}<br/>"
    details += f"<b>Dates:</b> {trip.start_date} to {trip.end_date}<br/>"
    if trip.description:
        details += f"<b>Description:</b> {trip.description}<br/>"
    details += f"<b>Status:</b> {trip.status.value if trip.status else 'planning'}"
    story.append(Paragraph(details, styles["Normal"]))
    story.append(Spacer(1, 0.3 * inch))

    # Itinerary
    if days:
        story.append(Paragraph("Itinerary", styles["Heading2"]))
        for day in days:
            day_title = f"Day {day.day_number} — {day.date}"
            if day.title:
                day_title += f" — {day.title}"
            story.append(Paragraph(day_title, styles["Heading3"]))

            if day.notes:
                story.append(Paragraph(day.notes, styles["Normal"]))

            activities = db.query(Activity).filter(
                Activity.itinerary_day_id == day.id
            ).order_by(Activity.sort_order).all()

            if activities:
                table_data = [["Time", "Activity", "Location", "Category"]]
                for act in activities:
                    time_str = ""
                    if act.start_time:
                        time_str = act.start_time.strftime("%H:%M")
                        if act.end_time:
                            time_str += f" - {act.end_time.strftime('%H:%M')}"
                    table_data.append([
                        time_str,
                        act.title,
                        act.location or "",
                        act.category.value if act.category else "",
                    ])
                table = Table(table_data, colWidths=[1.2 * inch, 2.5 * inch, 2 * inch, 1.3 * inch])
                table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.23, 0.51, 0.96)),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ]))
                story.append(table)
            story.append(Spacer(1, 0.2 * inch))

    # Budget summary
    if budget:
        story.append(Paragraph("Budget Summary", styles["Heading2"]))
        story.append(Paragraph(
            f"<b>Total Budget:</b> {budget.currency} {float(budget.total_budget):,.2f}",
            styles["Normal"],
        ))
        expenses = db.query(Expense).filter(Expense.budget_id == budget.id).all()
        if expenses:
            total_spent = sum(float(e.amount) for e in expenses)
            story.append(Paragraph(
                f"<b>Total Spent:</b> {budget.currency} {total_spent:,.2f}",
                styles["Normal"],
            ))
            remaining = float(budget.total_budget) - total_spent
            story.append(Paragraph(
                f"<b>Remaining:</b> {budget.currency} {remaining:,.2f}",
                styles["Normal"],
            ))

    doc.build(story)
    buffer.seek(0)

    filename = f"{trip.title.replace(' ', '_')}_itinerary.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
