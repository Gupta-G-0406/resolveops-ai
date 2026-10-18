import { Link } from "react-router";

export default function NotFoundPage() {
    return (
        <section className="ops-panel">
            <h2>Page not found</h2>
            <p className="ops-muted">
                The requested page does not exist.
            </p>
            <Link to="/dashboard" className="ops-primary-btn">
                Return to Dashboard →
            </Link>
        </section>
    );
}