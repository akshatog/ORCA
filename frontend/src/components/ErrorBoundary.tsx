import React from "react";

interface State {
  error: Error | null;
}

interface Props {
  children: React.ReactNode;
  fallback?: React.ReactNode;
  onReset?: () => void;
}

/**
 * Catches any render-time exception in the subtree and shows a recovery UI
 * instead of leaving the screen blank. Without this, a single uncaught
 * error in any component unmounts the entire React tree silently.
 */
export class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("[ORCA ErrorBoundary] Caught render error:", error, info);
  }

  reset = () => {
    this.setState({ error: null });
    this.props.onReset?.();
  };

  render() {
    if (this.state.error) {
      if (this.props.fallback) return this.props.fallback;
      return (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            minHeight: 200,
            padding: 32,
            textAlign: "center",
            color: "var(--ink-500, #6b7280)",
            fontFamily: "var(--font-mono, monospace)",
            fontSize: 13,
          }}
        >
          <div style={{ fontSize: 28, marginBottom: 12 }}>⚓</div>
          <div style={{ fontWeight: 700, marginBottom: 6, color: "var(--ink-800, #1f2937)" }}>
            Something went wrong
          </div>
          <div style={{ marginBottom: 16, maxWidth: 420, color: "var(--ink-400, #9ca3af)", fontSize: 12 }}>
            {this.state.error.message}
          </div>
          <button
            onClick={this.reset}
            style={{
              padding: "6px 18px",
              border: "1px solid var(--rule, #d1d5db)",
              borderRadius: 2,
              background: "none",
              cursor: "pointer",
              fontSize: 12,
              letterSpacing: "0.08em",
            }}
          >
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
