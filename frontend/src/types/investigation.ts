export interface InvestigationRun {
    id: number;
    ticket_id: number;
    order_number: string;
    status: string;
    report: string | null;
    selected_agents: string[];
    policy_ids: string[];
    evidence: Record<string, unknown>;
    verification: Record<string, unknown>;
    created_at: string;
    completed_at: string | null;
}

export interface AuditEvent {
    id: number;
    investigation_id: number;
    event_type: string;
    details: Record<string, unknown>;
    created_at: string;
}


export interface InvestigationListItem {
    id: number;
    ticket_id: number;
    order_number: string;
    status: string;
    selected_agents: string[];
    policy_ids: string[];
    created_at: string;
    completed_at: string | null;
}

export interface InvestigationListResponse {
    items: InvestigationListItem[];
    total: number;
    limit: number;
    offset: number;
}

export interface InvestigationListParams {
    limit?: number;
    offset?: number;
    ticket_id?: number;
    status?: string;
}

export interface InvestigationStats {
    total: number;
    completed: number;
    needs_review: number;
    failed: number;
    running: number;
    success_rate: number;
}