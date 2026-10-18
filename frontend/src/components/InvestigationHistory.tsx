
import { useEffect, useState } from "react";

import {
    getInvestigationHistory,
    getInvestigationAuditEvents,
} from "../services/investigationApi";
import InvestigationReport from "./InvestigationReport";

import type {
    AuditEvent,
    InvestigationRun,
} from "../types/investigation";

interface Props {
    ticketId: number;
    refreshKey?: number;
}

function formatDate(value: string | null): string {
    if (!value) return "Not available";

    const date = new Date(value);

    return Number.isNaN(date.getTime())
        ? "Invalid date"
        : date.toLocaleString();
}

function formatJson(value: unknown): string {
    return value == null
        ? "No data available"
        : JSON.stringify(value, null, 2) ?? "No data available";
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
            {status.replaceAll("_", " ")}
        </span>
    );
}

function InvestigationCard({
    investigation,
}: {
    investigation: InvestigationRun;
}) {
    const [expanded, setExpanded] = useState(false);
    const [events, setEvents] = useState<AuditEvent[]>([]);
    const [auditLoading, setAuditLoading] = useState(false);
    const [auditError, setAuditError] = useState<string | null>(null);

    useEffect(() => {
        if (!expanded) return;

        const controller = new AbortController();

        async function loadAudit() {
            setAuditLoading(true);
            setAuditError(null);

            try {
                const result = await getInvestigationAuditEvents(
                    investigation.id,
                    controller.signal
                );

                if (!controller.signal.aborted) {
                    setEvents(result);
                }
            } catch (err) {
                if (!controller.signal.aborted) {
                    setAuditError(
                        err instanceof Error
                            ? err.message
                            : "Failed to load audit events"
                    );
                }
            } finally {
                if (!controller.signal.aborted) {
                    setAuditLoading(false);
                }
            }
        }

        void loadAudit();

        return () => controller.abort();
    }, [expanded, investigation.id]);

    return (
        <article className="ops-history-card">
            <div className="ops-history-card-header">
                <div>
                    <div className="ops-history-card-title">
                        <span className="ops-history-card-icon">✦</span>
                        <h3>Investigation #{investigation.id}</h3>
                    </div>

                    <p className="ops-history-meta">
                        Order {investigation.order_number} ·{" "}
                        {formatDate(investigation.created_at)}
                    </p>
                </div>

                <StatusBadge status={investigation.status} />
            </div>

            <div className="ops-history-summary">
                <div>
                    <p className="ops-history-label">SPECIALIST AGENTS</p>

                    <div className="ops-history-tags">
                        {(investigation.selected_agents ?? []).length > 0 ? (
                            investigation.selected_agents.map((agent) => (
                                <span className="ops-agent-tag" key={agent}>
                                    {agent} agent
                                </span>
                            ))
                        ) : (
                            <span className="ops-history-empty">
                                No agents recorded
                            </span>
                        )}
                    </div>
                </div>

                <div>
                    <p className="ops-history-label">POLICY REFERENCES</p>

                    <div className="ops-history-tags">
                        {(investigation.policy_ids ?? []).length > 0 ? (
                            investigation.policy_ids.map((policy) => (
                                <span className="ops-policy-tag" key={policy}>
                                    {policy}
                                </span>
                            ))
                        ) : (
                            <span className="ops-history-empty">
                                No policies recorded
                            </span>
                        )}
                    </div>
                </div>
            </div>

            <div className="ops-history-actions">
                <button
                    type="button"
                    onClick={() => setExpanded((value) => !value)}
                    aria-expanded={expanded}
                    className="ops-history-expand"
                >
                    {expanded ? "Hide investigation ↑" : "View investigation →"}
                </button>

                <span className="ops-history-completed">
                    {investigation.completed_at
                        ? `Finished ${formatDate(investigation.completed_at)}`
                        : "Not finished"}
                </span>
            </div>

            {expanded && (
                <div className="ops-history-details">
                    <section className="ops-detail-section">
                        <h4>AI Investigation Report</h4>

                        <div className="ops-report-content">
                            {investigation.report ? (
                                <InvestigationReport report={investigation.report} />
                            ) : (
                                <p className="ops-history-empty">
                                    No report available
                                </p>
                            )}
                        </div>
                    </section>

                    <div className="ops-detail-grid">
                        <section className="ops-detail-section">
                            <h4>MCP / Agent Evidence</h4>
                            <pre className="ops-json-panel">
                                {formatJson(investigation.evidence)}
                            </pre>
                        </section>

                        <section className="ops-detail-section">
                            <h4>Evidence Verification</h4>
                            <pre className="ops-json-panel">
                                {formatJson(investigation.verification)}
                            </pre>
                        </section>
                    </div>

                    <section className="ops-detail-section">
                        <h4>Audit Timeline</h4>

                        {auditLoading && (
                            <p className="ops-history-empty">
                                Loading audit events...
                            </p>
                        )}

                        {auditError && (
                            <p role="alert" className="ops-error">
                                {auditError}
                            </p>
                        )}

                        {!auditLoading && !auditError && events.length === 0 && (
                            <p className="ops-history-empty">
                                No audit events available.
                            </p>
                        )}

                        {!auditLoading && !auditError && events.length > 0 && (
                            <ol className="ops-audit-timeline">
                                {events.map((event) => (
                                    <li key={event.id} className="ops-audit-event">
                                        <div className="ops-audit-dot" />

                                        <div className="ops-audit-content">
                                            <div className="ops-audit-heading">
                                                <strong>
                                                    {event.event_type.replaceAll("_", " ")}
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
                </div>
            )}
        </article>
    );
}

export default function InvestigationHistory({
    ticketId,
    refreshKey = 0,
}: Props) {
    const [investigations, setInvestigations] =
        useState<InvestigationRun[]>([]);

    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [reloadCount, setReloadCount] = useState(0);

    useEffect(() => {
        const controller = new AbortController();

        async function loadHistory() {
            setLoading(true);
            setError(null);

            try {
                const result = await getInvestigationHistory(
                    ticketId,
                    controller.signal
                );

                if (!controller.signal.aborted) {
                    setInvestigations(
                        [...result].sort((a, b) => b.id - a.id)
                    );
                }
            } catch (err) {
                if (!controller.signal.aborted) {
                    setError(
                        err instanceof Error
                            ? err.message
                            : "Unable to load investigation history"
                    );
                }
            } finally {
                if (!controller.signal.aborted) {
                    setLoading(false);
                }
            }
        }

        void loadHistory();

        return () => controller.abort();
    }, [ticketId, refreshKey, reloadCount]);

    return (
        <section className="ops-history">
            <div className="ops-history-heading">
                <div>
                    <p className="ops-history-eyebrow">
                        INVESTIGATION RECORDS
                    </p>

                    <h2>Investigation History</h2>

                    <p>
                        Previous AI investigations for ticket #{ticketId}
                    </p>
                </div>

                <button
                    type="button"
                    onClick={() => setReloadCount((value) => value + 1)}
                    disabled={loading}
                    className="ops-history-refresh"
                >
                    ↻ Refresh
                </button>
            </div>

            {loading && (
                <p role="status" className="ops-history-empty">
                    Loading investigation history...
                </p>
            )}

            {!loading && error && (
                <p role="alert" className="ops-error">
                    {error}
                </p>
            )}

            {!loading && !error && investigations.length === 0 && (
                <div className="ops-history-empty-state">
                    <span>◇</span>
                    <h3>No investigations found</h3>
                    <p>Run an AI investigation to create the first record.</p>
                </div>
            )}

            {!loading && !error && investigations.length > 0 && (
                <div className="ops-history-list">
                    {investigations.map((investigation) => (
                        <InvestigationCard
                            key={investigation.id}
                            investigation={investigation}
                        />
                    ))}
                </div>
            )}
        </section>
    );
}
