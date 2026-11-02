"use client";

export default function ErrorPage({ reset }: { reset: () => void }) {
  return (
    <section className="panel empty-state">
      <h1>Something went wrong.</h1>
      <p>Your documents are stored by the backend. Try reloading this view.</p>
      <button className="action-button" onClick={reset}>
        Try again
      </button>
    </section>
  );
}
