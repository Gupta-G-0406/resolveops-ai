import { NavLink, Outlet, useLocation, useParams } from "react-router";

const navItems = [
    { path: "/dashboard", label: "Dashboard", icon: "◫" },
    { path: "/tickets", label: "Support Tickets", icon: "▤" },
    { path: "/investigations", label: "Investigations", icon: "◇" },
];

export default function AppLayout() {
    const location = useLocation();
    const { ticketId } = useParams();

    const isTicketDetail = /^\/tickets\/[^/]+$/.test(location.pathname);

    const pageTitle = isTicketDetail
        ? `Ticket #${ticketId ?? location.pathname.split("/").pop()}`
        : location.pathname.startsWith("/investigations")
            ? "Investigation History"
            : location.pathname.startsWith("/tickets")
                ? "Support Tickets"
                : "Operations Overview";

    const breadcrumb = isTicketDetail
        ? `RESOLVEOPS / TICKETS / #${ticketId ?? location.pathname.split("/").pop()}`
        : `RESOLVEOPS / ${location.pathname.split("/")[1]?.toUpperCase() || "DASHBOARD"}`;

    return (
        <div className="ops-shell">
            <aside className="ops-sidebar">
                <div className="ops-brand">
                    <div className="ops-brand-icon">✦</div>
                    <div>
                        <div className="ops-brand-title">ResolveOps AI</div>
                        <div className="ops-brand-subtitle">
                            INTELLIGENT OPERATIONS
                        </div>
                    </div>
                </div>

                <div className="ops-nav-label">WORKSPACE</div>

                <nav className="ops-nav" aria-label="Main navigation">
                    {navItems.map((item) => (
                        <NavLink
                            key={item.path}
                            to={item.path}
                            className={({ isActive }) =>
                                `ops-nav-item ${isActive ? "ops-nav-active" : ""
                                }`
                            }
                        >
                            <span className="ops-nav-icon">{item.icon}</span>
                            {item.label}
                        </NavLink>
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
                        <p className="ops-breadcrumb">{breadcrumb}</p>
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
                    <Outlet />
                </main>
            </div>
        </div>
    );
}