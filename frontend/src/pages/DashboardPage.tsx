import { useNavigate } from "react-router";
import TicketsTable from "../components/TicketsTable";

export default function DashboardPage() {
    const navigate = useNavigate();

    return (
        <>
            <section className="ops-welcome">
                <div>
                    <p className="ops-eyebrow">
                        AI-POWERED SUPPORT INTELLIGENCE
                    </p>

                    <h2>Welcome to your operations center</h2>

                    <p>
                        Monitor support activity, investigate issues and
                        review AI-generated evidence in one workspace.
                    </p>
                </div>

                <button
                    type="button"
                    className="ops-primary-btn"
                    onClick={() => navigate("/investigations")}
                >
                    View Investigations →
                </button>
            </section>

            {/* Keep your existing Support Overview and Analytics sections here. */}

            <TicketsTable />
        </>
    );
}