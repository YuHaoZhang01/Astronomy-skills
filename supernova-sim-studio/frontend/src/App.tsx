import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "./api";
import { PlotPanel } from "./PlotPanel";
import type {
  Artifact,
  CompareItem,
  Engine,
  ParameterField,
  ParameterSchema,
  ProfilePair,
  Project,
  Run,
  RunPreview,
  Series,
  SweepPreview,
} from "./types";

type Page = "projects" | "compose" | "runs" | "profiles" | "compare";
type Mode = "run" | "sweep";

const PAGE_TITLE: Record<Page, string> = {
  projects: "科研项目",
  compose: "开始一次新的爆炸模拟",
  runs: "任务与运行状态",
  profiles: "恒星模型库",
  compare: "运行结果对比",
};

const STATUS_LABEL: Record<Run["status"], string> = {
  queued: "排队中",
  running: "运行中",
  cancelling: "取消中",
  succeeded: "已完成",
  failed: "失败",
  cancelled: "已取消",
  interrupted: "已中断",
};

const TERMINAL = new Set(["succeeded", "failed", "cancelled", "interrupted"]);

function formatBytes(value: number): string {
  if (value < 1024) return `${value} B`;
  if (value < 1024 ** 2) return `${(value / 1024).toFixed(1)} KiB`;
  if (value < 1024 ** 3) return `${(value / 1024 ** 2).toFixed(1)} MiB`;
  return `${(value / 1024 ** 3).toFixed(2)} GiB`;
}

function shortTime(value?: string): string {
  return value ? new Intl.DateTimeFormat("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit" }).format(new Date(value)) : "—";
}

function simulationTime(run: Run): string {
  if (run.current_time === undefined || run.current_time === null) return "等待时间步";
  const days = run.engine_id === "stella" ? run.current_time : run.current_time / 86400;
  return `${days.toFixed(2)} day`;
}

function errorText(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

export function App() {
  const [page, setPage] = useState<Page>("compose");
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState(
    () => window.localStorage.getItem("snstudio.activeProject") ?? "default",
  );
  const [engines, setEngines] = useState<Engine[]>([]);
  const [profiles, setProfiles] = useState<ProfilePair[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [error, setError] = useState("");

  const refreshCatalog = useCallback(async () => {
    try {
      const [nextEngines, nextProfiles, nextProjects] = await Promise.all([
        api.engines(),
        api.profiles(),
        api.projects(),
      ]);
      setEngines(nextEngines);
      setProfiles(nextProfiles);
      setProjects(nextProjects);
      setProjectId((current) => {
        const next = nextProjects.some((project) => project.id === current)
          ? current
          : (nextProjects[0]?.id ?? "default");
        window.localStorage.setItem("snstudio.activeProject", next);
        return next;
      });
    } catch (reason) {
      setError(errorText(reason));
    }
  }, []);

  const refreshRuns = useCallback(async () => {
    try {
      setRuns(await api.runs(projectId));
    } catch (reason) {
      setError(errorText(reason));
    }
  }, [projectId]);

  useEffect(() => {
    void refreshCatalog();
    void refreshRuns();
    const timer = window.setInterval(refreshRuns, 1600);
    return () => window.clearInterval(timer);
  }, [refreshCatalog, refreshRuns]);

  const active = runs.filter((run) => ["queued", "running", "cancelling"].includes(run.status)).length;
  const completed = runs.filter((run) => run.status === "succeeded").length;
  const activeProject = projects.find((project) => project.id === projectId);

  function selectProject(id: string) {
    window.localStorage.setItem("snstudio.activeProject", id);
    setProjectId(id);
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">SN</div>
          <div>
            <strong>超新星模拟台</strong>
            <span>Simulation Studio</span>
          </div>
        </div>
        <nav>
          <NavButton active={page === "projects"} onClick={() => setPage("projects")} icon="◇" label="科研项目" />
          <NavButton active={page === "compose"} onClick={() => setPage("compose")} icon="✦" label="新建计算" />
          <NavButton active={page === "runs"} onClick={() => setPage("runs")} icon="≋" label="任务队列" badge={active || undefined} />
          <NavButton active={page === "profiles"} onClick={() => setPage("profiles")} icon="◎" label="恒星模型" />
          <NavButton active={page === "compare"} onClick={() => setPage("compare")} icon="⌁" label="结果对比" />
        </nav>
        <div className="engine-list">
          <p className="eyebrow">计算引擎</p>
          {engines.map((engine) => (
            <div className="engine-row" key={engine.id} title={engine.reason}>
              <i className={engine.enabled ? "health-dot ok" : "health-dot"} />
              <span>{engine.name}</span>
              <small>{engine.enabled ? engine.version.slice(0, 10) : "未配置"}</small>
            </div>
          ))}
        </div>
        <div className="sidebar-foot">
          <span>本机优先 · Tailscale 就绪</span>
          <code>v0.1.0</code>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div>
            <p className="eyebrow">NON-COMMERCIAL RESEARCH WORKBENCH</p>
            <h1>{PAGE_TITLE[page]}</h1>
          </div>
          <div className="summary-pills">
            <span className="project-pill">{activeProject?.name ?? "默认项目"}</span>
            <span><b>{active}</b> 活跃</span>
            <span><b>{completed}</b> 完成</span>
          </div>
        </header>

        {error && <div className="alert error"><span>{error}</span><button onClick={() => setError("")}>×</button></div>}

        {page === "projects" && (
          <ProjectsPage
            projects={projects}
            activeId={projectId}
            refresh={refreshCatalog}
            select={(id) => {
              selectProject(id);
              setPage("compose");
            }}
          />
        )}
        {page === "compose" && (
          <Composer
            projectId={projectId}
            engines={engines}
            profiles={profiles}
            onSubmitted={() => {
              void refreshRuns();
              setPage("runs");
            }}
          />
        )}
        {page === "runs" && <RunsPage runs={runs} refresh={refreshRuns} />}
        {page === "profiles" && <ProfilesPage profiles={profiles} refresh={refreshCatalog} />}
        {page === "compare" && <ComparePage runs={runs} />}
      </main>
    </div>
  );
}

function NavButton({ active, onClick, icon, label, badge }: { active: boolean; onClick: () => void; icon: string; label: string; badge?: number }) {
  return (
    <button className={`nav-button ${active ? "active" : ""}`} onClick={onClick}>
      <span className="nav-icon">{icon}</span><span>{label}</span>{badge ? <b>{badge}</b> : null}
    </button>
  );
}

interface ComposerProps {
  projectId: string;
  engines: Engine[];
  profiles: ProfilePair[];
  onSubmitted: () => void;
}

interface AxisRow {
  key: string;
  kind: "list" | "linear" | "log";
  values: string;
  start: string;
  stop: string;
  steps: string;
}

function Composer({ projectId, engines, profiles, onSubmitted }: ComposerProps) {
  const [mode, setMode] = useState<Mode>("run");
  const [engineId, setEngineId] = useState("supersnec");
  const [profileId, setProfileId] = useState("builtin:supersnec:stripped_star");
  const [name, setName] = useState("SuperSNEC 探索运行");
  const [outputMode, setOutputMode] = useState<"full" | "minimal">("full");
  const [schema, setSchema] = useState<ParameterSchema | null>(null);
  const [parameters, setParameters] = useState<Record<string, unknown>>({});
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [rawMode, setRawMode] = useState(false);
  const [rawText, setRawText] = useState("");
  const [runPreview, setRunPreview] = useState<RunPreview | null>(null);
  const [sweepPreview, setSweepPreview] = useState<SweepPreview | null>(null);
  const [axes, setAxes] = useState<AxisRow[]>([{ key: "Ni_mass", kind: "list", values: "0.03, 0.05, 0.08", start: "", stop: "", steps: "3" }]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const selectedEngine = engines.find((engine) => engine.id === engineId);

  useEffect(() => {
    void api.schema(engineId).then((next) => {
      setSchema(next);
      setParameters(Object.fromEntries(next.fields.map((field) => [field.key, field.default])));
      setRawText(next.template);
      setRunPreview(null);
      setSweepPreview(null);
    }).catch((reason) => setError(errorText(reason)));
    const preferred = profiles.find((profile) => profile.id.startsWith(`builtin:${engineId}:`));
    if (preferred) setProfileId(preferred.id);
  }, [engineId, profiles]);

  const visibleFields = schema?.fields.filter((field) => showAdvanced || !field.advanced) ?? [];
  const groups = useMemo(() => {
    const grouped = new Map<string, ParameterField[]>();
    visibleFields.forEach((field) => grouped.set(field.group, [...(grouped.get(field.group) ?? []), field]));
    return [...grouped.entries()];
  }, [visibleFields]);
  const sweepable = schema?.fields.filter((field) => field.sweepable && ["number", "integer"].includes(field.type)) ?? [];

  const resetPreview = () => {
    setRunPreview(null);
    setSweepPreview(null);
  };
  const basePayload = {
    project_id: projectId,
    engine_id: engineId,
    profile_id: profileId,
    name,
    parameters,
    raw_parameters: rawMode ? rawText : null,
    output_mode: mode === "sweep" ? "minimal" : outputMode,
  };

  const buildAxes = () => Object.fromEntries(axes.map((axis) => {
    const field = schema?.fields.find((item) => item.key === axis.key);
    const numeric = field && ["number", "integer"].includes(field.type);
    if (axis.kind === "list") {
      const values = axis.values.split(",").map((item) => item.trim()).filter(Boolean).map((item) => numeric ? Number(item) : item);
      return [axis.key, { kind: "list", values }];
    }
    return [axis.key, { kind: axis.kind, start: Number(axis.start), stop: Number(axis.stop), steps: Number(axis.steps) }];
  }));

  async function preview() {
    setBusy(true); setError("");
    try {
      if (mode === "run") {
        setRunPreview(await api.previewRun(basePayload));
      } else {
        const { parameters: base_parameters, ...rest } = basePayload;
        setSweepPreview(await api.previewSweep({ ...rest, base_parameters, axes: buildAxes(), output_mode: "minimal" }));
      }
    } catch (reason) { setError(errorText(reason)); }
    finally { setBusy(false); }
  }

  async function submit() {
    const valid = mode === "run" ? runPreview?.valid : sweepPreview?.valid;
    if (!valid) return;
    const count = mode === "run" ? 1 : sweepPreview?.count ?? 0;
    if (!window.confirm(`确认提交 ${count} 个计算任务？`)) return;
    setBusy(true); setError("");
    try {
      if (mode === "run") await api.submitRun(basePayload);
      else {
        const { parameters: base_parameters, ...rest } = basePayload;
        await api.submitSweep({ ...rest, base_parameters, axes: buildAxes(), output_mode: "minimal" });
      }
      onSubmitted();
    } catch (reason) { setError(errorText(reason)); }
    finally { setBusy(false); }
  }

  function updateAxis(index: number, changes: Partial<AxisRow>) {
    setAxes((current) => current.map((axis, axisIndex) => axisIndex === index ? { ...axis, ...changes } : axis));
    resetPreview();
  }

  return (
    <div className="composer-layout">
      <section className="card composer-main">
        <div className="segmented">
          <button className={mode === "run" ? "active" : ""} onClick={() => { setMode("run"); setOutputMode("full"); resetPreview(); }}>单次运行</button>
          <button className={mode === "sweep" ? "active" : ""} onClick={() => { setMode("sweep"); setOutputMode("minimal"); resetPreview(); }}>参数扫描</button>
        </div>
        {error && <div className="alert error">{error}</div>}
        <div className="form-grid primary-fields">
          <label>任务名称<input value={name} onChange={(event) => { setName(event.target.value); resetPreview(); }} /></label>
          <label>计算引擎
            <select value={engineId} onChange={(event) => setEngineId(event.target.value)}>
              {engines.map((engine) => <option key={engine.id} value={engine.id} disabled={!engine.enabled}>{engine.name}{engine.enabled ? "" : " · 未配置"}</option>)}
            </select>
          </label>
          <label>恒星模型
            <select value={profileId} onChange={(event) => { setProfileId(event.target.value); resetPreview(); }}>
              {profiles.filter((profile) => !profile.engine_id || profile.engine_id === engineId).map((profile) => <option key={profile.id} value={profile.id}>{profile.name} · {profile.source === "builtin" ? "内置" : "上传"}</option>)}
            </select>
          </label>
          <label>输出策略
            <select value={mode === "sweep" ? "minimal" : outputMode} disabled={mode === "sweep"} onChange={(event) => { setOutputMode(event.target.value as "full" | "minimal"); resetPreview(); }}>
              <option value="full">Full · 完整剖面</option><option value="minimal">Minimal · 拟合标量</option>
            </select>
          </label>
        </div>

        {mode === "sweep" && (
          <div className="sweep-builder">
            <div className="section-heading"><div><p className="eyebrow">CARTESIAN GRID</p><h2>扫描维度</h2></div><button className="ghost" onClick={() => setAxes((current) => [...current, { key: sweepable[0]?.key ?? "Ni_mass", kind: "list", values: "", start: "", stop: "", steps: "3" }])}>＋ 添加维度</button></div>
            {axes.map((axis, index) => (
              <div className="axis-row" key={`${index}-${axis.key}`}>
                <select value={axis.key} onChange={(event) => updateAxis(index, { key: event.target.value })}>{sweepable.map((field) => <option key={field.key} value={field.key}>{field.key}</option>)}</select>
                <select value={axis.kind} onChange={(event) => updateAxis(index, { kind: event.target.value as AxisRow["kind"] })}><option value="list">显式列表</option><option value="linear">线性范围</option><option value="log">对数范围</option></select>
                {axis.kind === "list" ? <input className="axis-values" placeholder="0.03, 0.05, 0.08" value={axis.values} onChange={(event) => updateAxis(index, { values: event.target.value })} /> : <><input placeholder="start" value={axis.start} onChange={(event) => updateAxis(index, { start: event.target.value })} /><input placeholder="stop" value={axis.stop} onChange={(event) => updateAxis(index, { stop: event.target.value })} /><input placeholder="steps" value={axis.steps} onChange={(event) => updateAxis(index, { steps: event.target.value })} /></>}
                <button className="icon-button danger" disabled={axes.length === 1} onClick={() => { setAxes((current) => current.filter((_, axisIndex) => axisIndex !== index)); resetPreview(); }}>×</button>
              </div>
            ))}
          </div>
        )}

        <div className="section-heading parameter-heading">
          <div><p className="eyebrow">PHYSICAL PARAMETERS</p><h2>模型参数</h2></div>
          <div className="toggle-row"><label className="switch-label"><input type="checkbox" checked={showAdvanced} onChange={(event) => setShowAdvanced(event.target.checked)} />高级参数</label><label className="switch-label"><input type="checkbox" checked={rawMode} onChange={(event) => { setRawMode(event.target.checked); resetPreview(); }} />原始文件</label></div>
        </div>
        {rawMode ? (
          <textarea className="raw-editor" spellCheck={false} value={rawText} onChange={(event) => { setRawText(event.target.value); resetPreview(); }} />
        ) : (
          <div className="parameter-groups">
            {groups.map(([group, fields], index) => (
              <details key={group} open={index < 3}>
                <summary><span>{group}</span><small>{fields.length} fields</small></summary>
                <div className="form-grid parameter-grid">
                  {fields.map((field) => <ParameterInput key={field.key} field={field} value={parameters[field.key]} onChange={(value) => { setParameters((current) => ({ ...current, [field.key]: value })); resetPreview(); }} />)}
                </div>
              </details>
            ))}
          </div>
        )}
      </section>

      <aside className="composer-aside">
        <section className="card action-card">
          <p className="eyebrow">PRE-FLIGHT</p><h2>提交前检查</h2>
          <ul className="check-list"><li className="ok">独立运行目录</li><li className="ok">参数与模型快照</li><li className="ok">完成标志 + 产物校验</li><li className="ok">浏览器关闭后继续</li></ul>
          <button className="primary wide" disabled={busy || !schema} onClick={() => void preview()}>{busy ? "正在检查…" : mode === "run" ? "预览参数" : "预览扫描"}</button>
          <button className="secondary wide" disabled={busy || !(mode === "run" ? runPreview?.valid : sweepPreview?.valid)} onClick={() => void submit()}>确认并提交</button>
        </section>
        {(runPreview || sweepPreview) && <PreviewCard run={runPreview} sweep={sweepPreview} />}
        <section className="card note-card"><p className="eyebrow">LICENSE</p><p>每次运行都会记录引擎版本与输入校验和；请遵守所选求解器的许可与引用要求。</p><span>{selectedEngine?.license ?? "请查阅引擎许可"}</span></section>
      </aside>
    </div>
  );
}

function ProjectsPage({
  projects,
  activeId,
  refresh,
  select,
}: {
  projects: Project[];
  activeId: string;
  refresh: () => Promise<void>;
  select: (id: string) => void;
}) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function create() {
    if (!name.trim()) return;
    setBusy(true);
    setMessage("");
    try {
      const project = await api.createProject({ name: name.trim(), description: description.trim() });
      await refresh();
      select(project.id);
    } catch (reason) {
      setMessage(errorText(reason));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="projects-layout">
      <section className="card project-create">
        <p className="eyebrow">NEW PROJECT</p>
        <h2>建立独立研究项目</h2>
        <p>项目用于隔离任务列表与对比范围；模型库仍可跨项目复用。</p>
        <label>项目名称<input value={name} maxLength={120} onChange={(event) => setName(event.target.value)} placeholder="例如 SN 2026abc" /></label>
        <label>研究备注<textarea value={description} maxLength={1000} onChange={(event) => setDescription(event.target.value)} placeholder="目标、假设或数据来源" /></label>
        <button className="primary wide" disabled={busy || !name.trim()} onClick={() => void create()}>{busy ? "正在创建…" : "创建并进入"}</button>
        {message && <div className="alert error">{message}</div>}
      </section>
      <section className="card project-library">
        <div className="section-heading"><div><p className="eyebrow">PROJECT LIBRARY</p><h2>{projects.length} 个项目</h2></div></div>
        <div className="project-grid">
          {projects.map((project) => (
            <article className={project.id === activeId ? "active" : ""} key={project.id}>
              <div><span>{project.id === activeId ? "当前项目" : "研究项目"}</span><h3>{project.name}</h3><p>{project.description || "尚未填写项目备注。"}</p></div>
              <footer><code>{project.id.slice(0, 12)}</code><small>{shortTime(project.created_at)}</small><button className="secondary" onClick={() => select(project.id)}>{project.id === activeId ? "继续计算" : "进入项目"}</button></footer>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}

function ParameterInput({ field, value, onChange }: { field: ParameterField; value: unknown; onChange: (value: unknown) => void }) {
  return (
    <label className="parameter-field" title={field.description}>
      <span>{field.label}<code>{field.key}</code></span>
      <div className="input-with-unit">
        {field.type === "boolean" ? <input type="checkbox" checked={Boolean(value)} onChange={(event) => onChange(event.target.checked)} /> : field.choices ? <select value={String(value)} onChange={(event) => onChange(event.target.value)}>{field.choices.map((choice) => <option key={String(choice)} value={String(choice)}>{String(choice)}</option>)}</select> : <input type={field.type === "string" ? "text" : "number"} value={String(value ?? "")} min={field.minimum} max={field.maximum} step="any" onChange={(event) => onChange(event.target.value)} />}
        {field.unit && <em>{field.unit}</em>}
      </div>
    </label>
  );
}

function PreviewCard({ run, sweep }: { run: RunPreview | null; sweep: SweepPreview | null }) {
  const valid = run?.valid ?? sweep?.valid ?? false;
  const errors = run?.errors ?? sweep?.errors ?? [];
  const warnings = run?.warnings ?? sweep?.warnings ?? [];
  return (
    <section className={`card preview-card ${valid ? "valid" : "invalid"}`}>
      <p className="eyebrow">VALIDATION</p><h2>{valid ? "检查通过" : "需要修改"}</h2>
      {sweep && <div className="preview-count"><b>{sweep.count}</b><span>个独立任务</span></div>}
      {errors.map((item) => <p className="message error-text" key={item}>× {item}</p>)}
      {warnings.map((item) => <p className="message warning-text" key={item}>! {item}</p>)}
      {run?.valid && <details><summary>查看渲染后的 parameters</summary><pre>{run.rendered_parameters}</pre></details>}
      {sweep?.valid && <details><summary>查看前 {sweep.combinations.length} 个组合</summary><pre>{JSON.stringify(sweep.combinations, null, 2)}</pre></details>}
    </section>
  );
}

function RunsPage({ runs, refresh }: { runs: Run[]; refresh: () => Promise<void> }) {
  const [selectedId, setSelectedId] = useState<string | null>(runs[0]?.id ?? null);
  const selected = runs.find((run) => run.id === selectedId) ?? null;
  const [filter, setFilter] = useState("all");
  const shown = filter === "all" ? runs : runs.filter((run) => run.status === filter);

  async function action(kind: "cancel" | "retry" | "delete", run: Run) {
    if ((kind === "cancel" || kind === "delete") && !window.confirm(`${kind === "cancel" ? "取消" : "移入回收目录"}任务“${run.name}”？`)) return;
    if (kind === "cancel") await api.cancel(run.id);
    if (kind === "retry") await api.retry(run.id);
    if (kind === "delete") { await api.delete(run.id); if (selectedId === run.id) setSelectedId(null); }
    await refresh();
  }

  return (
    <div className="runs-layout">
      <section className="card runs-table-card">
        <div className="section-heading"><div><p className="eyebrow">PERSISTENT QUEUE</p><h2>任务队列</h2></div><select value={filter} onChange={(event) => setFilter(event.target.value)}><option value="all">全部状态</option>{Object.entries(STATUS_LABEL).map(([key, label]) => <option value={key} key={key}>{label}</option>)}</select></div>
        <div className="table-wrap"><table><thead><tr><th>任务</th><th>引擎</th><th>状态</th><th>进度</th><th>创建时间</th><th /></tr></thead><tbody>
          {shown.map((run) => <tr key={run.id} className={selectedId === run.id ? "selected" : ""} onClick={() => setSelectedId(run.id)}><td><strong>{run.name}</strong><small>{run.id.slice(0, 10)}</small></td><td><code>{run.engine_id}</code></td><td><span className={`status ${run.status}`}>{STATUS_LABEL[run.status]}</span></td><td><div className="progress"><i style={{ width: `${Math.max(run.progress * 100, run.status === "running" ? 2 : 0)}%` }} /></div><small>{Math.round(run.progress * 100)}%</small></td><td>{shortTime(run.created_at)}</td><td><div className="row-actions">{["queued", "running"].includes(run.status) && <button onClick={(event) => { event.stopPropagation(); void action("cancel", run); }}>取消</button>}{TERMINAL.has(run.status) && <button onClick={(event) => { event.stopPropagation(); void action("retry", run); }}>重试</button>}{TERMINAL.has(run.status) && <button className="danger" onClick={(event) => { event.stopPropagation(); void action("delete", run); }}>删除</button>}</div></td></tr>)}
          {!shown.length && <tr><td colSpan={6} className="empty">还没有符合条件的任务</td></tr>}
        </tbody></table></div>
      </section>
      {selected && <RunDetail run={selected} />}
    </div>
  );
}

function RunDetail({ run }: { run: Run }) {
  const [logs, setLogs] = useState("");
  const [series, setSeries] = useState<Series[]>([]);
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [tab, setTab] = useState<"plots" | "logs" | "files" | "params">("plots");

  useEffect(() => {
    setLogs(""); setSeries([]); setArtifacts([]);
    void api.logs(run.id).then((value) => setLogs(value.text));
    const loadResults = () => Promise.all([api.series(run.id), api.artifacts(run.id)]).then(([nextSeries, nextArtifacts]) => { setSeries(nextSeries); setArtifacts(nextArtifacts); });
    if (TERMINAL.has(run.status)) void loadResults();
    const stream = new EventSource(`/api/v1/runs/${run.id}/events`);
    stream.onmessage = (event) => {
      const payload = JSON.parse(event.data) as { log: string; run: Run };
      if (payload.log) setLogs((current) => current + payload.log);
      if (TERMINAL.has(payload.run.status)) { stream.close(); void loadResults(); }
    };
    stream.onerror = () => stream.close();
    return () => stream.close();
  }, [run.id]);

  return (
    <section className="card run-detail">
      <div className="detail-head"><div><p className="eyebrow">RUN DETAIL</p><h2>{run.name}</h2><span className={`status ${run.status}`}>{STATUS_LABEL[run.status]}</span></div><div className="metric"><b>{Math.round(run.progress * 100)}%</b><span>{simulationTime(run)}</span></div></div>
      {run.error && <div className="alert error">{run.error}</div>}
      <div className="tabbar"><button className={tab === "plots" ? "active" : ""} onClick={() => setTab("plots")}>结果曲线</button><button className={tab === "logs" ? "active" : ""} onClick={() => setTab("logs")}>实时日志</button><button className={tab === "files" ? "active" : ""} onClick={() => setTab("files")}>产物文件</button><button className={tab === "params" ? "active" : ""} onClick={() => setTab("params")}>参数快照</button></div>
      {tab === "plots" && <div className="plots-grid">{series.length ? <><PlotPanel title="Bolometric luminosity" kind="luminosity" series={series} /><PlotPanel title="Synthetic magnitudes" kind="magnitude" series={series} /><PlotPanel title="Photospheric velocity" kind="velocity" series={series} /><PlotPanel title="Effective temperature" kind="temperature" series={series} /></> : <div className="empty large">计算完成后在这里显示交互曲线</div>}</div>}
      {tab === "logs" && <pre className="log-view">{logs || "等待运行器输出…"}</pre>}
      {tab === "files" && <div className="artifact-list">{artifacts.map((artifact) => <a key={artifact.path} href={`/api/v1/runs/${run.id}/artifacts/${artifact.path}`}><span>{artifact.path}</span><small>{formatBytes(artifact.size_bytes)}</small></a>)}{!artifacts.length && <div className="empty">暂无已索引产物</div>}</div>}
      {tab === "params" && <pre className="parameter-snapshot">{run.rendered_parameters || JSON.stringify(run.parameters, null, 2)}</pre>}
    </section>
  );
}

function ProfilesPage({ profiles, refresh }: { profiles: ProfilePair[]; refresh: () => Promise<void> }) {
  const [name, setName] = useState("");
  const [structure, setStructure] = useState<File | null>(null);
  const [composition, setComposition] = useState<File | null>(null);
  const [message, setMessage] = useState("");
  async function upload() {
    if (!structure || !composition || !name) return;
    const form = new FormData(); form.set("name", name); form.set("structure", structure); form.set("composition", composition);
    try { const saved = await api.uploadProfile(form); setMessage(`已导入 ${saved.name}`); setName(""); setStructure(null); setComposition(null); await refresh(); }
    catch (reason) { setMessage(errorText(reason)); }
  }
  return (
    <div className="profiles-layout">
      <section className="card upload-card"><p className="eyebrow">IMPORT MODEL</p><h2>上传匹配的模型文件</h2><p>结构文件使用 <code>.short</code>，组分文件使用 <code>.iso.dat</code>。服务端会校验文件名、大小和数据行数。</p><label>模型名称<input value={name} onChange={(event) => setName(event.target.value)} placeholder="例如 r17 compact" /></label><label className="file-drop">结构模型<input type="file" accept=".short" onChange={(event) => setStructure(event.target.files?.[0] ?? null)} /><span>{structure?.name ?? "选择 .short"}</span></label><label className="file-drop">组分模型<input type="file" accept=".dat" onChange={(event) => setComposition(event.target.files?.[0] ?? null)} /><span>{composition?.name ?? "选择 .iso.dat"}</span></label><button className="primary wide" disabled={!name || !structure || !composition} onClick={() => void upload()}>导入模型</button>{message && <div className="alert">{message}</div>}</section>
      <section className="card library-card"><div className="section-heading"><div><p className="eyebrow">PROFILE LIBRARY</p><h2>{profiles.length} 个可用模型</h2></div></div><div className="profile-grid">{profiles.map((profile) => <article key={profile.id}><div className="profile-icon">ρ</div><div><h3>{profile.name}</h3><p>{profile.structure_filename}</p><p>{profile.composition_filename}</p></div><div className="profile-meta"><span>{profile.source === "builtin" ? "内置" : "上传"}</span><small>{formatBytes(profile.size_bytes)}</small><code>{profile.sha256.slice(0, 9)}</code></div></article>)}</div></section>
    </div>
  );
}

function ComparePage({ runs }: { runs: Run[] }) {
  const completed = runs.filter((run) => run.status === "succeeded");
  const [selected, setSelected] = useState<string[]>([]);
  const [items, setItems] = useState<CompareItem[]>([]);
  const [error, setError] = useState("");
  async function load() { try { setItems(await api.compare(selected)); setError(""); } catch (reason) { setError(errorText(reason)); } }
  return (
    <div className="compare-layout"><section className="card compare-picker"><p className="eyebrow">OVERLAY RUNS</p><h2>选择 2–6 个运行</h2><div className="compare-options">{completed.map((run) => <label key={run.id}><input type="checkbox" checked={selected.includes(run.id)} disabled={!selected.includes(run.id) && selected.length >= 6} onChange={(event) => setSelected((current) => event.target.checked ? [...current, run.id] : current.filter((id) => id !== run.id))} /><span><strong>{run.name}</strong><small>{run.engine_id} · {shortTime(run.finished_at)}</small></span></label>)}</div>{!completed.length && <div className="empty">暂无成功运行</div>}<button className="primary wide" disabled={selected.length < 2} onClick={() => void load()}>加载对比</button>{error && <div className="alert error">{error}</div>}</section><section className="card compare-plots">{items.length ? <div className="plots-grid"><PlotPanel title="Bolometric luminosity comparison" kind="luminosity" comparison={items} /><PlotPanel title="Magnitude comparison" kind="magnitude" comparison={items} /><PlotPanel title="Velocity comparison" kind="velocity" comparison={items} /><PlotPanel title="Temperature comparison" kind="temperature" comparison={items} /></div> : <div className="empty large">选择运行后叠加比较光变、速度和温度</div>}</section></div>
  );
}
