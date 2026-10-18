import AppRouter from "./app/AppRouter";
import { OperationsDataProvider } from "./app/OperationsDataContext";
import "./App.css";

export default function App() {
  return (
    <OperationsDataProvider>
      <AppRouter />
    </OperationsDataProvider>
  );
}