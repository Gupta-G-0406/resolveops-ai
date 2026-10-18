import { useNavigate } from "react-router";
import GlobalInvestigationHistory from "../components/GlobalInvestigationHistory";

export default function InvestigationsPage() {
    const navigate = useNavigate();

    return (
        <GlobalInvestigationHistory
            onBack={() => navigate("/dashboard")}
            onOpenTicket={(ticketId) => navigate(`/tickets/${ticketId}`)}
        />
    );
}