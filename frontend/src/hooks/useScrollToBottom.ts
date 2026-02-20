"use client";

import { useEffect, useRef } from "react";

export function useScrollToBottom<T extends HTMLElement>(
  deps: unknown[]
): React.RefObject<T | null> {
  const ref = useRef<T>(null);

  useEffect(() => {
    if (ref.current) {
      ref.current.scrollTo({
        top: ref.current.scrollHeight,
        behavior: "smooth",
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return ref;
}
