import { useMemo, useState } from "react";
import { useNavigate } from "react-router";
import { useOperationsData } from "../app/useOperationsData";
export default function TicketsTable() {
    const { tickets, orders, loading, error } = useOperationsData();
    const [search, setSearch] = useState("");
    const navigate = useNavigate();

    const ordersById = useMemo(
        () => new Map(orders.map((order) => [order.id, order])),
        [orders]
    );

    const filteredTickets = useMemo(() => {
        const query = search.trim().toLowerCase();

        return tickets.filter((ticket) => {
            const order = ordersById.get(ticket.order_id);

            return (
                ticket.subject.toLowerCase().includes(query) ||
                String(ticket.id).includes(query) ||
                (order?.order_number ?? "").toLowerCase().includes(query)
            );
        });
    }, [tickets, ordersById, search]);

    return (
        <section className="ops-table-panel">
            <div className="ops-table-header">
                <div>
                    <h2>Customer Support Tickets</h2>
                    <p>Select a ticket to launch an AI investigation</p>
                </div>

                <input
                    className="ops-search"
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                    placeholder="Search tickets or orders..."
                    aria-label="Search tickets"
                />
            </div>

            {loading ? (
                <p className="ops-table-message">Loading tickets...</p>
            ) : error ? (
                <p role="alert" className="ops-table-message ops-error">
                    {error}
                </p>
            ) : filteredTickets.length === 0 ? (
                <p className="ops-table-message">No matching tickets found.</p>
            ) : (
                <div className="ops-table-scroll">
                    <table className="ops-table">
                        <thead>
                            <tr>
                                <th>Ticket</th>
                                <th>Subject</th>
                                <th>Order</th>
                                <th>Status</th>
                                <th>Action</th>
                            </tr>
                        </thead>

                        <tbody>
                            {filteredTickets.map((ticket) => {
                                const order = ordersById.get(ticket.order_id);

                                return (
                                    <tr key={ticket.id}>
                                        <td>#{ticket.id}</td>
                                        <td className="ops-ticket-subject">{ticket.subject}</td>
                                        <td>{order?.order_number ?? "Unknown"}</td>
                                        <td>
                                            <span
                                                className={`ops-status ${ticket.status.toLowerCase() === "open"
                                                    ? "ops-status-open"
                                                    : "ops-status-other"
                                                    }`}
                                            >
                                                {ticket.status}
                                            </span>
                                        </td>
                                        <td>
                                            <button
                                                type="button"
                                                className="ops-view-btn"
                                                onClick={() => navigate(`/tickets/${ticket.id}`)}
                                            >
                                                Investigate →
                                            </button>
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            )}
        </section>
    );
}