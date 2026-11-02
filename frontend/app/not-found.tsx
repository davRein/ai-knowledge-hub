import Link from "next/link";

export default function NotFound() {
  return (
    <section className="panel empty-state">
      <h1>Page not found.</h1>
      <p>Return to your workspace to continue.</p>
      <Link className="primary-link" href="/">
        Back to chat
      </Link>
    </section>
  );
}
