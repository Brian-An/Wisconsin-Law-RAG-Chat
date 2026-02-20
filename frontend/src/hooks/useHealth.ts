"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import type { HealthResponse } from "@/lib/types";
import { HEALTH_POLL_INTERVAL } from "@/lib/constants";

export function useHealth() {
  const [health, setHealth] = useState<HealthResponse | null>(null);

  useEffect(() => {
    let mounted = true;

    const check = async () => {
      try {
        const data = await api.health();
        if (mounted) setHealth(data);
      } catch {
        if (mounted) setHealth({ status: "degraded", collection_count: 0 });
      }
    };

    check();
    const interval = setInterval(check, HEALTH_POLL_INTERVAL);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  return health;
}
