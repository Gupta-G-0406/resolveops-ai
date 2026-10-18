
export interface Payment {
  id: number;
  status: string;
  amount_paise: number;
}

export interface Shipment {
  id: number;
  status: string;
  delivery_proof_available: boolean;
}

export interface Order {
  id: number;
  order_number: string;
  customer_name: string;
  total_amount_paise: number;
  status: string;
  payment: Payment | null;
  shipment: Shipment | null;
}

export interface Ticket {
  id: number;
  order_id: number;
  subject: string;
  description: string;
  status: string;
}


export interface TicketDetail extends Ticket {
  order: Order;
}


export interface InvestigationVerification {
  status: "passed" | "incomplete";
  checks: Record<string, string>;
  problems: string[];
}

export interface InvestigationResponse {
  ticket_id: number;
  order_number: string;
  status: "completed" | "needs_review";
  report: string;
  tools_used: string[];

  selected_agents: string[];
  policy_ids: string[];
  verification: InvestigationVerification;
}
