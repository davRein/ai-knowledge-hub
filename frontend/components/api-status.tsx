"use client";

import { useEffect, useState } from "react";
import { checkHealth } from "../lib/api";

type Status = "checking" | "online" | "offline";

export function ApiStatus() {
  const [status, setStatus] = useState<Status>("checking");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    const timeout = window.setTimeout(() => controller.abort(), 5000);
    checkHealth(controller.signal)
      .then(() => {
        if (active) setStatus("online");
      })
      .catch(() => {
        if (active) setStatus("offline");
      })
      .finally(() => window.clearTimeout(timeout));
    return () => {
      active = false;
      window.clearTimeout(timeout);
      controller.abort();
    };
  }, [attempt]);

  return (
    <div className="api-status">
      <p role="status" className={`status-${status}`}>
        <span aria-hidden="true" className="status-dot" />
        {status === "checking" && "Checking API…"}
        {status === "online" && "API reachable · local demo"}
        {status === "offline" && "API unavailable · start the backend"}
      </p>
      {status === "offline" && (
        <button
          className="text-button"
          onClick={() => {
            setStatus("checking");
            setAttempt((value) => value + 1);
          }}
        >
          Retry connection
        </button>
      )}
      <p className="fine-print">
        Process health only. Database connectivity is not checked.
      </p>
    </div>
  );
}
