
import { useEffect, useState } from "react";

import { api } from "../services/api";
import type { TicketDetail as TicketDetailType, InvestigationResponse, } from "../types";
import InvestigationReport from "./InvestigationReport";
import InvestigationHistory from "../components/InvestigationHistory";
interface Props {
    ticketId: number;
    onBack: () => void;
}

export default function TicketDetail({
    ticketId,
    onBack,
}: Props) {
    const [ticket, setTicket] =
        useState<TicketDetailType | null>(null);

    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const [investigation, setInvestigation] =
        useState<InvestigationResponse | null>(null);

    const [investigating, setInvestigating] =
        useState(false);

    const [investigationError, setInvestigationError] =
        useState<string | null>(null);

    const [historyRefreshKey, setHistoryRefreshKey] = useState(0);


    async function handleInvestigate() {
        if (investigating) return;

        setInvestigating(true);
        setInvestigationError(null);
        setInvestigation(null);

        try {
            const result = await api.investigateTicket(ticketId);

            setInvestigation(result);

            // Refresh saved investigation history after the API succeeds.
            setHistoryRefreshKey((previous) => previous + 1);
        } catch (err) {
            setInvestigationError(
                err instanceof Error
                    ? err.message
                    : "Investigation failed"
            );
        } finally {
            setInvestigating(false);
        }
    }


    useEffect(() => {
        let active = true;

        async function loadTicket() {
            setLoading(true);
            setError(null);
            setTicket(null);
            setInvestigation(null);
            setInvestigationError(null);

            try {
                const data = await api.getTicket(ticketId);

                if (active) {
                    setTicket(data);
                }
            } catch (err) {
                if (active) {
                    setError(
                        err instanceof Error
                            ? err.message
                            : "Failed to load ticket"
                    );
                }
            } finally {
                if (active) {
                    setLoading(false);
                }
            }
        }

        void loadTicket();

        return () => {
            active = false;
        };
    }, [ticketId]);

    if (loading) {
        return <p className="p-8">Loading investigation context...</p>;
    }

    if (error || !ticket) {
        return (
            <div className="space-y-4 p-8">
                <p className="text-red-600">
                    {error ?? "Ticket not found"}
                </p>
                <button onClick={onBack}>Back to tickets</button>
            </div>
        );
    }

    const { order } = ticket;

    return (
        <div className="space-y-6">
            <button
                onClick={onBack}
                className="text-sm font-medium text-blue-600"
            >
                ← Back to tickets
            </button>

            <div className="rounded-xl bg-white p-6 shadow-sm">
                <h2 className="text-2xl font-bold">
                    Ticket #{ticket.id}
                </h2>
                <p className="mt-2 font-medium">{ticket.subject}</p>
                <p className="mt-2 text-slate-600">
                    {ticket.description}
                </p>
            </div>

            <div className="grid gap-4 md:grid-cols-3">
                <InfoCard
                    title="Order"
                    lines={[
                        `Number: ${order.order_number}`,
                        `Status: ${order.status}`,
                        `Customer: ${order.customer_name}`,
                        `Amount: ₹${(
                            order.total_amount_paise / 100
                        ).toFixed(2)}`,
                    ]}
                />

                <InfoCard
                    title="Payment"
                    lines={[
                        `Status: ${order.payment?.status ?? "Unknown"}`,
                        `Amount: ₹${(
                            (order.payment?.amount_paise ?? 0) / 100
                        ).toFixed(2)}`,
                    ]}
                />

                <InfoCard
                    title="Shipment"
                    lines={[
                        `Status: ${order.shipment?.status ?? "Unknown"}`,
                        `Delivery proof: ${order.shipment?.delivery_proof_available
                            ? "Available"
                            : "Not available"
                        }`,
                    ]}
                />
            </div>


            <section className="rounded-xl border border-slate-200 bg-white p-6">
                <div className="flex flex-wrap items-center justify-between gap-4">
                    <div>
                        <h3 className="text-lg font-semibold">
                            AI Investigation
                        </h3>
                        <p className="mt-1 text-sm text-slate-500">
                            Investigate this ticket using Groq, LangGraph,
                            and MCP business tools.
                        </p>
                    </div>

                    <button
                        type="button"
                        onClick={handleInvestigate}
                        disabled={investigating}
                        className="rounded-lg bg-blue-600 px-5 py-3 font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                        {investigating
                            ? "Investigating..."
                            : "Investigate with AI"}
                    </button>
                </div>

                {investigating && (
                    <p className="mt-5 text-sm text-blue-600">
                        AI is retrieving order evidence and analyzing the complaint...
                    </p>
                )}

                {investigationError && (
                    <p className="mt-5 text-sm text-red-600">
                        {investigationError}
                    </p>
                )}


                {investigation && (
                    <div className="mt-6 space-y-5">

                        {/* Investigation status */}
                        <div className="flex flex-wrap items-center gap-3">
                            <span
                                className={`rounded-full px-3 py-1 text-xs font-semibold ${investigation.status === "completed"
                                    ? "bg-green-100 text-green-700"
                                    : "bg-amber-100 text-amber-700"
                                    }`}
                            >
                                {investigation.status === "completed"
                                    ? "Evidence Retrieved"
                                    : "Needs Review"}
                            </span>

                            <span className="text-sm text-slate-500">
                                Order: {investigation.order_number}
                            </span>
                        </div>

                        {/* Selected specialist agents */}
                        <div>
                            <h4 className="mb-2 font-semibold text-slate-800">
                                Specialist Agents
                            </h4>

                            <div className="flex flex-wrap gap-2">
                                {investigation.selected_agents.map((agent) => (
                                    <span
                                        key={agent}
                                        className="rounded-lg bg-blue-50 px-3 py-2 text-sm text-blue-700"
                                    >
                                        {agent.charAt(0).toUpperCase() + agent.slice(1)}
                                        {" Agent"}
                                    </span>
                                ))}
                            </div>
                        </div>

                        {/* Retrieved company policies */}
                        <div>
                            <h4 className="mb-2 font-semibold text-slate-800">
                                Retrieved Policies
                            </h4>

                            {investigation.policy_ids.length > 0 ? (
                                <div className="flex flex-wrap gap-2">
                                    {investigation.policy_ids.map((policyId) => (
                                        <span
                                            key={policyId}
                                            className="rounded-lg bg-purple-50 px-3 py-2 text-sm text-purple-700"
                                        >
                                            {policyId}
                                        </span>
                                    ))}
                                </div>
                            ) : (
                                <p className="text-sm text-amber-600">
                                    No policy evidence retrieved.
                                </p>
                            )}
                        </div>

                        {/* Evidence verification */}
                        <div className="rounded-lg border border-slate-200 p-4">
                            <h4 className="mb-3 font-semibold text-slate-800">
                                Evidence Verification
                            </h4>

                            <p className="mb-3 text-sm">
                                Status:{" "}
                                <strong>
                                    {investigation.verification.status}
                                </strong>
                            </p>

                            <div className="space-y-2">
                                {Object.entries(
                                    investigation.verification.checks
                                ).map(([agent, status]) => (
                                    <div
                                        key={agent}
                                        className="flex justify-between text-sm"
                                    >
                                        <span className="capitalize text-slate-600">
                                            {agent}
                                        </span>
                                        <span className="font-medium text-slate-800">
                                            {status}
                                        </span>
                                    </div>
                                ))}
                            </div>

                            {investigation.verification.problems.length > 0 && (
                                <ul className="mt-3 list-disc pl-5 text-sm text-red-600">
                                    {investigation.verification.problems.map(
                                        (problem, index) => (
                                            <li key={index}>{problem}</li>
                                        )
                                    )}
                                </ul>
                            )}
                        </div>

                        {/* Final AI investigation report */}
                        <div className="rounded-lg bg-slate-50 p-5">
                            <h4 className="mb-3 font-semibold text-slate-800">
                                Multi-Agent Investigation Report
                            </h4>

                            <InvestigationReport report={investigation.report} />
                        </div>

                        <p className="text-xs text-slate-500">
                            AI-generated investigation based on available business
                            records and synthetic demo policies. No refund or
                            financial action has been executed.
                        </p>
                    </div>
                )}

            </section>

            {/* Previous AI investigations saved in PostgreSQL */}
            <section className="rounded-xl border border-slate-200 bg-white p-6">
                <InvestigationHistory
                    ticketId={ticket.id}
                    refreshKey={historyRefreshKey}
                />
            </section>

        </div>
    );
}

function InfoCard({
    title,
    lines,
}: {
    title: string;
    lines: string[];
}) {
    return (
        <div className="rounded-xl bg-white p-5 shadow-sm">
            <h3 className="mb-3 font-semibold">{title}</h3>
            {lines.map((line) => (
                <p key={line} className="mt-2 text-sm text-slate-600">
                    {line}
                </p>
            ))}
        </div>
    );
}
