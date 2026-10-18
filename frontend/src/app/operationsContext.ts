import { createContext } from "react";
import type { Order, Ticket } from "../types";

export type OperationsData = {
    tickets: Ticket[];
    orders: Order[];
    loading: boolean;
    error: string | null;
    refresh: () => Promise<void>;
};

export const OperationsContext =
    createContext<OperationsData | null>(null);