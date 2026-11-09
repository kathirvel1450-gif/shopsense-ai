import { lazy, Suspense } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import AppShell from './components/layout/AppShell.jsx';
import { LoadingState } from './components/common/States.jsx';
import Overview from './pages/Overview.jsx';

const DataQuality = lazy(() => import('./pages/DataQuality.jsx'));
const CustomerIntelligence = lazy(() => import('./pages/CustomerIntelligence.jsx'));
const SupportIntelligence = lazy(() => import('./pages/SupportIntelligence.jsx'));
const AIAssistant = lazy(() => import('./pages/AIAssistant.jsx'));
const SettingsPage = lazy(() => import('./pages/Settings.jsx'));

export default function App() {
  return <Suspense fallback={<main className="main-content"><LoadingState /></main>}><Routes><Route path="/" element={<AppShell />}>
    <Route index element={<Overview />} />
    <Route path="data-quality" element={<DataQuality />} />
    <Route path="customers" element={<CustomerIntelligence />} />
    <Route path="support" element={<SupportIntelligence />} />
    <Route path="assistant" element={<AIAssistant />} />
    <Route path="settings" element={<SettingsPage />} />
    <Route path="*" element={<Navigate to="/" replace />} />
  </Route></Routes></Suspense>;
}
