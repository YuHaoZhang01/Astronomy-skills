import type {
  Artifact,
  CompareItem,
  Engine,
  ParameterSchema,
  ProfilePair,
  Project,
  Run,
  RunPreview,
  Series,
  SweepPreview,
} from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: init?.body instanceof FormData ? init.headers : { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    try {
      const payload = await response.json();
      message = payload.detail ?? message;
    } catch {
      // Keep the HTTP status when the server did not return JSON.
    }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

export const api = {
  engines: () => request<Engine[]>("/api/v1/engines"),
  projects: () => request<Project[]>("/api/v1/projects"),
  createProject: (payload: { name: string; description: string }) =>
    request<Project>("/api/v1/projects", { method: "POST", body: JSON.stringify(payload) }),
  profiles: () => request<ProfilePair[]>("/api/v1/profiles"),
  schema: (engine: string) => request<ParameterSchema>(`/api/v1/engines/${engine}/parameters`),
  runs: (projectId?: string) =>
    request<Run[]>(`/api/v1/runs?limit=300${projectId ? `&project_id=${encodeURIComponent(projectId)}` : ""}`),
  run: (id: string) => request<Run>(`/api/v1/runs/${id}`),
  previewRun: (payload: unknown) => request<RunPreview>("/api/v1/runs/preview", { method: "POST", body: JSON.stringify(payload) }),
  submitRun: (payload: unknown) => request<Run>("/api/v1/runs", { method: "POST", body: JSON.stringify(payload) }),
  previewSweep: (payload: unknown) => request<SweepPreview>("/api/v1/sweeps/preview", { method: "POST", body: JSON.stringify(payload) }),
  submitSweep: (payload: unknown) => request<{ sweep: unknown; runs: Run[] }>("/api/v1/sweeps", { method: "POST", body: JSON.stringify(payload) }),
  cancel: (id: string) => request<Run>(`/api/v1/runs/${id}/cancel`, { method: "POST" }),
  retry: (id: string) => request<Run>(`/api/v1/runs/${id}/retry`, { method: "POST" }),
  delete: (id: string) => request<{ deleted: boolean; recoverable_path?: string }>(`/api/v1/runs/${id}`, { method: "DELETE" }),
  logs: (id: string) => request<{ offset: number; text: string }>(`/api/v1/runs/${id}/logs`),
  series: (id: string) => request<Series[]>(`/api/v1/runs/${id}/series`),
  artifacts: (id: string) => request<Artifact[]>(`/api/v1/runs/${id}/artifacts`),
  compare: (ids: string[]) => request<CompareItem[]>(`/api/v1/compare?${ids.map((id) => `run_ids=${encodeURIComponent(id)}`).join("&")}`),
  uploadProfile: (form: FormData) => request<ProfilePair>("/api/v1/profiles", { method: "POST", body: form }),
};
