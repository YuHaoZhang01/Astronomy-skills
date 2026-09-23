export type RunStatus =
  | "queued"
  | "running"
  | "cancelling"
  | "succeeded"
  | "failed"
  | "cancelled"
  | "interrupted";

export interface Engine {
  id: string;
  name: string;
  family: string;
  version: string;
  enabled: boolean;
  reason?: string;
  capabilities: string[];
  license?: string;
}

export interface Project {
  id: string;
  name: string;
  description: string;
  created_at: string;
}

export interface ProfilePair {
  id: string;
  name: string;
  structure_filename: string;
  composition_filename: string;
  sha256: string;
  source: "builtin" | "upload";
  engine_id?: string;
  size_bytes: number;
  metadata: Record<string, unknown>;
}

export interface ParameterField {
  key: string;
  label: string;
  group: string;
  type: "integer" | "number" | "string" | "enum" | "boolean";
  default: unknown;
  unit?: string;
  minimum?: number;
  maximum?: number;
  choices?: unknown[];
  description: string;
  advanced: boolean;
  sweepable: boolean;
}

export interface ParameterSchema {
  engine_id: string;
  fields: ParameterField[];
  template: string;
}

export interface Run {
  id: string;
  project_id: string;
  sweep_id?: string;
  engine_id: string;
  profile_id: string;
  name: string;
  parameters: Record<string, unknown>;
  raw_parameters?: string;
  rendered_parameters?: string;
  output_mode: "full" | "minimal";
  status: RunStatus;
  progress: number;
  current_time?: number;
  tend?: number;
  error?: string;
  run_dir: string;
  created_at: string;
  started_at?: string;
  finished_at?: string;
  engine_version?: string;
  manifest?: { artifacts?: Artifact[] };
}

export interface Series {
  id: string;
  label: string;
  kind: "luminosity" | "magnitude" | "velocity" | "temperature";
  x: number[];
  y: number[];
  x_unit: string;
  y_unit: string;
  inverted_y: boolean;
}

export interface Artifact {
  path: string;
  size_bytes: number;
  sha256?: string;
}

export interface RunPreview {
  valid: boolean;
  rendered_parameters: string;
  normalized_parameters: Record<string, unknown>;
  errors: string[];
  warnings: string[];
  engine: Engine;
  profile: ProfilePair;
}

export interface SweepPreview {
  valid: boolean;
  count: number;
  combinations: Record<string, unknown>[];
  errors: string[];
  warnings: string[];
}

export interface CompareItem {
  run: Run;
  series: Series[];
}
