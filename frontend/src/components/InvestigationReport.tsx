import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type InvestigationReportProps = {
    report: string;
};

export default function InvestigationReport({
    report,
}: InvestigationReportProps) {
    return (
        <div className="investigation-report">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {report}
            </ReactMarkdown>
        </div>
    );
}