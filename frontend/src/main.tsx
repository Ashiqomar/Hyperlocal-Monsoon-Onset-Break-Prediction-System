import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router";

import { NotFound, RouteError } from "./pages/RouteError";
import "./index.css";

// Each route is its own chunk: the farmer screen, opened on basic phones, must
// not download Leaflet and the officer dashboard.
const router = createBrowserRouter([
  {
    errorElement: <RouteError />,
    children: [
      { path: "/", lazy: async () => ({ Component: (await import("./App")).default }) },
      { path: "/farmer/:panchayatId", lazy: async () => ({ Component: (await import("./pages/FarmerPage")).default }) },
      {
        path: "/admin/feedback",
        lazy: async () => ({ Component: (await import("./pages/AdminFeedbackPage")).default }),
      },
      { path: "*", element: <NotFound /> },
    ],
  },
]);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
);
