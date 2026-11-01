import { Suspense, useEffect } from 'react';
import { BrowserRouter, useLocation, useRoutes } from 'react-router-dom';
import { ErrorBoundary } from '../components/common/ErrorBoundary';
import { Footer } from '../components/layout/Footer';
import { Navbar } from '../components/layout/Navbar';
import { PageContainer } from '../components/layout/PageContainer';
import { RoadmapProvider } from '../hooks/useRoadmap';
import { routes } from './routes';

function ScrollTop() {
  const { pathname } = useLocation();
  useEffect(() => { window.scrollTo(0, 0); }, [pathname]);
  return null;
}

function AppRoutes() {
  return (
    <Suspense fallback={<PageContainer className="py-16"><p role="status" className="text-ink-2">Loading…</p></PageContainer>}>
      {useRoutes(routes)}
    </Suspense>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <RoadmapProvider>
          <ScrollTop />
          <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-ink focus:px-4 focus:py-2 focus:text-white">Skip to content</a>
          <Navbar />
          <main id="main" className="min-h-[70vh]"><AppRoutes /></main>
          <Footer />
        </RoadmapProvider>
      </BrowserRouter>
    </ErrorBoundary>
  );
}
