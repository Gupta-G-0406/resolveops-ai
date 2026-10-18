
import { useEffect, useState } from "react";
import { api } from "./services/api";
import type { Order, Ticket } from "./types";
import TicketDetail from "./components/TicketDetail";
import GlobalInvestigationHistory from "./components/GlobalInvestigationHistory";
import { getInvestigationStats } from "./services/investigationApi";
import type { InvestigationStats } from "./types/investigation";
import "./App.css";

type Page = "dashboard" | "tickets" | "investigations";

const navItems: { id: Page; label: string; icon: string }[] = [
  { id: "dashboard", label: "Dashboard", icon: "◫" },
  { id: "tickets", label: "Support Tickets", icon: "▤" },
  { id: "investigations", label: "Investigations", icon: "◇" },
];

function App() {
  const [page, setPage] = useState<Page>("dashboard");
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [selectedTicketId, setSelectedTicketId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<InvestigationStats | null>(null);
  const [statsError, setStatsError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [search, setSearch] = useState("");

  useEffect(() => {
    let active = true;

    async function loadDashboard() {
      try {
        const [ticketData, orderData] = await Promise.all([
          api.getTickets(),
          api.getOrders(),
        ]);

        if (!active) return;

        setTickets(ticketData);
        setOrders(orderData);
        setError(null);
      } catch (err) {
        if (active) {
          setError(
            err instanceof Error ? err.message : "Failed to load dashboard"
          );
        }
      } finally {
        if (active) setLoading(false);
      }
    }

    void loadDashboard();

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    const controller = new AbortController();

    async function loadStats() {
      try {
        const result = await getInvestigationStats(controller.signal);

        if (!controller.signal.aborted) {
          setStats(result);
          setStatsError(null);
        }
      } catch (err) {
        if (!controller.signal.aborted) {
          setStatsError(
            err instanceof Error ? err.message : "Failed to load analytics"
          );
        }
      }
    }

    void loadStats();

    return () => controller.abort();
  }, [refreshKey]);

  function navigate(nextPage: Page) {
    setSelectedTicketId(null);
    setPage(nextPage);

    if (nextPage === "dashboard") {
      setRefreshKey((value) => value + 1);
    }
  }

  function backFromTicket() {
    setSelectedTicketId(null);
    setRefreshKey((value) => value + 1);
  }

  const openTickets = tickets.filter(
    (ticket) => ticket.status.toLowerCase() === "open"
  ).length;

  const filteredTickets = tickets.filter((ticket) => {
    const order = orders.find((item) => item.id === ticket.order_id);
    const query = search.trim().toLowerCase();

    return (
      ticket.subject.toLowerCase().includes(query) ||
      String(ticket.id).includes(query) ||
      (order?.order_number ?? "").toLowerCase().includes(query)
    );
  });

  const metrics = [
    {
      label: "Total Tickets",
      value: tickets.length,
      icon: "▤",
      tone: "violet",
    },
    {
      label: "Open Tickets",
      value: openTickets,
      icon: "◉",
      tone: "amber",
    },
    {
      label: "Total Orders",
      value: orders.length,
      icon: "▣",
      tone: "cyan",
    },
    {
      label: "AI Investigations",
      value: stats?.total ?? "—",
      icon: "✦",
      tone: "green",
    },
  ];

  const pageTitle = selectedTicketId !== null
    ? `Ticket #${selectedTicketId}`
    : page === "dashboard"
      ? "Operations Overview"
      : page === "tickets"
        ? "Support Tickets"
        : "Investigation History";

  return (
    <div className="ops-shell">
      <aside className="ops-sidebar">
        <div className="ops-brand">
          <div className="ops-brand-icon">✦</div>
          <div>
            <div className="ops-brand-title">ResolveOps AI</div>
            <div className="ops-brand-subtitle">INTELLIGENT OPERATIONS</div>
          </div>
        </div>

        <div className="ops-nav-label">WORKSPACE</div>

        <nav className="ops-nav" aria-label="Main navigation">
          {navItems.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => navigate(item.id)}
              className={`ops-nav-item ${selectedTicketId !== null
                ? item.id === "tickets"
                : page === item.id
                  ? "ops-nav-active"
                  : ""
                }`}
            >
              <span className="ops-nav-icon">{item.icon}</span>
              {item.label}
            </button>
          ))}
        </nav>

        <div className="ops-sidebar-footer">
          <div className="ops-system-dot" />
          <div>
            <div className="ops-footer-title">AI Operations</div>
            <div className="ops-footer-subtitle">
              LangGraph · MCP · Agentic RAG
            </div>
          </div>
        </div>
      </aside>

      <div className="ops-main">
        <header className="ops-topbar">
          <div>
            <p className="ops-breadcrumb">
              {selectedTicketId !== null
                ? `RESOLVEOPS / TICKETS / #${selectedTicketId}`
                : `RESOLVEOPS / ${page.toUpperCase()}`}
            </p>
            <h1 className="ops-page-title">{pageTitle}</h1>
          </div>

          <div className="ops-topbar-right">
            <span className="ops-environment">
              <span className="ops-system-dot" />
              Demo Environment
            </span>

            <div className="ops-avatar" aria-label="AI operations">
              AI
            </div>
          </div>
        </header>

        <main className="ops-content">
          {selectedTicketId !== null ? (
            <TicketDetail
              ticketId={selectedTicketId}
              onBack={backFromTicket}
            />
          ) : page === "investigations" ? (
            <GlobalInvestigationHistory
              onBack={() => navigate("dashboard")}
              onOpenTicket={(ticketId) => {
                setSelectedTicketId(ticketId);
              }}
            />
          ) : (
            <>
              {page === "dashboard" && (
                <>
                  <section className="ops-welcome">
                    <div>
                      <p className="ops-eyebrow">AI-POWERED SUPPORT INTELLIGENCE</p>
                      <h2>Welcome to your operations center</h2>
                      <p>
                        Monitor support activity, investigate issues and
                        review AI-generated evidence in one workspace.
                      </p>
                    </div>

                    <button
                      type="button"
                      className="ops-primary-btn"
                      onClick={() => navigate("investigations")}
                    >
                      View Investigations →
                    </button>
                  </section>

                  <section>
                    <div className="ops-section-heading">
                      <h2>Support Overview</h2>
                      <span>Live backend data</span>
                    </div>

                    {error && <p role="alert" className="ops-error">{error}</p>}

                    <div className="ops-metrics">
                      {metrics.map((metric) => (
                        <div
                          className={`ops-metric ops-tone-${metric.tone}`}
                          key={metric.label}
                        >
                          <div className="ops-metric-top">
                            <span>{metric.label}</span>
                            <span className="ops-metric-icon">
                              {metric.icon}
                            </span>
                          </div>
                          <div className="ops-metric-value">
                            {loading ? "…" : metric.value}
                          </div>
                        </div>
                      ))}
                    </div>
                  </section>

                  <section className="ops-analytics">
                    <div className="ops-section-heading">
                      <h2>AI Investigation Analytics</h2>
                      <span>PostgreSQL investigation records</span>
                    </div>

                    {statsError && (
                      <p role="alert" className="ops-error">{statsError}</p>
                    )}

                    <div className="ops-analytics-grid">
                      <div className="ops-panel">
                        <h3>Investigation Outcomes</h3>

                        {stats ? (
                          <>
                            <div className="ops-outcome-number">
                              {stats.success_rate.toFixed(1)}%
                            </div>
                            <p className="ops-muted">Completion rate</p>

                            <div className="ops-progress-track">
                              {stats.total > 0 && (
                                <>
                                  <div
                                    className="ops-progress-completed"
                                    style={{
                                      width: `${stats.completed / stats.total * 100}%`,
                                    }}
                                  />
                                  <div
                                    className="ops-progress-review"
                                    style={{
                                      width: `${stats.needs_review / stats.total * 100}%`,
                                    }}
                                  />
                                  <div
                                    className="ops-progress-running"
                                    style={{
                                      width: `${stats.running / stats.total * 100}%`,
                                    }}
                                  />
                                  <div
                                    className="ops-progress-failed"
                                    style={{
                                      width: `${stats.failed / stats.total * 100}%`,
                                    }}
                                  />
                                </>
                              )}
                            </div>

                            <div className="ops-legend">
                              <span>● Completed: {stats.completed}</span>
                              <span>● Review: {stats.needs_review}</span>
                              <span>● Running: {stats.running}</span>
                              <span>● Failed: {stats.failed}</span>
                            </div>
                          </>
                        ) : (
                          <p className="ops-muted">
                            {statsError ? "Analytics unavailable" : "Loading analytics..."}
                          </p>
                        )}
                      </div>

                      <div className="ops-panel ops-agent-panel">
                        <div className="ops-agent-icon">✦</div>
                        <h3>Multi-Agent Intelligence</h3>
                        <p>
                          LangGraph coordinates specialist agents that retrieve
                          order, shipment and policy evidence using MCP tools
                          and Agentic RAG.
                        </p>
                        <div className="ops-agent-tags">
                          <span>LangGraph</span>
                          <span>MCP</span>
                          <span>ChromaDB</span>
                          <span>Groq</span>
                        </div>
                      </div>
                    </div>
                  </section>
                </>
              )}

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
                  <p className="ops-table-message">
                    No matching tickets found.
                  </p>
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
                          const order = orders.find(
                            (item) => item.id === ticket.order_id
                          );

                          return (
                            <tr key={ticket.id}>
                              <td>#{ticket.id}</td>
                              <td className="ops-ticket-subject">
                                {ticket.subject}
                              </td>
                              <td>{order?.order_number ?? "Unknown"}</td>
                              <td>
                                <span className={`ops-status ${ticket.status.toLowerCase() === "open"
                                  ? "ops-status-open"
                                  : "ops-status-other"
                                  }`}>
                                  {ticket.status}
                                </span>
                              </td>
                              <td>
                                <button
                                  type="button"
                                  className="ops-view-btn"
                                  onClick={() => setSelectedTicketId(ticket.id)}
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
            </>
          )}
        </main>
      </div>
    </div>
  );
}

export default App;
