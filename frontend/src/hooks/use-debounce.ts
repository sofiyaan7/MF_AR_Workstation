import * as React from "react";

/** Delays a rapidly changing value — used to keep search feeling instant. */
export function useDebounce<T>(value: T, delay = 250): T {
  const [debounced, setDebounced] = React.useState(value);

  React.useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), delay);
    return () => window.clearTimeout(timer);
  }, [value, delay]);

  return debounced;
}
