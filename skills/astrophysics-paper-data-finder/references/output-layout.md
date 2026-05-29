# 输出目录与清单格式

## 推荐目录结构

```text
<run-root>/
  request.json
  search-log.md
  references/
    references.md
    bibliography.bib
  data/
    <paper-slug>/
      original/
      working/
  manifests/
    datasets.json
  notebooks/
    review_lightcurves.ipynb
  qa/
    plot-check.md
```

## 最小要求

- `request.json`：原始请求、绝对日期范围、搜索词、假设。
- `search-log.md`：检索过哪些站点、筛掉了哪些论文、为什么筛掉。
- `references/references.md`：每篇论文的简要说明和数据入口。
- `references/bibliography.bib`：BibTeX 条目。
- `data/<paper-slug>/original/`：原始下载文件，保持原文件名和原格式。
- `data/<paper-slug>/working/`：只放解压件、清洗件或临时作图副本。
- `manifests/datasets.json`：notebook 和后续脚本使用的数据索引。
- `notebooks/`：核对 notebook。
- `qa/plot-check.md`：和原文图的核对结果。

## datasets.json 模板

```json
{
  "title": "Type Ibn supernova light curves published between 2021-03-08 and 2026-03-08",
  "created_at": "2026-03-08T12:00:00+08:00",
  "request": {
    "topic": "Type Ibn supernova",
    "data_type": "light curve",
    "target_count": 10,
    "date_start": "2021-03-08",
    "date_end": "2026-03-08"
  },
  "datasets": [
    {
      "paper_id": "2024ApJ...123..456A",
      "paper_short": "Author et al. 2024",
      "label": "Author et al. 2024 photometry",
      "path": "../data/author-2024/original/table1.ecsv",
      "source_url": "https://example.org/table1.ecsv",
      "file_format": "ecsv",
      "x_col": "mjd",
      "y_col": "mag",
      "yerr_col": "mag_err",
      "series_col": "filter",
      "panel": "Author et al. 2024",
      "invert_yaxis": true,
      "notes": "AB magnitude; nondetections removed"
    }
  ]
}
```

## 字段要求

- `path`：相对 `datasets.json` 的相对路径，或绝对路径。
- `paper_id`：优先用 ADS bibcode；没有时可用 DOI 或稳定自定义 ID。
- `label`：图例中可直接显示的短名称。
- `x_col`, `y_col`：必须显式指定，不要依赖脚本猜测。
- `yerr_col`：没有就省略。
- `series_col`：同一文件含多个波段或子样本时填写。
- `panel`：希望画到同一子图里的多条记录使用同一 panel 名。
- `invert_yaxis`：星等图通常设为 `true`。
- `notes`：记录单位、筛选条件、上限处理方式等。

## 生成 notebook

- 运行 skill 自带脚本 `scripts/make_review_notebook.py`。
- 推荐参数形式：

```text
python <skill-dir>/scripts/make_review_notebook.py --manifest <run-root>/manifests/datasets.json --output <run-root>/notebooks/review_lightcurves.ipynb
```

- 如果系统里没有 `python` 命令，改用当前环境可用的 Python 解释器，但保持脚本参数不变。
