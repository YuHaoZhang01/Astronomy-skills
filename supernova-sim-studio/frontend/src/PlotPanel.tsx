import { useEffect, useRef } from "react";
import Plotly from "plotly.js-basic-dist-min";
import type { CompareItem, Series } from "./types";

const COLORS = ["#40c9ff", "#ff7a90", "#ffd166", "#78e6a0", "#af8cff", "#ffad5c", "#66e0d4"];

interface Props {
  title: string;
  series?: Series[];
  comparison?: CompareItem[];
  kind: Series["kind"];
}

export function PlotPanel({ title, series = [], comparison = [], kind }: Props) {
  const element = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!element.current) return;
    const traces: unknown[] = [];
    if (comparison.length) {
      comparison.forEach((item, runIndex) => {
        item.series.filter((entry) => entry.kind === kind).forEach((entry) => {
          traces.push({
            x: entry.x,
            y: entry.y,
            type: "scatter",
            mode: "lines",
            name: `${item.run.name} · ${entry.label}`,
            line: { color: COLORS[runIndex % COLORS.length], width: 2 },
            hovertemplate: "%{x:.4g} day<br>%{y:.5g}<extra>%{fullData.name}</extra>",
          });
        });
      });
    } else {
      series.filter((entry) => entry.kind === kind).forEach((entry, index) => {
        traces.push({
          x: entry.x,
          y: entry.y,
          type: "scatter",
          mode: "lines",
          name: entry.label,
          line: { color: COLORS[index % COLORS.length], width: 2.2 },
          hovertemplate: "%{x:.4g} day<br>%{y:.5g}<extra>%{fullData.name}</extra>",
        });
      });
    }
    const inverted = kind === "magnitude";
    const unit = kind === "luminosity" ? "erg s⁻¹" : kind === "velocity" ? "km s⁻¹" : kind === "temperature" ? "K" : "mag";
    void Plotly.react(
      element.current,
      traces,
      {
        title: { text: title, font: { size: 16, color: "#e8f2ff" }, x: 0.03 },
        paper_bgcolor: "transparent",
        plot_bgcolor: "transparent",
        font: { color: "#aebed0", family: "Inter, system-ui, sans-serif" },
        margin: { l: 65, r: 20, t: 55, b: 55 },
        xaxis: { title: "爆炸后时间 [day]", gridcolor: "#253449", zerolinecolor: "#253449" },
        yaxis: {
          title: unit,
          gridcolor: "#253449",
          zerolinecolor: "#253449",
          autorange: inverted ? "reversed" : true,
          type: kind === "luminosity" ? "log" : "linear",
        },
        legend: { orientation: "h", y: -0.22 },
        hovermode: "x unified",
        autosize: true,
      },
      { responsive: true, displaylogo: false, scrollZoom: true },
    );
    return () => {
      if (element.current) Plotly.purge(element.current);
    };
  }, [comparison, kind, series, title]);

  const count = comparison.length
    ? comparison.reduce((total, item) => total + item.series.filter((entry) => entry.kind === kind).length, 0)
    : series.filter((entry) => entry.kind === kind).length;
  if (!count) return null;
  return <div ref={element} className="plot-panel" aria-label={title} />;
}
