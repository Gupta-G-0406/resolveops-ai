import {
    useEffect,
    useState,
    type ReactNode,
} from "react";

import { api } from "../services/api";
import type { Order, Ticket } from "../types";
import { OperationsContext } from "./operationsContext";

export function OperationsDataProvider({
    children,
}: {
    children: ReactNode;
}) {
    const [tickets, setTickets] = useState<Ticket[]>([]);
    const [orders, setOrders] = useState<Order[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [refreshKey, setRefreshKey] = useState(0);

    useEffect(() => {
        let active = true;

        async function loadData() {
            setLoading(true);

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
                        err instanceof Error
                            ? err.message
                            : "Failed to load operations data"
                    );
                }
            } finally {
                if (active) setLoading(false);
            }
        }

        void loadData();

        return () => {
            active = false;
        };
    }, [refreshKey]);

    async function refresh() {
        setRefreshKey((value) => value + 1);
    }

    return (
        <OperationsContext.Provider
            value={{ tickets, orders, loading, error, refresh }}
        >
            {children}
        </OperationsContext.Provider>
    );
}