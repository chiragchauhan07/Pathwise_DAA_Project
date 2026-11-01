import { Component, type ErrorInfo, type ReactNode } from 'react';

export class ErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  componentDidCatch(error: Error, info: ErrorInfo) { console.error('Pathwise render error', error, info.componentStack); }
  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <div role="alert" className="mx-auto max-w-xl px-6 py-24">
        <h1 className="h-page">Something went wrong</h1>
        <p className="mt-3 text-ink-2">This screen couldn’t be displayed. Reload to continue; your saved paths are kept.</p>
        <button type="button" className="btn btn-primary mt-6" onClick={() => window.location.reload()}>Reload</button>
      </div>
    );
  }
}
