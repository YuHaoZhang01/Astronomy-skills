/// <reference types="vite/client" />

declare module "plotly.js-basic-dist-min" {
  const Plotly: {
    react: (element: HTMLElement, data: unknown[], layout?: unknown, config?: unknown) => Promise<void>;
    purge: (element: HTMLElement) => void;
  };
  export default Plotly;
}
