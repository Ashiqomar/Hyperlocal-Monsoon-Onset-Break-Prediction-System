import { useEffect, type ReactNode } from "react";
import { isRouteErrorResponse, Link, useRouteError } from "react-router";

/**
 * Shown for unknown URLs and for crashes while loading or rendering a page.
 * Imported eagerly (not lazily) so it still works when a page chunk fails to download.
 */
export function RouteError() {
  const error = useRouteError();
  const notFound = isRouteErrorResponse(error) && error.status === 404;
  // After a redeploy, old tabs may request page chunks that no longer exist.
  const chunkFailed =
    error instanceof Error && /dynamically imported module|Loading chunk|Failed to fetch/i.test(error.message);

  useEffect(() => {
    if (!notFound) console.error(error);
  }, [error, notFound]);

  if (notFound) return <NotFound />;

  return (
    <Shell
      title="Something went wrong"
      text={
        chunkFailed
          ? "This page couldn’t be loaded. The app may have been updated, or the connection dropped."
          : "An unexpected error occurred while showing this page."
      }
    >
      <button
        onClick={() => window.location.reload()}
        className="min-h-12 rounded-xl bg-slate-900 px-5 py-2.5 text-base font-semibold text-white active:bg-slate-700"
      >
        Reload page
      </button>
    </Shell>
  );
}

export function NotFound() {
  return (
    <Shell title="Page not found" text="Check the link you were sent. Farmer advice links look like /farmer/GP014.">
      <Link to="/" className="text-sm font-medium text-sky-700 hover:underline">
        Go to the officer dashboard
      </Link>
    </Shell>
  );
}

function Shell({ title, text, children }: { title: string; text: string; children: ReactNode }) {
  return (
    <div className="flex min-h-dvh items-center justify-center bg-stone-100 px-4">
      <div className="w-full max-w-md rounded-3xl bg-white p-6 text-center shadow-sm ring-1 ring-slate-900/5">
        <h1 className="text-xl font-bold text-slate-900">{title}</h1>
        <p className="mt-2 text-slate-600">{text}</p>
        <div className="mt-5 flex flex-col items-center gap-3">{children}</div>
      </div>
    </div>
  );
}
