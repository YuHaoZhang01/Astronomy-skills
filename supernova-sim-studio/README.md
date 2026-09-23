# 超新星模拟台

一个本机优先、可远程部署的 SNEC、SuperSNEC 与 OpenStella Web 工作台。它提供独立科研项目、中文参数表单、隔离运行目录、持久任务队列、参数扫描、实时日志、交互式光变/速度/温度图、CLI 和 Codex Agent Skill。

## Mac 快速开始

机器需要 `uv`；项目已经构建好前端，因此不要求本机安装 Docker。

```bash
cd /Users/zyh/Desktop/SNfitting-skill/supernova-sim-studio
./snstudio doctor
./snstudio start
```

浏览器打开 `http://127.0.0.1:8787`。关闭浏览器不会停止计算；停止启动命令才会关闭本机 API 与 Worker。默认数据位于 `~/Library/Application Support/Supernova Simulation Studio`，可用 `SNSTUDIO_DATA_DIR` 覆盖。

当前自动发现：

- SuperSNEC：`/Users/zyh/Library/CloudStorage/OneDrive-个人/ResearchOps/01_personal_projects/11-Early_Radiation/SuperSNEC`
- SNEC 1.01：`/Users/zyh/Desktop/software/SNEC`
- OpenStella：`/Users/zyh/Desktop/software/OpenStella`，固定提交 `6c6ad649a9987595da7fc57e735f640c5375e329`。

如需在另一台 Mac 安装同一版本的 OpenStella，先安装 `gcc@15` 与 `open-mpi`，再运行：

```bash
brew install gcc@15 open-mpi
./ops/install-openstella.sh /Users/zyh/Desktop/software/OpenStella
```

构建脚本会生成官方 90-zone `m030307mhomo` 模型、6 组 opacity table 和 STELLA 主程序，并逐项检查产物与完成标志。

## CLI 与 Agent Skill

```bash
./snctl --json engines
./snctl --json run preview --params '{"Ni_mass":0.05,"final_energy":1e51}'
./snctl --json run submit --params '{"Ni_mass":0.05,"final_energy":1e51}'
./snctl --json sweep preview examples/sweep.json
./snstudio install-skill
```

远程使用时设置 `SNSTUDIO_API_URL=https://服务器的-MagicDNS-名称`，CLI 和 Agent Skill 即会操作服务器队列。批量提交、取消和删除应先预览并由用户确认。

## 空白 Ubuntu 24.04 一键部署

前提是服务器已经可以通过 SSH 登录，账号可使用 `sudo`，并准备一个一次性、预授权的 Tailscale auth key。

```bash
./snstudio deploy user@server
```

脚本会安装 Docker Engine、Tailscale、GNU Fortran 与 OpenMPI，固定检出 SuperSNEC 提交 `318fc4160a28a6299db9f58966b79c8d2d35a440` 和 OpenStella 提交 `6c6ad649a9987595da7fc57e735f640c5375e329`，在服务器上原生编译 SNEC 与 OpenStella，启动 API/Worker，确认 STELLA doctor 已启用，并通过 Tailscale Serve 暴露 HTTPS。应用端口只绑定服务器的 `127.0.0.1:8787`，不会直接开放到公网。

## 任务正确性

- 每个任务拥有独立的 `parameters`、模型副本、`Data/`、日志和 manifest。
- 成功不仅检查退出码，还要求 `Done! :-)` 以及光度、速度、星等和 SuperSNEC summary 产物。
- 原版 SNEC 的合法均匀质量网格枚举是 `uniform_in_mass`；客户端会拒绝会导致静默退出的 `uniform_by_mass`。
- OpenStella 成功条件同时要求退出码 0、`Normal stop of stella`，以及非空且可解析的 `.tt/.lbol/.swd/.res`；可恢复的 `IFAIL=3` 步长回退不会被误判为失败。
- 单次运行默认完整输出；扫描默认 `output_mode=1`，保留拟合所需标量并降低磁盘占用。
- 删除操作把运行目录移动到应用的 `trash/`，不会立即不可恢复地清除文件。

API 的交互文档位于 `/docs`，主要接口位于 `/api/v1`。后端测试运行方式：

```bash
cd backend
uv run --extra dev pytest -q
uv run --extra dev ruff check src tests
```

## 许可与引用

本工作台面向个人科研。所有求解器保持在独立目录并保留上游许可：SuperSNEC 与 SNEC 1.01 使用 CC BY-NC-SA 4.0，OpenStella 使用 GPL-3.0。发表 SNEC 结果时应引用 Morozova, Piro & Ott (2015, ApJ, 814, 63)，使用 SuperSNEC 时还应按其 `CITATION.cff` 引用扩展代码；OpenStella 结果请遵守其仓库中的引用说明。
