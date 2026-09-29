import { useCallback, useEffect, useState } from "react";

import { isAbortError } from "../api";

export type AsyncState<T> =
  | { status: "loading" }
  /** `refreshError` is set when a background refetch failed but older data is still shown. */
  | { status: "ok"; data: T; refreshError?: Error }
  | { status: "error"; error: Error };

interface Options {
  /**
   * On refetch, keep showing the previous data instead of going back to "loading",
   * and keep it if the refetch fails (the failure is reported as `refreshError`).
   */
  keepPreviousData?: boolean;
}

/**
 * Runs `fn` whenever `deps` change, aborting the previous request.
 * Returns the state plus `reload()` for retry buttons.
 */
export function useAsync<T>(
  fn: (signal: AbortSignal) => Promise<T>,
  deps: unknown[],
  options: Options = {},
): AsyncState<T> & { reload: () => void } {
  const [state, setState] = useState<AsyncState<T>>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);
  const keep = options.keepPreviousData ?? false;

  useEffect(() => {
    const controller = new AbortController();
    setState((prev) => (keep && prev.status === "ok" ? { status: "ok", data: prev.data } : { status: "loading" }));
    fn(controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) setState({ status: "ok", data });
      })
      .catch((e: unknown) => {
        if (controller.signal.aborted || isAbortError(e)) return;
        const error = e instanceof Error ? e : new Error(String(e));
        setState((prev) =>
          keep && prev.status === "ok"
            ? { status: "ok", data: prev.data, refreshError: error }
            : { status: "error", error },
        );
      });
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, attempt]);

  const reload = useCallback(() => setAttempt((a) => a + 1), []);
  return { ...state, reload };
}
