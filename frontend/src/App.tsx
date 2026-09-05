import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { DatabaseModeProvider } from './context/DatabaseModeContext';
import { AppLayout } from './components/layout/AppLayout';

import { DashboardPage } from './pages/DashboardPage';
import { DisputesPage } from './pages/DisputesPage';
import { DisputeDetailPage } from './pages/DisputeDetailPage';
import { RazorpayWebhookPage } from './pages/RazorpayWebhookPage';
import { HistoryPage } from './pages/HistoryPage';
import { SettingsPage } from './pages/SettingsPage';

export const App: React.FC = () => {
  return (
    <DatabaseModeProvider>
      <Routes>
        {/* Main Merchant Portal Shell Routes */}
        <Route path="/" element={<AppLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="disputes" element={<DisputesPage />} />
          <Route path="disputes/:disputeId" element={<DisputeDetailPage />} />
          <Route path="history" element={<HistoryPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>

        {/* Standalone Razorpay Webhook Simulation Website */}
        <Route path="/webhooks" element={<RazorpayWebhookPage />} />
        <Route path="/webhook" element={<Navigate to="/webhooks" replace />} />

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </DatabaseModeProvider>
  );
};

