from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from typing import Any

import httpx
import typer

from .config import get_settings
from .database import get_database
from .engines import EngineRegistry

studio_app = typer.Typer(help="超新星模拟台本机与部署管理")
ctl_app = typer.Typer(help="SNEC/STELLA 任务控制 CLI", no_args_is_help=True)
run_app = typer.Typer(help="单次任务")
sweep_app = typer.Typer(help="参数扫描")
profiles_app = typer.Typer(help="恒星模型")
ctl_app.add_typer(run_app, name="run")
ctl_app.add_typer(sweep_app, name="sweep")
ctl_app.add_typer(profiles_app, name="profiles")


class ClientContext:
    def __init__(self, url: str, json_output: bool):
        self.url = url.rstrip("/")
        self.json_output = json_output

    def request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            response = httpx.request(method, self.url + path, timeout=60, **kwargs)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text
            try:
                detail = exc.response.json().get("detail", detail)
            except (ValueError, AttributeError):
                pass
            typer.echo(f"API 错误：{detail}", err=True)
            raise typer.Exit(1) from exc
        except httpx.HTTPError as exc:
            typer.echo(f"无法连接 {self.url}：{exc}", err=True)
            raise typer.Exit(1) from exc
        if not response.content:
            return None
        return response.json()

    def emit(self, value: Any) -> None:
        if self.json_output:
            typer.echo(json.dumps(value, ensure_ascii=False, indent=2, default=str))
            return
        if isinstance(value, (dict, list)):
            typer.echo(json.dumps(value, ensure_ascii=False, indent=2, default=str))
        else:
            typer.echo(str(value))


@ctl_app.callback()
def ctl_callback(
    ctx: typer.Context,
    url: str = typer.Option(None, "--url", envvar="SNSTUDIO_API_URL", help="API 地址"),
    json_output: bool = typer.Option(False, "--json", help="输出稳定 JSON"),
) -> None:
    ctx.obj = ClientContext(url or get_settings().api_url, json_output)


def client(ctx: typer.Context) -> ClientContext:
    return ctx.ensure_object(ClientContext)


def load_json(value: str | None, path: Path | None) -> dict[str, Any]:
    if path:
        return json.loads(path.read_text())
    return json.loads(value) if value else {}


@ctl_app.command("doctor")
def remote_doctor(ctx: typer.Context) -> None:
    client(ctx).emit(client(ctx).request("GET", "/api/v1/doctor"))


@ctl_app.command("engines")
def engines(ctx: typer.Context) -> None:
    client(ctx).emit(client(ctx).request("GET", "/api/v1/engines"))


@profiles_app.command("list")
def profile_list(ctx: typer.Context) -> None:
    client(ctx).emit(client(ctx).request("GET", "/api/v1/profiles"))


@profiles_app.command("upload")
def profile_upload(
    ctx: typer.Context,
    name: str = typer.Option(..., help="模型名称"),
    structure: Path = typer.Option(..., exists=True, dir_okay=False),
    composition: Path = typer.Option(..., exists=True, dir_okay=False),
) -> None:
    with structure.open("rb") as structure_handle, composition.open("rb") as composition_handle:
        result = client(ctx).request(
            "POST",
            "/api/v1/profiles",
            data={"name": name},
            files={
                "structure": (structure.name, structure_handle, "text/plain"),
                "composition": (composition.name, composition_handle, "text/plain"),
            },
        )
    client(ctx).emit(result)


def make_run_payload(
    engine: str,
    profile: str,
    name: str,
    params: str | None,
    params_file: Path | None,
    raw_file: Path | None,
    output_mode: str,
    project: str,
) -> dict[str, Any]:
    return {
        "project_id": project,
        "engine_id": engine,
        "profile_id": profile,
        "name": name,
        "parameters": load_json(params, params_file),
        "raw_parameters": raw_file.read_text() if raw_file else None,
        "output_mode": output_mode,
    }


@run_app.command("preview")
def run_preview(
    ctx: typer.Context,
    engine: str = typer.Option("supersnec"),
    profile: str = typer.Option("builtin:supersnec:stripped_star"),
    name: str = typer.Option("SNEC run"),
    params: str | None = typer.Option(None, help="JSON 参数对象"),
    params_file: Path | None = typer.Option(None, exists=True, dir_okay=False),
    raw_file: Path | None = typer.Option(None, exists=True, dir_okay=False),
    output_mode: str = typer.Option("full"),
    project: str = typer.Option("default"),
) -> None:
    payload = make_run_payload(
        engine, profile, name, params, params_file, raw_file, output_mode, project
    )
    client(ctx).emit(client(ctx).request("POST", "/api/v1/runs/preview", json=payload))


@run_app.command("submit")
def run_submit(
    ctx: typer.Context,
    engine: str = typer.Option("supersnec"),
    profile: str = typer.Option("builtin:supersnec:stripped_star"),
    name: str = typer.Option("SNEC run"),
    params: str | None = typer.Option(None, help="JSON 参数对象"),
    params_file: Path | None = typer.Option(None, exists=True, dir_okay=False),
    raw_file: Path | None = typer.Option(None, exists=True, dir_okay=False),
    output_mode: str = typer.Option("full"),
    project: str = typer.Option("default"),
) -> None:
    payload = make_run_payload(
        engine, profile, name, params, params_file, raw_file, output_mode, project
    )
    client(ctx).emit(client(ctx).request("POST", "/api/v1/runs", json=payload))


def sweep_payload(spec_file: Path) -> dict[str, Any]:
    return json.loads(spec_file.read_text())


@sweep_app.command("preview")
def sweep_preview(
    ctx: typer.Context, spec: Path = typer.Argument(..., exists=True, dir_okay=False)
) -> None:
    client(ctx).emit(
        client(ctx).request("POST", "/api/v1/sweeps/preview", json=sweep_payload(spec))
    )


@sweep_app.command("submit")
def sweep_submit(
    ctx: typer.Context, spec: Path = typer.Argument(..., exists=True, dir_okay=False)
) -> None:
    client(ctx).emit(client(ctx).request("POST", "/api/v1/sweeps", json=sweep_payload(spec)))


@ctl_app.command("status")
def status(
    ctx: typer.Context,
    run_id: str | None = typer.Argument(None, help="运行 ID；省略时列出最近任务"),
    limit: int = typer.Option(50, help="列出任务时的最大数量"),
) -> None:
    path = f"/api/v1/runs/{run_id}" if run_id else f"/api/v1/runs?limit={limit}"
    client(ctx).emit(client(ctx).request("GET", path))


@ctl_app.command("logs")
def logs(
    ctx: typer.Context, run_id: str, follow: bool = typer.Option(False, "--follow", "-f")
) -> None:
    offset = 0
    while True:
        result = client(ctx).request("GET", f"/api/v1/runs/{run_id}/logs?offset={offset}")
        typer.echo(result["text"], nl=False)
        offset = result["offset"]
        if not follow:
            break
        run = client(ctx).request("GET", f"/api/v1/runs/{run_id}")
        if run["status"] in {"succeeded", "failed", "cancelled", "interrupted"}:
            break
        time.sleep(1)


@ctl_app.command("results")
def results(ctx: typer.Context, run_id: str) -> None:
    client(ctx).emit(client(ctx).request("GET", f"/api/v1/runs/{run_id}/series"))


@ctl_app.command("compare")
def compare(ctx: typer.Context, run_ids: list[str] = typer.Argument(...)) -> None:
    query = "&".join(f"run_ids={run_id}" for run_id in run_ids)
    client(ctx).emit(client(ctx).request("GET", f"/api/v1/compare?{query}"))


@ctl_app.command("cancel")
def cancel(ctx: typer.Context, run_id: str) -> None:
    client(ctx).emit(client(ctx).request("POST", f"/api/v1/runs/{run_id}/cancel"))


@ctl_app.command("delete")
def delete(ctx: typer.Context, run_id: str) -> None:
    client(ctx).emit(client(ctx).request("DELETE", f"/api/v1/runs/{run_id}"))


def find_executable(name: str) -> str | None:
    discovered = shutil.which(name)
    if discovered:
        return discovered
    home = Path.home()
    candidates = [home / ".local" / "bin" / name, home / ".cargo" / "bin" / name]
    for root in (
        home / ".nvm" / "versions" / "node",
        home / ".local" / "config" / "nvm" / "versions" / "node",
    ):
        candidates.extend(sorted(root.glob(f"*/bin/{name}"), reverse=True))
    return (
        str(next((path for path in candidates if path.is_file() and os.access(path, os.X_OK)), ""))
        or None
    )


@studio_app.command("doctor")
def local_doctor() -> None:
    settings = get_settings()
    database = get_database()
    engines = [
        adapter.doctor().model_dump(mode="json") for adapter in EngineRegistry(settings).all()
    ]
    result = {
        "ok": any(engine["enabled"] for engine in engines),
        "data_dir": str(settings.data_dir),
        "database": str(database.path),
        "engines": engines,
        "node": find_executable("node"),
        "npm": find_executable("npm"),
        "pnpm": find_executable("pnpm"),
        "uv": find_executable("uv"),
    }
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["ok"]:
        raise typer.Exit(1)


@studio_app.command("start")
def start(
    no_browser: bool = typer.Option(False, help="不自动打开浏览器"),
    api_only: bool = typer.Option(False, help="只启动 API，不启动 Worker"),
) -> None:
    settings = get_settings()
    env = os.environ.copy()
    processes: list[subprocess.Popen[Any]] = []
    try:
        if not api_only:
            processes.append(subprocess.Popen([sys.executable, "-m", "snstudio.worker"], env=env))
        processes.append(
            subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "snstudio.main:app",
                    "--host",
                    settings.host,
                    "--port",
                    str(settings.port),
                ],
                env=env,
            )
        )
        typer.echo(f"超新星模拟台已启动：{settings.api_url}")
        if not no_browser:
            time.sleep(1.2)
            webbrowser.open(settings.api_url)
        return_code = processes[-1].wait()
        raise typer.Exit(return_code)
    except KeyboardInterrupt:
        typer.echo("正在停止服务…")
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
        for process in processes:
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()


@studio_app.command("install-skill")
def install_skill(force: bool = typer.Option(False, help="覆盖已有 Skill")) -> None:
    repository = Path(__file__).resolve().parents[3]
    source = repository / "skill" / "sn-simulation-studio"
    target = Path.home() / ".codex" / "skills" / "sn-simulation-studio"
    if not source.is_dir():
        typer.echo(f"找不到 Skill：{source}", err=True)
        raise typer.Exit(1)
    if target.exists():
        if not force:
            typer.echo(f"Skill 已存在：{target}；使用 --force 覆盖", err=True)
            raise typer.Exit(1)
        shutil.rmtree(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target)
    typer.echo(f"已安装：{target}")


@studio_app.command("deploy")
def deploy(target: str = typer.Argument(..., help="SSH 目标，例如 user@server")) -> None:
    repository = Path(__file__).resolve().parents[3]
    script = repository / "ops" / "deploy.sh"
    if not script.is_file():
        typer.echo(f"找不到部署脚本：{script}", err=True)
        raise typer.Exit(1)
    raise typer.Exit(subprocess.call([str(script), target], cwd=repository))
