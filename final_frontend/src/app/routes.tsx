import { lazy } from 'react';
import { Link, Navigate, type RouteObject } from 'react-router-dom';

const HomePage = lazy(() => import('../pages/HomePage'));
const DAAPage = lazy(() => import('../pages/DAAPage'));
const AIPage = lazy(() => import('../pages/AIPage'));

export const routes: RouteObject[] = [
  { path: '/', element: <HomePage /> },
  { path: '/daa', element: <DAAPage /> },
  { path: '/daa-concepts', element: <Navigate to="/daa" replace /> },
  { path: '/ai', element: <AIPage /> },
  { path: '/ai-concepts', element: <Navigate to="/ai" replace /> },
  { path: '/roadmaps', element: <Navigate to="/" replace /> },
  { path: '/about', element: <Navigate to="/ai" replace /> },
  { path: '*', element: <NotFound /> },
];

function NotFound() {
  return (
    <div className="mx-auto max-w-xl px-6 py-24">
      <h1 className="h-page">Page not found</h1>
      <p className="mt-3 text-ink-2">That page doesn’t exist.</p>
      <Link to="/" className="btn btn-primary mt-6">Back to the planner</Link>
    </div>
  );
}
