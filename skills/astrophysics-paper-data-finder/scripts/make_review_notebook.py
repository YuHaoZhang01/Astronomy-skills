#!/usr/bin/env python3
"""
Generate a Jupyter notebook that reloads downloaded astronomy datasets from a
manifest JSON file and re-plots them for paper-to-data verification.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def markdown_cell(source: str) -> dict:
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": [line + "\n" for line in source.strip().splitlines()],
    }


def code_cell(source: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [line + "\n" for line in source.strip().splitlines()],
    }


def build_notebook(manifest_path: Path) -> dict:
    manifest_literal = manifest_path.resolve().as_posix()
    title = manifest_path.stem.replace("_", " ").title()

    intro = f"""
# Review Notebook

This notebook was generated from `{manifest_literal}`.

Use it to:

1. reload the downloaded public datasets,
2. re-plot the reported light curves or tables,
3. compare the result against the source paper figures,
4. record any mismatch caused by unit choices, phase definitions, filters, or missing rows.
"""

    setup = f"""
from pathlib import Path
import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

try:
    from astropy.table import Table
except ImportError:
    Table = None

MANIFEST_PATH = Path(r"{manifest_literal}")
manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
datasets = manifest.get("datasets", [])

print(manifest.get("title", "{title}"))
print(f"datasets: {{len(datasets)}}")
"""

    helpers = """
def resolve_path(entry):
    raw = Path(entry["path"])
    if raw.is_absolute():
        return raw
    return (MANIFEST_PATH.parent / raw).resolve()


def load_dataframe(entry):
    path = resolve_path(entry)
    suffix = path.suffix.lower()

    if suffix == ".csv":
        return pd.read_csv(path, comment="#")
    if suffix in {".tsv", ".tab"}:
        return pd.read_csv(path, sep="\\t", comment="#")
    if suffix in {".txt", ".dat", ".ascii"}:
        return pd.read_csv(path, sep=None, engine="python", comment="#")
    if suffix == ".json":
        return pd.read_json(path)
    if suffix == ".ecsv":
        if Table is None:
            raise ImportError("Reading ECSV requires astropy.")
        return Table.read(path, format="ascii.ecsv").to_pandas()
    if suffix in {".fits", ".fit", ".fts"}:
        if Table is None:
            raise ImportError("Reading FITS tables requires astropy.")
        return Table.read(path).to_pandas()

    try:
        return pd.read_csv(path, sep=None, engine="python", comment="#")
    except Exception as exc:
        raise ValueError(f"Unsupported or unreadable file: {path}") from exc


def prepare_numeric(frame, columns):
    for column in columns:
        if column and column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame


def iter_groups(frame, entry):
    series_col = entry.get("series_col")
    if series_col and series_col in frame.columns:
        for series_value, group in frame.groupby(series_col):
            yield str(series_value), group
        return
    yield entry.get("label", "dataset"), frame
"""

    plotting = """
if not datasets:
    raise ValueError("No datasets found in manifest.")

panel_names = []
panel_to_entries = {}
for entry in datasets:
    panel = entry.get("panel") or entry.get("paper_short") or entry.get("label") or "Panel"
    if panel not in panel_to_entries:
        panel_names.append(panel)
        panel_to_entries[panel] = []
    panel_to_entries[panel].append(entry)

fig, axes = plt.subplots(
    len(panel_names),
    1,
    figsize=(10, max(4, 4 * len(panel_names))),
    squeeze=False,
    constrained_layout=True,
)

summary_rows = []

for axis, panel in zip(axes.flatten(), panel_names):
    plotted_anything = False
    for entry in panel_to_entries[panel]:
        frame = load_dataframe(entry).copy()
        frame.columns = [str(col) for col in frame.columns]

        x_col = entry["x_col"]
        y_col = entry["y_col"]
        yerr_col = entry.get("yerr_col")

        missing = [col for col in [x_col, y_col, yerr_col] if col and col not in frame.columns]
        if missing:
            raise KeyError(f"{entry.get('label', panel)} missing columns: {missing}")

        frame = prepare_numeric(frame, [x_col, y_col, yerr_col])
        frame = frame.dropna(subset=[x_col, y_col]).sort_values(x_col)

        for group_name, group in iter_groups(frame, entry):
            legend_label = group_name if entry.get("series_col") else entry.get("label", group_name)
            if yerr_col and yerr_col in group.columns:
                axis.errorbar(
                    group[x_col],
                    group[y_col],
                    yerr=group[yerr_col],
                    fmt="o",
                    ms=3,
                    capsize=2,
                    linestyle="none",
                    label=legend_label,
                )
            else:
                axis.plot(group[x_col], group[y_col], "o", ms=3, label=legend_label)
            plotted_anything = True

        summary_rows.append(
            {
                "panel": panel,
                "label": entry.get("label", panel),
                "rows": len(frame),
                "path": str(resolve_path(entry)),
            }
        )

    axis.set_title(panel)
    first_entry = panel_to_entries[panel][0]
    axis.set_xlabel(first_entry.get("x_label", first_entry["x_col"]))
    axis.set_ylabel(first_entry.get("y_label", first_entry["y_col"]))
    axis.grid(alpha=0.25)
    if first_entry.get("invert_yaxis"):
        axis.invert_yaxis()
    if plotted_anything:
        axis.legend(loc="best", fontsize=8)

plt.show()
pd.DataFrame(summary_rows)
"""

    notes = """
# Fill in after visual comparison

comparison_notes = {
    "matched_panels": [],
    "mismatched_panels": [],
    "open_questions": [],
}

comparison_notes
"""

    return {
        "cells": [
            markdown_cell(intro),
            code_cell(setup),
            code_cell(helpers),
            code_cell(plotting),
            code_cell(notes),
        ],
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "version": "3.x",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a Jupyter review notebook from a datasets manifest."
    )
    parser.add_argument(
        "--manifest",
        required=True,
        help="Path to manifests/datasets.json",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to the output .ipynb file",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest_path = Path(args.manifest)
    output_path = Path(args.output)

    notebook = build_notebook(manifest_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(notebook, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
