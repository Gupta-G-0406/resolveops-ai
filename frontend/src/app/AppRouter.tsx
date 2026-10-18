import {
    createBrowserRouter,
    Navigate,
    RouterProvider,
} from "react-router";

import AppLayout from "./AppLayout";
import DashboardPage from "../pages/DashboardPage";
import TicketsPage from "../pages/TicketsPage";
import TicketDetailPage from "../pages/TicketDetailPage";
import InvestigationsPage from "../pages/InvestigationsPage";
import NotFoundPage from "../pages/NotFoundPage";

const router = createBrowserRouter([
    {
        path: "/",
        element: <AppLayout />,
        children: [
            { index: true, element: <Navigate to="/dashboard" replace /> },
            { path: "dashboard", element: <DashboardPage /> },
            { path: "tickets", element: <TicketsPage /> },
            { path: "tickets/:ticketId", element: <TicketDetailPage /> },
            { path: "investigations", element: <InvestigationsPage /> },
            { path: "*", element: <NotFoundPage /> },
        ],
    },
]);

export default function AppRouter() {
    return <RouterProvider router={router} />;
}