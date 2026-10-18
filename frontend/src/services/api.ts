import type { InvestigationResponse, Order, Ticket, TicketDetail } from "../types";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ??
  "http://127.0.0.1:8000";


async function request<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const response = await fetch(
    `${API_BASE_URL}${path}`,
    options,
  );

  if (!response.ok) {
    const body = await response.text();

    throw new Error(
      `API error ${response.status}: ${body}`
    );
  }

  return (await response.json()) as T;
}


export const api = {
  getTickets: () => request<Ticket[]>("/api/tickets"),

  getOrders: () => request<Order[]>("/api/orders"),

  getOrder: (id: number) =>
    request<Order>(`/api/orders/${id}`),

  getTicket: (id: number) =>
    request<TicketDetail>(`/api/tickets/${id}`),
  investigateTicket: (ticketId: number) =>
    request<InvestigationResponse>(
      `/api/tickets/${ticketId}/investigate`,
      { method: "POST" },
    ),
};