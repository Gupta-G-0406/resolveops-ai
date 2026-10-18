
import logging
import asyncio
from uuid import uuid4

from app.services.investigation_heartbeat import run_with_heartbeat

from fastapi import APIRouter, Depends, HTTPException , Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

from app.schemas.investigation import (
    InvestigationResponse,
    InvestigationHistoryItem,
    InvestigationListResponse,
    InvestigationDetailResponse,
    AuditEventResponse,
    InvestigationStatsResponse
)

from app.services import (
    ticket_service,
    investigation_service,
    investigation_repository,
)


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/api/tickets",
    tags=["Investigations"],
)


# ============================================================
# Run AI Investigation
# ============================================================


@router.post(
    "/{ticket_id}/investigate",
    response_model=InvestigationResponse,
)
async def investigate_ticket(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
):
    # 1. Load ticket.
    ticket = await ticket_service.get_ticket_details(
        db,
        ticket_id,
    )

    if ticket is None:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found",
        )

    # 2. Create investigation record.
    run = await investigation_repository.create_run(
        db,
        ticket_id=ticket.id,
        order_number=ticket.order.order_number,
    )

    run_id = run.id
    worker_id = str(uuid4())

    # 3. Atomically acquire worker ownership.
    #
    # This must happen before starting LangGraph.
    try:
        acquired = await (
            investigation_repository.acquire_investigation_lease(
                db,
                run_id=run_id,
                worker_id=worker_id,
            )
        )
    except BaseException:
        await db.rollback()
        logger.exception(
            "Lease acquisition failed: run_id=%s",
            run_id,
        )
        raise

    if not acquired:
        logger.error(
            "Lease acquisition rejected: run_id=%s",
            run_id,
        )
        raise HTTPException(
            status_code=409,
            detail="Investigation worker lease could not be acquired",
        )

    logger.info(
        "Investigation lease acquired: run_id=%s worker_id=%s",
        run_id,
        worker_id,
    )

    # 4. Execute investigation with periodic heartbeat.
    try:
        result = await run_with_heartbeat(
            investigation_service.investigate_ticket(ticket),
            run_id=run_id,
            worker_id=worker_id,
        )

        # 5. Only the current lease owner may finalize.
        await investigation_repository.complete_run_owned(
            db,
            run_id=run_id,
            worker_id=worker_id,
            result=result,
            evidence=result["evidence"],
        )

        logger.info(
            "Investigation completed: ticket_id=%s run_id=%s",
            ticket_id,
            run_id,
        )

        return result

    except investigation_repository.InvestigationLeaseLostError:
        await db.rollback()

        logger.error(
            "Investigation ownership lost: run_id=%s worker_id=%s",
            run_id,
            worker_id,
        )

        # Do not mark failed: another worker or recovery
        # process may already own or finalize this record.
        raise HTTPException(
            status_code=409,
            detail="Investigation worker lease was lost",
        )

    except asyncio.CancelledError:
        await db.rollback()

        logger.warning(
            "Investigation cancelled: run_id=%s",
            run_id,
        )

        # Client disconnect / server shutdown cancellation.
        # Do not swallow cancellation.
        #
        # The lease will eventually expire unless another
        # recovery mechanism handles the record.
        raise

    except Exception as exc:
        logger.exception(
            "Investigation failed: ticket_id=%s run_id=%s",
            ticket_id,
            run_id,
        )

        try:
            await db.rollback()

            await investigation_repository.fail_run_owned(
                db,
                run_id=run_id,
                worker_id=worker_id,
                error_type=type(exc).__name__,
            )

        except investigation_repository.InvestigationLeaseLostError:
            logger.warning(
                "Failure not persisted because lease was lost: "
                "run_id=%s",
                run_id,
            )
            await db.rollback()

        except Exception:
            logger.exception(
                "Failed to persist investigation failure: "
                "run_id=%s",
                run_id,
            )
            await db.rollback()

        # Preserve MCPConnectionError -> 503,
        # MCPToolError -> 502,
        # and other existing exception handlers.
        raise


# ============================================================
# Investigation History
# ============================================================

@router.get(
    "/{ticket_id}/investigations",
    response_model=list[InvestigationHistoryItem],
)
async def get_investigation_history(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
):
    ticket = await ticket_service.get_ticket_by_id(
        db,
        ticket_id,
    )

    if ticket is None:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found",
        )

    return await investigation_repository.list_ticket_runs(
        db,
        ticket_id,
    )



# ============================================================
# Global Investigation History API
# ============================================================

history_router = APIRouter(
    prefix="/api/investigations",
    tags=["Investigation History"],
)


@history_router.get(
    "",
    response_model=InvestigationListResponse,
)
async def list_investigations(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    ticket_id: int | None = Query(default=None, ge=1),
    status: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """List investigations with pagination and filters."""

    runs, total = (
        await investigation_repository.list_investigations(
            db,
            limit=limit,
            offset=offset,
            ticket_id=ticket_id,
            status=status,
        )
    )

    return {
        "items": runs,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@history_router.get(
    "/stats",
    response_model=InvestigationStatsResponse,
)
async def get_investigation_stats(
    db: AsyncSession = Depends(get_db),
):
    return await investigation_repository.get_investigation_stats(db)




@history_router.get(
    "/stale",
    response_model=list[InvestigationHistoryItem],
)
async def get_stale_investigations(
    timeout_minutes: int = Query(
        default=30,
        ge=1,
        le=10080,
    ),
    db: AsyncSession = Depends(get_db),
):
    """Read-only listing of potentially stale investigations."""

    return await investigation_repository.list_stale_investigations(
        db,
        timeout_minutes=timeout_minutes,
    )


@history_router.get(
    "/{investigation_id}",
    response_model=InvestigationDetailResponse,
)
async def get_investigation_detail(
    investigation_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a complete investigation record."""

    run = await investigation_repository.get_investigation(
        db,
        investigation_id,
    )

    if run is None:
        raise HTTPException(
            status_code=404,
            detail="Investigation not found",
        )

    return run


@history_router.get(
    "/{investigation_id}/audit-events",
    response_model=list[AuditEventResponse],
)
async def get_investigation_audit_events(
    investigation_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get the investigation audit timeline."""

    run = await investigation_repository.get_investigation(
        db,
        investigation_id,
    )

    if run is None:
        raise HTTPException(
            status_code=404,
            detail="Investigation not found",
        )

    return await investigation_repository.list_audit_events(
        db,
        investigation_id,
    )
