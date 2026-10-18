import { useNavigate, useParams } from "react-router";
import TicketDetail from "../components/TicketDetail";
import { useOperationsData } from "../app/useOperationsData";
export default function TicketDetailPage() {
    const { ticketId } = useParams();
    const navigate = useNavigate();
    const { refresh } = useOperationsData();

    const id = Number(ticketId);

    if (!Number.isSafeInteger(id) || id <= 0) {
        return <p role="alert" className="ops-error">Invalid ticket ID.</p>;
    }

    return (
        <TicketDetail
            ticketId={id}
            onBack={() => {
                void refresh();
                navigate("/tickets");
            }}
        />
    );
}