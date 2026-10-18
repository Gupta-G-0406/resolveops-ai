import type {
    AuditEvent,
    InvestigationListParams,
    InvestigationListResponse,
    InvestigationRun,
    InvestigationStats
} from "../types/investigation";
const API_BASE_URL =
    import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export async function getInvestigationHistory(
    ticketId: number,
    signal?: AbortSignal
): Promise<InvestigationRun[]> {
    const response = await fetch(
        `${API_BASE_URL}/api/tickets/${ticketId}/investigations`,
        {
            method: "GET",
            headers: {
                Accept: "application/json",
            },
            signal,
        }
    );

    if (!response.ok) {
        throw new Error(
            `Failed to load investigation history (${response.status})`
        );
    }

    const data: unknown = await response.json();

    // Supports either a direct array or an object containing
    // an "investigations" array.
    if (Array.isArray(data)) {
        return data as InvestigationRun[];
    }

    if (
        typeof data === "object" &&
        data !== null &&
        "investigations" in data &&
        Array.isArray(data.investigations)
    ) {
        return data.investigations as InvestigationRun[];
    }

    throw new Error("Unexpected investigation history API response");
}



async function investigationRequest<T>(
    path: string,
    signal?: AbortSignal
): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${path}`, {
        method: "GET",
        headers: {
            Accept: "application/json",
        },
        signal,
    });

    if (!response.ok) {
        throw new Error(
            `Investigation API error (${response.status})`
        );
    }

    return (await response.json()) as T;
}

export function getAllInvestigations(
    params: InvestigationListParams = {},
    signal?: AbortSignal
): Promise<InvestigationListResponse> {
    const query = new URLSearchParams();

    query.set("limit", String(params.limit ?? 10));
    query.set("offset", String(params.offset ?? 0));

    if (params.ticket_id !== undefined) {
        query.set("ticket_id", String(params.ticket_id));
    }

    if (params.status) {
        query.set("status", params.status);
    }

    return investigationRequest<InvestigationListResponse>(
        `/api/investigations?${query.toString()}`,
        signal
    );
}

export function getInvestigationDetail(
    investigationId: number,
    signal?: AbortSignal
): Promise<InvestigationRun> {
    return investigationRequest<InvestigationRun>(
        `/api/investigations/${investigationId}`,
        signal
    );
}

export function getInvestigationAuditEvents(
    investigationId: number,
    signal?: AbortSignal
): Promise<AuditEvent[]> {
    return investigationRequest<AuditEvent[]>(
        `/api/investigations/${investigationId}/audit-events`,
        signal
    );
}


export function getInvestigationStats(
    signal?: AbortSignal
): Promise<InvestigationStats> {
    return investigationRequest<InvestigationStats>(
        "/api/investigations/stats",
        signal
    );
}