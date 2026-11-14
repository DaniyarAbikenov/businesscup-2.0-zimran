import '@fontsource-variable/inter';
import '@fontsource-variable/fraunces';
import './styles/tokens.css';
import './styles/base.css';
import './styles/components.css';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import { ErrorBoundary, Toaster } from './components/Toaster';
import { installGlobalHandlers, log } from './log';

installGlobalHandlers();
log.info('app.start', 'RoleShift loaded', { ua: navigator.userAgent.slice(0, 80) });

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <ErrorBoundary><App /></ErrorBoundary>
      <Toaster />
    </BrowserRouter>
  </StrictMode>
);
