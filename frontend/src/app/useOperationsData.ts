import { useContext } from "react";
import { OperationsContext } from "./operationsContext";

export function useOperationsData() {
    const context = useContext(OperationsContext);

    if (!context) {
        throw new Error(
            "useOperationsData must be used inside OperationsDataProvider"
        );
    }

    return context;
}