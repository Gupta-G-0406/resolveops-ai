
import { useEffect, useState } from "react";

import {
    getAllInvestigations,
    getInvestigationAuditEvents,
    getInvestigationDetail,
} from "../services/investigationApi";

import type {
    AuditEvent,
    InvestigationListResponse,
    InvestigationRun,
} from "../types/investigation";

interface Props {
    onBack: () => void;
    onOpenTicket: (ticketId: number) => void;
}

const PAGE_SIZE = 10;

function formatDate(value: string | null): string {
    if (!value) return "Not available";

    const date = new Date(value);

    return Number.isNaN(date.getTime())
        ? "Invalid date"
        : date.toLocaleString();
}

function formatLabel(value: string): string {
    return value
        .replaceAll("_", " ")
        .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatJson(value: unknown): string {
    if (value == null) return "No data available";

    return JSON.stringify(value, null, 2) ?? "No data available";
}

function StatusBadge({ status }: { status: string }) {
    const styles: Record<string, string> = {
        completed: "ops-badge-success",
        needs_review: "ops-badge-warning",
        running: "ops-badge-info",
        failed: "ops-badge-danger",
    };

    return (
        <span className={`ops-history-badge ${styles[status] ?? ""}`}>
            {formatLabel(status)}
        </span>
    );
}

function InvestigationDetails({
    investigationId,
    onClose,
}: {
    investigationId: number;
    onClose: () => void;
}) {
    const [detail, setDetail] = useState<InvestigationRun | null>(null);
    const [events, setEvents] = useState<AuditEvent[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const controller = new AbortController();

        async function loadDetails() {
            setLoading(true);
            setError(null);
            setDetail(null);
            setEvents([]);

            try {
                const [run, auditEvents] = await Promise.all([
                    getInvestigationDetail(
                        investigationId,
                        controller.signal
                    ),
                    getInvestigationAuditEvents(
                        investigationId,
                        controller.signal
                    ),
                ]);

                if (controller.signal.aborted) return;

                setDetail(run);
                setEvents(auditEvents);
            } catch (err) {
                if (!controller.signal.aborted) {
                    setError(
                        err instanceof Error
                            ? err.message
                            : "Failed to load investigation details"
                    );
                }
            } finally {
                if (!controller.signal.aborted) {
                    setLoading(false);
                }
            }
        }

        void loadDetails();

        return () => controller.abort();
    }, [investigationId]);

    return (
        <section className="ops-ai-workspace">
            <div className="ops-ai-report-heading">
                <div>
                    <p className="ops-ai-eyebrow">INVESTIGATION DETAILS</p>
                    <h3 className="text-xl font-bold text-slate-100">
                        Investigation #{investigationId}
                    </h3>
                </div>

                <button
                    type="button"
                    onClick={onClose}
                    className="ops-history-refresh"
                >
                    Close Details
                </button>
            </div>

            {loading && (
                <p role="status" className="ops-history-empty">
                    Loading investigation details...
                </p>
            )}

            {error && (
                <p role="alert" className="ops-ai-error">
                    {error}
                </p>
            )}

            {detail && (
                <div className="ops-history-details">
                    <div className="flex flex-wrap items-center gap-3">
                        <StatusBadge status={detail.status} />
                        <span className="ops-history-meta">
                            Ticket #{detail.ticket_id}
                        </span>
                        <span className="ops-history-meta">
                            Order {detail.order_number}
                        </span>
                    </div>

                    <div className="ops-ai-result-grid">
                        <section className="ops-ai-panel">
                            <h4 className="mb-3 font-semibold text-slate-100">
                                Specialist Agents
                            </h4>

                            <div className="ops-history-tags">
                                {(detail.selected_agents ?? []).length > 0 ? (
                                    detail.selected_agents.map((agent) => (
                                        <span className="ops-agent-tag" key={agent}>
                                            {formatLabel(agent)}
                                        </span>
                                    ))
                                ) : (
                                    <p className="ops-history-empty">
                                        No agents recorded
                                    </p>
                                )}
                            </div>
                        </section>

                        <section className="ops-ai-panel">
                            <h4 className="mb-3 font-semibold text-slate-100">
                                Referenced Policies
                            </h4>

                            <div className="ops-history-tags">
                                {(detail.policy_ids ?? []).length > 0 ? (
                                    detail.policy_ids.map((policy) => (
                                        <span className="ops-policy-tag" key={policy}>
                                            {policy}
                                        </span>
                                    ))
                                ) : (
                                    <p className="ops-history-empty">
                                        No policies recorded
                                    </p>
                                )}
                            </div>
                        </section>
                    </div>

                    <section className="ops-detail-section">
                        <h4>AI Investigation Report</h4>
                        <div className="ops-report-content">
                            {detail.report ?? "No report available"}
                        </div>
                    </section>

                    <div className="ops-detail-grid">
                        <section className="ops-detail-section">
                            <h4>MCP / Agent Evidence</h4>
                            <pre className="ops-json-panel">
                                {formatJson(detail.evidence)}
                            </pre>
                        </section>

                        <section className="ops-detail-section">
                            <h4>Verification</h4>
                            <pre className="ops-json-panel">
                                {formatJson(detail.verification)}
                            </pre>
                        </section>
                    </div>

                    <section className="ops-detail-section">
                        <h4>Audit Timeline</h4>

                        {events.length === 0 ? (
                            <p className="ops-history-empty">
                                No audit events available.
                            </p>
                        ) : (
                            <ol className="ops-audit-timeline">
                                {events.map((event) => (
                                    <li key={event.id} className="ops-audit-event">
                                        <div className="ops-audit-dot" />

                                        <div className="ops-audit-content">
                                            <div className="ops-audit-heading">
                                                <strong>
                                                    {formatLabel(event.event_type)}
                                                </strong>
                                                <span>{formatDate(event.created_at)}</span>
                                            </div>

                                            <pre className="ops-audit-json">
                                                {formatJson(event.details)}
                                            </pre>
                                        </div>
                                    </li>
                                ))}
                            </ol>
                        )}
                    </section>

                    <p className="ops-history-meta">
                        Created: {formatDate(detail.created_at)} · Completed:{" "}
                        {formatDate(detail.completed_at)}
                    </p>
                </div>
            )}
        </section>
    );
}

export default function GlobalInvestigationHistory({
    onBack,
    onOpenTicket,
}: Props) {
    const [page, setPage] = useState(0);
    const [status, setStatus] = useState("");
    const [ticketFilter, setTicketFilter] = useState("");
    const [data, setData] =
        useState<InvestigationListResponse | null>(null);

    const [selectedId, setSelectedId] = useState<number | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const parsedTicketId = Number(ticketFilter);

    const validTicketFilter =
        ticketFilter === "" ||
        (/^[1-9]\d*$/.test(ticketFilter) &&
            Number.isSafeInteger(parsedTicketId));

    useEffect(() => {
        if (!validTicketFilter) return;

        const controller = new AbortController();

        async function loadInvestigations() {
            setLoading(true);
            setError(null);
            setData(null);

            try {
                const result = await getAllInvestigations(
                    {
                        limit: PAGE_SIZE,
                        offset: page * PAGE_SIZE,
                        status: status || undefined,
                        ticket_id:
                            ticketFilter === ""
                                ? undefined
                                : parsedTicketId,
                    },
                    controller.signal
                );

                if (!controller.signal.aborted) {
                    setData(result);
                }
            } catch (err) {
                if (!controller.signal.aborted) {
                    setError(
                        err instanceof Error
                            ? err.message
                            : "Failed to load investigations"
                    );
                }
            } finally {
                if (!controller.signal.aborted) {
                    setLoading(false);
                }
            }
        }

        void loadInvestigations();

        return () => controller.abort();
    }, [
        page,
        status,
        ticketFilter,
        parsedTicketId,
        validTicketFilter,
    ]);

    const items = validTicketFilter ? (data?.items ?? []) : [];
    const totalPages = Math.ceil((data?.total ?? 0) / PAGE_SIZE);

    return (
        <div className="ops-ticket-detail">
            <div className="ops-history-heading">
                <div>
                    <p className="ops-history-eyebrow">
                        INVESTIGATION RECORDS
                    </p>
                    <h2>Global Investigations</h2>
                    <p>
                        Review all AI investigation runs and their audit trails.
                    </p>
                </div>

                <button
                    type="button"
                    onClick={onBack}
                    className="ops-history-refresh"
                >
                    ← Dashboard
                </button>
            </div>

            <section className="ops-ai-workspace">
                <div className="ops-global-filters">
                    <label className="ops-global-filter">
                        <span>Status</span>
                        <select
                            value={status}
                            onChange={(event) => {
                                setStatus(event.target.value);
                                setPage(0);
                                setSelectedId(null);
                            }}
                        >
                            <option value="">All statuses</option>
                            <option value="completed">Completed</option>
                            <option value="needs_review">Needs Review</option>
                            <option value="running">Running</option>
                            <option value="failed">Failed</option>
                        </select>
                    </label>

                    <label className="ops-global-filter">
                        <span>Ticket ID</span>
                        <input
                            type="number"
                            min="1"
                            step="1"
                            value={ticketFilter}
                            placeholder="All tickets"
                            onChange={(event) => {
                                setTicketFilter(event.target.value);
                                setPage(0);
                                setSelectedId(null);
                            }}
                        />
                    </label>
                </div>
            </section>

            <section className="ops-ai-workspace">
                <div className="ops-global-table-heading">
                    <h3>Investigation Runs</h3>
                    <span>Total: {data?.total ?? "—"}</span>
                </div>

                {!validTicketFilter && (
                    <p role="alert" className="ops-global-error">
                        Ticket ID must be a positive integer.
                    </p>
                )}

                {validTicketFilter && loading && (
                    <p role="status" className="ops-history-empty">
                        Loading investigations...
                    </p>
                )}

                {validTicketFilter && error && (
                    <p role="alert" className="ops-global-error">
                        {error}
                    </p>
                )}

                {validTicketFilter &&
                    !loading &&
                    !error &&
                    items.length === 0 && (
                        <p className="ops-history-empty">
                            No investigations found.
                        </p>
                    )}

                {validTicketFilter &&
                    !loading &&
                    !error &&
                    items.length > 0 && (
                        <div className="ops-global-table-wrap">
                            <table className="ops-global-table">
                                <thead>
                                    <tr>
                                        <th>Run</th>
                                        <th>Ticket</th>
                                        <th>Order</th>
                                        <th>Status</th>
                                        <th>Created</th>
                                        <th>Action</th>
                                    </tr>
                                </thead>

                                <tbody>
                                    {items.map((run) => (
                                        <tr key={run.id}>
                                            <td>#{run.id}</td>
                                            <td>
                                                <button
                                                    type="button"
                                                    className="ops-global-link"
                                                    onClick={() => onOpenTicket(run.ticket_id)}
                                                >
                                                    #{run.ticket_id}
                                                </button>
                                            </td>
                                            <td>{run.order_number}</td>
                                            <td>
                                                <StatusBadge status={run.status} />
                                            </td>
                                            <td>{formatDate(run.created_at)}</td>
                                            <td>
                                                <button
                                                    type="button"
                                                    className="ops-global-link"
                                                    onClick={() =>
                                                        setSelectedId(
                                                            selectedId === run.id ? null : run.id
                                                        )
                                                    }
                                                >
                                                    {selectedId === run.id
                                                        ? "Hide Details"
                                                        : "View Details →"}
                                                </button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}

                <div className="ops-global-pagination">
                    <button
                        type="button"
                        disabled={!validTicketFilter || loading || page === 0}
                        onClick={() => {
                            setPage((current) => current - 1);
                            setSelectedId(null);
                        }}
                    >
                        ← Previous
                    </button>

                    <span>
                        Page {page + 1} of {Math.max(totalPages, 1)}
                    </span>

                    <button
                        type="button"
                        disabled={
                            !validTicketFilter ||
                            loading ||
                            !data ||
                            (page + 1) * PAGE_SIZE >= data.total
                        }
                        onClick={() => {
                            setPage((current) => current + 1);
                            setSelectedId(null);
                        }}
                    >
                        Next →
                    </button>
                </div>
            </section>

            {selectedId !== null && (
                <InvestigationDetails
                    investigationId={selectedId}
                    onClose={() => setSelectedId(null)}
                />
            )}
        </div>
    );
}
