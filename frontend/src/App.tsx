import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { LiveProvider } from './context/LiveProvider';
import { AppLayout } from './components/layout/AppLayout';
import { DashboardPage } from './pages/DashboardPage';
import { FleetPage } from './pages/FleetPage';
import { VehicleDetailPage } from './pages/VehicleDetailPage';
import { DiagnosticsPage } from './pages/DiagnosticsPage';
import { ServicePage } from './pages/ServicePage';
import { AlertsPage } from './pages/AlertsPage';

export default function App() {
  return (
    <BrowserRouter>
      <LiveProvider>
        <Routes>
          <Route element={<AppLayout />}>
            <Route index element={<DashboardPage />} />
            <Route path="fleet" element={<FleetPage />} />
            <Route path="fleet/:vehicleId" element={<VehicleDetailPage />} />
            <Route path="diagnostics" element={<DiagnosticsPage />} />
            <Route path="service" element={<ServicePage />} />
            <Route path="alerts" element={<AlertsPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </LiveProvider>
    </BrowserRouter>
  );
}
