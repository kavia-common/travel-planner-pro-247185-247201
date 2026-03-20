"""
Budget and expense routes for Travel Planner Pro.

Provides endpoints for managing trip budgets and expenses.
"""

from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.database import get_db
from src.api.models import Budget, Expense, User
from src.api.schemas import (
    BudgetPayload, BudgetResponse, ExpensePayload, ExpenseResponse,
)
from src.api.auth import get_current_user
from src.api.routes_trips import _get_trip_with_access

router = APIRouter(prefix="/api/trips/{trip_id}", tags=["Budget & Expenses"])


def _expense_to_response(exp: Expense) -> ExpenseResponse:
    """Convert an Expense ORM object to an ExpenseResponse schema."""
    return ExpenseResponse(
        id=str(exp.id),
        budget_id=str(exp.budget_id),
        title=exp.title,
        amount=float(exp.amount),
        category=exp.category.value if exp.category else "other",
        date=exp.date.isoformat() if exp.date else "",
        notes=exp.notes,
    )


def _budget_to_response(budget: Budget) -> BudgetResponse:
    """Convert a Budget ORM object to a BudgetResponse schema."""
    return BudgetResponse(
        id=str(budget.id),
        trip_id=str(budget.trip_id),
        total_budget=float(budget.total_budget),
        currency=budget.currency,
        expenses=[_expense_to_response(e) for e in (budget.expenses or [])],
    )


# PUBLIC_INTERFACE
@router.get(
    "/budget",
    response_model=BudgetResponse,
    summary="Get trip budget",
    description="Returns the budget and all expenses for a trip.",
)
def get_budget(
    trip_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get the budget for a trip.

    If no budget exists, returns a default empty budget.

    Args:
        trip_id: The trip UUID.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        BudgetResponse with expenses.
    """
    _get_trip_with_access(trip_id, current_user, db)

    budget = db.query(Budget).filter(Budget.trip_id == trip_id).first()
    if not budget:
        # Return a virtual empty budget
        return BudgetResponse(
            id="",
            trip_id=trip_id,
            total_budget=0,
            currency="USD",
            expenses=[],
        )
    return _budget_to_response(budget)


# PUBLIC_INTERFACE
@router.post(
    "/budget",
    response_model=BudgetResponse,
    summary="Create or update budget",
    description="Create or update the budget for a trip (upsert).",
)
def upsert_budget(
    trip_id: str,
    payload: BudgetPayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create or update a trip budget.

    Args:
        trip_id: The trip UUID.
        payload: Budget data (total_budget, currency).
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The created or updated BudgetResponse.
    """
    _get_trip_with_access(trip_id, current_user, db, require_edit=True)

    budget = db.query(Budget).filter(Budget.trip_id == trip_id).first()
    if budget:
        budget.total_budget = payload.total_budget
        budget.currency = payload.currency
        budget.updated_at = datetime.utcnow()
    else:
        budget = Budget(
            trip_id=trip_id,
            total_budget=payload.total_budget,
            currency=payload.currency,
        )
        db.add(budget)

    db.commit()
    db.refresh(budget)
    return _budget_to_response(budget)


# PUBLIC_INTERFACE
@router.post(
    "/expenses",
    response_model=ExpenseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create expense",
    description="Add an expense to the trip budget.",
)
def create_expense(
    trip_id: str,
    payload: ExpensePayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new expense.

    Automatically creates a budget if one doesn't exist.

    Args:
        trip_id: The trip UUID.
        payload: Expense creation data.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The created ExpenseResponse object.
    """
    _get_trip_with_access(trip_id, current_user, db, require_edit=True)

    # Ensure budget exists
    budget = db.query(Budget).filter(Budget.trip_id == trip_id).first()
    if not budget:
        budget = Budget(trip_id=trip_id, total_budget=0, currency="USD")
        db.add(budget)
        db.commit()
        db.refresh(budget)

    expense = Expense(
        budget_id=budget.id,
        title=payload.title,
        amount=payload.amount,
        category=payload.category.value,
        date=date.fromisoformat(payload.date) if payload.date else None,
        notes=payload.notes,
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return _expense_to_response(expense)


# PUBLIC_INTERFACE
@router.delete(
    "/expenses/{expense_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete expense",
    description="Remove an expense from the trip budget.",
)
def delete_expense(
    trip_id: str,
    expense_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete an expense.

    Args:
        trip_id: The trip UUID.
        expense_id: The expense UUID.
        current_user: The authenticated user.
        db: Database session.
    """
    _get_trip_with_access(trip_id, current_user, db, require_edit=True)

    budget = db.query(Budget).filter(Budget.trip_id == trip_id).first()
    if not budget:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")

    expense = db.query(Expense).filter(
        Expense.id == expense_id,
        Expense.budget_id == budget.id,
    ).first()
    if not expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")

    db.delete(expense)
    db.commit()
    return None
