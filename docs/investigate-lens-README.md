# Investigate Lens — DiVo Gen²AI 动态资产知识库

**日期**: 2026-06-30

> *人是会制造和使用工具的高等灵长类哺乳动物——马克思*

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![SQLite](https://img.shields.io/badge/Storage-SQLite%20WAL-green)](https://www.sqlite.org/)
[![MCP](https://img.shields.io/badge/Protocol-MCP%20stdio-orange)](https://modelcontextprotocol.io/)

> **一句话**：把散落在 15 个 Python 环境、68 个模型权重、37 个数据集、7 条流水线里的计算资产，自动扫描进 SQLite，通过 MCP 协议暴露给 AI 助手实时查询——替代手动维护的静态文档，成为团队的单点真相（Single Source of Truth）。

## 为什么需要这个工具？

如果你的团队和我们有类似的处境——

| 痛点 | 表现 | 后果 |
|------|------|------|
| **信息过时** | MHCflurry 实际版本 2.3.0rc4，文档中仍为 2.2.1 | AI 助手基于错误信息做决策 |
| **维护成本高** | 每次部署新工具/升级版本需手动更新几百行文档 | 信息滞后持续恶化 |
| **查询能力弱** | 静态文本无法查询"torch 在哪些环境有装" | 重复劳动，效率低下 |

那么 Investigate Lens 就是为此而生的。

---

## 架构总览

```
┌─────────────────────────────────────────────────────┐
│                  investigate_lens                    │
│                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │ 6 扫描器  │→│ SQLite DB │→│ 3 报告器  │          │
│  │ conda    │  │ 9 张表    │  │ JSON     │          │
│  │ venv/uv  │  │ 2516 包   │  │ Markdown │          │
│  │ models   │  │ 68 模型   │  │ Query    │          │
│  │ datasets │  │ 37 数据集 │  └──────────┘          │
│  │ cloud    │  │ 8 云资源  │                        │
│  │ pipelines│  │ 7 管线    │  ┌──────────┐          │
│  └──────────┘  └──────────┘  │ MCP Server│          │
│                               │ 5 工具    │          │
│                               │ il_query  │          │
│                               │ il_get_*  │          │
│                               └──────────┘          │
└─────────────────────────────────────────────────────┘
         ↑ cron 每日 + shell hook       ↓ AI IDE 实时调用
```

## 核心指标

| 指标 | 数值 |
|------|------|
| 扫描环境 | 15 个（10 conda + 5 venv/uv） |
| 采集包记录 | 2,516 条 |
| 发现模型权重 | 68 个 |
| 登记数据集 | 37 个 |
| 云资源 | 8 项 |
| 流水线 | 7 条 |
| 工具版本注册 | 34 条 |
| 全量扫描耗时 | **9.6 秒** |
| 增量扫描耗时 | **5.2 秒** |
| 数据库体积 | 464 KB |
| JSON 快照体积 | 536 KB |
| 代码量 | 3,994 行 Python + 148 行 Shell |
| 新环境纳入延迟 | 即时（shell hook）或最多 24h（daily cron） |

---

## 模块架构

```
investigate_lens/
├── config.py                  # WorkspaceConfig — 路径权威来源（frozen dataclass）
├── types.py                   # 8 个 dataclass — 统一数据模型
├── __main__.py                # CLI 入口 — scan / query / report / status
│
├── scanners/                  # 6 个扫描器
│   ├── base.py                # BaseScanner ABC — scan + fingerprint + detect_changes
│   ├── conda_env.py           # Conda 环境 — 直接读 conda-meta/*.json，避免子进程
│   ├── venv_uv.py             # venv/uv 环境 — 已知路径 + 有限深度搜索
│   ├── models_weights.py      # 模型权重 — 5 来源（manifest/HF/runtime/MHCflurry/VERSIONS.yml）
│   ├── datasets.py            # 数据集 — 项目 data/ + biodb + 扩展搜索
│   ├── cloud.py               # 云资源 — 三级降级（API → config → script）
│   └── pipelines.py           # 流水线 — Nextflow/Snakemake 解析
│
├── storage/                   # 持久化层
│   ├── db.py                  # InvestigateDB — SQLite 9 表，WAL 模式
│   └── fingerprint.py         # 4 种指纹函数 — 增量变更检测
│
├── reporters/                 # 报告层
│   ├── json_reporter.py       # AI 可读 JSON 快照
│   ├── markdown_reporter.py   # 人可读 Markdown 审计报告（7 章节）
│   └── query_engine.py        # 自然语言关键词路由查询
│
├── mcp_server/                # MCP Server
│   ├── server.py              # MCP 协议实现 — 5 个 Tool
│   └── run.sh                 # 启动脚本
│
└── run_investigate_lens.sh    # 定时执行 — 快照→扫描→验证→回滚保护
```

### 数据流

```
                    ┌─────────────┐
                    │ 6 Scanners  │
                    └──────┬──────┘
                           │ ScanResult
                    ┌──────▼──────┐
                    │ InvestigateDB│  SQLite (WAL, 9 tables)
                    └──────┬──────┘
                   ┌────────┼────────┐
                   │        │        │
            ┌──────▼──┐ ┌──▼────┐ ┌─▼────────┐
            │ JSON    │ │ MD    │ │ MCP Server│
            │ Snapshot│ │ Report│ │ 5 Tools   │
            └─────────┘ └───────┘ └───────────┘
                ↓           ↓           ↓
           AI agent      人类       AI IDE
         离线读取      审计        实时查询
```

---

## 增量扫描机制

双层指纹驱动增量扫描，避免重复计算：

```
ScanRequest
  → compute_fingerprints()      # 计算 L1(mtime+size) 或 L2(MD5 content hash)
  → detect_changes()            # 与 DB 存储指纹比对
  → 仅扫描变化的实体           # 节省 ~70% 时间
  → 更新指纹表
```

| 指纹函数 | 策略 | 适用 |
|----------|------|------|
| `compute_file_fingerprint` | `mtime:size` | 单文件（最快） |
| `compute_dir_fingerprint` | `MD5(子文件mtime:size)[:16]` | 目录（可限深度） |
| `compute_conda_env_fingerprint` | `conda-meta/history` 的 mtime:size | Conda 环境 |
| `compute_venv_fingerprint` | `pyvenv.cfg` 的 mtime:size | venv 环境 |

---

## 6 个扫描器详解

### CondaEnvScanner

**策略**：直接读取 `conda-meta/*.json` + `site-packages/*/METADATA`，**避免 `pip list` 子进程**。

- 遍历 `miniconda3/envs/` 下所有含 `conda-meta/` 的子目录
- 50+ 关键包名列表（torch, mhcflurry, rdkit, protenix, nextflow, snakemake 等）
- 性能优化：从 ~15s（pip list 子进程）降至 ~3s（直接文件解析）
- 包去重：conda-meta 和 site-packages 可能存在同名包，pip 版本优先
- 自动清理：对比磁盘与 DB，删除已不存在的环境记录

### VenvUvScanner

**策略**：已知固定路径 + 有限深度（3 层）搜索，跳过 /mnt/ 和隐藏目录。

- 跳过 30+ 不可能含 venv 的目录（.cache, .config, .ssh, miniconda3 等）
- WSL2 /mnt/ Windows 挂载完全不搜索（极慢）
- 自动清理：对比磁盘与 DB，删除已不存在的 venv 记录

### ModelsWeightsScanner

**5 个模型来源**：

| # | 来源 | 说明 | 示例 |
|---|------|------|------|
| 1 | `weights_manifest.yml` | 权威注册中心，含 `${PROJECT_ROOT}` 变量替换 | protenix-v2, boltz2-conf |
| 2 | HuggingFace 缓存 | `~/.cache/huggingface/hub/models--*` | esm2_t33_650M, esmfold_v1 |
| 3 | 运行时权重目录 | `weights/` 下搜索 `.pt/.safetensors` 等 | protenix-base-v1.0.0 |
| 4 | MHCflurry 模型 | `~/.local/share/mhcflurry/` | MHC-I 预测模型 |
| 5 | VERSIONS.yml | 工具版本注册表 | 34 个工具的版本与 Tier |

含路径可达性检测。

### DatasetsScanner

**3 个数据源**：

1. 项目 `data/` 目录
2. `/mnt/e/biodb/`（容错，depth=1 浅层扫描）
3. scan_roots 下扩展 `data/` 子目录

10 种类型推断：vcf, fasta, pdb, csv, pt, json, bam, h5, parquet, other

### CloudScanner — 三级降级

```
Level 1: 云平台 API           → 实例状态（需 token）
Level 2: 配置文件解析         → GPU/资源/版本配置
         部署脚本解析         → conda 环境定义
Level 3: 运行脚本推断         → GPU 类型/CUDA 版本
```

当 API 不可用时，从配置文件和脚本中提取尽可能多的信息，不因网络问题丢失全部云资源数据。

### PipelinesScanner

- 从 `pipeline_dirs` 直接检测 + scan_roots 有限深度搜索（max_depth=4）
- Nextflow：提取 modules、profiles、processes（正则 `process\s+(\w+)`）
- Snakemake：提取 rules、config、modules
- 60+ 个跳过目录（miniconda3, databases, node_modules 等）

---

## 存储设计

### SQLite Schema（9 张表）

```sql
scan_runs(id, timestamp, scan_type, duration_seconds, scanners_run, items_scanned, items_changed)
fingerprints(entity_id, scanner_name, fingerprint, updated_at)  -- UNIQUE(entity_id, scanner_name)
envs(name, env_type, path, python_version, conda_package_count, pip_package_count,
     total_size_mb, key_packages JSON, last_modified, fingerprint)  -- PK(name)
packages(env_name, name, version, source, build, channel, summary)  -- PK(env_name, name)
models(model_id, display_name, source_type, source_path, version, size_bytes, size_human,
       developer, license, required_by JSON, is_external, accessible)  -- PK(model_id)
datasets(path, parent_project, dataset_type, file_count, total_size_bytes, total_size_human,
         is_symlink, symlink_target, is_external, accessible, subdirs JSON)  -- PK(path)
cloud_resources(resource_id, platform, source_type, source_file, gpu_type, status,
                max_cpus, max_memory, max_time, python_version, pytorch_version,
                cuda_version, config_data JSON)  -- PK(resource_id)
pipelines(pipeline_id, framework, root_path, config_path, modules JSON,
          profiles JSON, processes JSON, updated_at)  -- PK(pipeline_id)
versions_yml(source_file, tool_name, version, category, tier, priority, upstream, notes,
            raw_entry JSON)  -- PK(source_file, tool_name)
```

**配置**：`PRAGMA journal_mode=WAL` + `PRAGMA foreign_keys=ON`

**Upsert 策略**：全部 `INSERT OR REPLACE`；packages 表先 DELETE 再 INSERT（pip 优先去重）

---

## MCP Server — AI 实时查询接口

### 设计动机

静态文档两个核心问题：
1. **信息过时**：MHCflurry 从 2.2.1 升级到 2.3.0rc4，文档未同步
2. **无法查询**：无法回答"torch 在哪些环境有装、各自什么版本"

MCP Server 让 AI 助手直接查询实时数据库，不再依赖静态文档。

### 5 个 MCP Tool

| Tool | 功能 | 输入 |
|------|------|------|
| `il_query` | 通用关键词路由查询 | `query: string` |
| `il_get_envs` | 环境详情 + 关键包版本 | `name?: string` |
| `il_get_models` | 模型/权重清单 | `name?: string` |
| `il_check_gpu_fit` | GPU 显存可用性判断 | `model_name: string` |
| `il_get_summary` | 资产总览（按章节） | `section?: string` |

### il_query 关键词路由

| 查询示例 | 路由目标 |
|----------|----------|
| `"torch versions"` | 跨环境 torch 版本矩阵 |
| `"aibioinfo packages"` | 环境详情 |
| `"protenix models"` | protenix 相关模型搜索 |
| `"cloud autodl"` | 云资源状态 |
| `"neoantigen pipeline"` | 管线查询 |
| `"summary"` | 全量资产摘要 |

### il_check_gpu_fit 示例

```json
// il_check_gpu_fit(model_name="protenix-v2")
{
  "model": "protenix-v2",
  "vram_estimated_gb": 10.0,
  "local_vram_gb": 4.0,
  "status": "❌ 不可用（需云端/大GPU）",
  "recommendation": "需 10.0GB 显存，本地 4GB 不足，建议使用云端 A100 或 CPU 模式"
}

// il_check_gpu_fit(model_name="esm2_t33_650M")
{
  "model": "esm2_t33_650M",
  "vram_estimated_gb": 2.5,
  "local_vram_gb": 4.0,
  "status": "✅ 可用",
  "recommendation": "可在本地 4GB GPU 上运行，预估显存 2.5GB"
}
```

### 技术实现

- 基于 `mcp` Python SDK v1.28.1，stdio 协议
- DB 只读访问（`file:path?mode=ro`）
- 18 个模型的显存估算表（`MODEL_VRAM_TABLE`）
- 本地 GPU 限制可配置（默认 4.0 GB，对应 RTX 3050 Ti）
- AI IDE 注册：通过 `mcp.json` 配置

---

## 自动纳入新环境（三层保障）

| 层级 | 机制 | 触发条件 | 延迟 |
|------|------|----------|------|
| **Shell Hook** | `conda`/`python` function wrapper | `conda create`/`conda remove`/`python -m venv` | **即时**（后台增量扫描 ~5s） |
| **Daily Cron** | `flock` + 全量扫描 | 每天 11:50 | 最多 24h |
| **手动** | `il-scan` / `il-quick` | 工程师主动 | 立即 |

### Shell Hook 实现

在 `~/.bash_aliases` 中定义 function wrapper：

```bash
conda() {
    command ~/miniconda3/bin/conda "$@"
    local ret=$?
    if [[ $ret -eq 0 ]]; then
        case "$1" in
            create|remove)  _il_auto_scan ;;
            env) case "$2" in create|remove) _il_auto_scan ;; esac ;;
        esac
    fi
    return $ret
}

python() {
    command "$_real_python" "$@"
    local ret=$?
    [[ $ret -eq 0 && "$1" == "-m" && "$2" == "venv" ]] && _il_auto_scan
    return $ret
}

_il_auto_scan() {
    (nohup bash ~/wk/investigate_lens/run_investigate_lens.sh incremental \
      >> ~/.investigate_lens/logs/hook.log 2>&1 &)
}
```

> 如需绕过 hook（如在脚本中），使用 `command conda ...` 或 `command python ...`。

### DB 清理

每次扫描时，conda_env 和 venv_uv 扫描器自动对比磁盘与 DB，删除已不存在环境的记录（envs + packages + fingerprints 行），`conda remove` 后不会残留旧数据。

---

## 运维体系

### 定时执行

```cron
50 11 * * * /usr/bin/flock -n ~/.investigate_lens/.cron.lock \
  bash ~/wk/investigate_lens/run_investigate_lens.sh full \
  >> ~/.investigate_lens/logs/cron.log 2>&1
```

- 每天 11:50 执行全量扫描（兜底保障）
- `flock -n` 防止重叠执行

### 快照 + 回滚保护

```
Step 1: DB 快照    → cp investigate_lens.db → .snapshot_YYYYMMDD_HHMMSS
Step 2: 执行扫描   → timeout 120s 包裹，超时/失败 → 回滚
Step 3: 验证新 DB  → 检查 5 张核心表存在 + envs 有数据 → 失败回滚
Step 4: 生成报告   → report --format both
Step 5: 清理       → 保留 4 个快照 + 8 个日志
```

### Shell 快捷命令

| 别名 | 功能 |
|------|------|
| `il-scan` | 全量扫描（带快照+回滚） |
| `il-scan-inc` | 增量扫描 |
| `il-q "query"` | 查询（如 `il-q "mhcflurry version"`） |
| `il-report` | 生成 JSON + Markdown 报告 |
| `il-status` | 查看指纹变化状态 |
| `il-full` | 一键：全量扫描 + 报告 |
| `il-quick` | 一键：增量扫描 + 报告 |
| `il-log` | 查看最近日志 |

---

## 工程实现过程

### 开发时间线

| 阶段 | 内容 | 关键决策 |
|------|------|----------|
| **Day 1: 数据建模** | 定义 8 个 dataclass + WorkspaceConfig | scan_roots 必须覆盖 $HOME + /mnt/，不限于 ~/wk/ |
| **Day 1: 扫描器实现** | 6 个扫描器，直接文件解析避免子进程 | conda_env 读 conda-meta/*.json 而非 `conda list` |
| **Day 1: 存储层** | SQLite 9 表 + WAL + 指纹增量 | 双层指纹：L1 mtime:size（快），L2 MD5 content hash（准） |
| **Day 2: 性能优化** | /mnt/ 浅层扫描 + skip_dirs + 深度限制 | /mnt/e/biodb 用 iterdir() 不用 rglob()；60+ 个跳过目录 |
| **Day 2: 报告层** | JSON 快照 + Markdown 报告 + Query 引擎 | Query 用关键词路由而非全文搜索（精确度优先） |
| **Day 2: 运维体系** | cron + flock + 快照回滚 + shell aliases | 超时 120s 自动 kill 不重试；验证失败自动回滚快照 |
| **Day 3: MCP Server** | Python mcp SDK v1.28.1 + stdio 协议 | 5 个 tool 覆盖全部查询场景；DB 只读模式 |
| **Day 3: Skills 改造** | 静态文档 563 行 → 114 行 | 动态数据指向 MCP，保留非动态指导内容 |
| **Day 4: 自动纳入** | Shell hook + daily cron + DB 清理 | conda/python wrapper 即时触发；cron 改为每天；扫描器加 _cleanup_stale |

### 性能优化历程

全量扫描从 >120s 超时优化到 9.6s，经历 5 轮瓶颈定位与修复：

| # | 瓶颈 | 耗时 | 优化手段 | 效果 |
|---|------|------|----------|------|
| 1 | `/mnt/e/biodb` rglob 极慢 | >60s | datasets 用 max_depth=1 + iterdir() | 降至 <5s |
| 2 | venv rglob $HOME 极慢 | >60s | 已知路径 + 3 层有限搜索 + skip /mnt/ | 降至 <2s |
| 3 | pip list 子进程 ×10 环境 | ~15s | 直接读 conda-meta/*.json + METADATA | 降至 ~3s |
| 4 | pipelines 进入 miniconda3/databases | >10s | 60+ 个 skip_dirs + nextflow.config 检测 | 降至 <2s |
| 5 | glob("*.nf") 遍历大目录 | >5s | 替换为 `(dir/"nextflow.config").exists()` | 降至 <1s |

**核心经验**：WSL2 的 /mnt/ Windows 挂载 I/O 比原生 Linux 慢 10-100 倍，必须浅层扫描 + 全面跳过。

### 遇到的 Bug 与修复

| Bug | 原因 | 修复 |
|-----|------|------|
| `UNIQUE constraint failed: packages.env_name, packages.name` | conda-meta 和 site-packages 存在同名包 | upsert_packages 先 DELETE 再 INSERT，pip 版本优先 |
| venv scanner rglob $HOME 卡死 | Python 的 rglob 在 $HOME 下遍历海量文件 | 替换为已知路径 + 有限深度搜索 |
| /mnt/e/biodb iterdir 子目录极慢 | Windows 挂载 I/O 延迟 | venv 完全跳过 /mnt/；datasets 用 depth=1 |
| DB 创建后 WAL/SHM 残留 | 杀死卡死进程后锁文件未清理 | rm -f investigate_lens.db* 后重跑 |
| MCP server import 循环 | types.py 遮蔽 stdlib types | MCP server 移至 mcp_server/ 子目录 |
| `conda remove` 后 DB 残留旧环境 | 增量扫描只更新不删除 | 加 `_cleanup_stale_envs`/`_cleanup_stale_venvs` 对比磁盘后删除 |

---

## 使用示例

### 命令行

```bash
# 全量扫描
il-scan

# 增量扫描（仅扫描变化的实体）
il-scan-inc

# 查询
il-q "torch versions"          # torch 跨环境版本矩阵
il-q "aibioinfo packages"      # 某环境关键包
il-q "protenix models"         # protenix 相关模型
il-q "cloud autodl"            # 云资源状态
il-q "summary"                 # 全量资产摘要

# 生成报告
il-report                      # JSON + Markdown

# 查看指纹状态
il-status
```

### MCP Tool（AI IDE 内）

```
il_query(query="mhcflurry version")     → aibioinfo: 2.3.0rc4
il_get_envs(name="protenix")            → protenix 环境详情 + 关键包
il_get_models(name="esm")              → 所有 ESM 模型 + 路径 + 大小
il_check_gpu_fit(model_name="boltz2")  → ❌ 不可用，需 8.0GB
il_get_summary(section="models")       → 模型资产总览
```

### Python API

```python
from investigate_lens.storage.db import InvestigateDB

db = InvestigateDB("~/wk/.investigate_lens/investigate_lens.db")
envs = db.get_all_envs()           # 所有环境
models = db.get_all_models()       # 所有模型
pkgs = db.search_packages("torch") # 搜索 torch
```

---

## 配置与部署

### 路径配置（config.py）

`WorkspaceConfig` 是 frozen dataclass，所有路径的权威来源：

| 字段 | 说明 |
|------|------|
| `scan_roots` | 扫描根（OS 级全覆盖，含 $HOME、工具目录、数据目录） |
| `conda_envs_dir` | Conda 环境目录 |
| `weights_manifest_path` | 权威权重注册中心 |
| `biodb_dir` | 生物数据库目录（WSL2 挂载需特殊处理） |
| `output_dir` | 输出目录（DB + 报告 + 快照） |

### MCP 注册

在 AI IDE 的 `mcp.json` 中添加：

```json
{
  "mcpServers": {
    "investigate_lens": {
      "command": "/path/to/investigate_lens/mcp_server/run.sh",
      "env": {
        "START_MCP_TIMEOUT_MS": "10000",
        "RUN_MCP_TIMEOUT_MS": "30000"
      }
    }
  }
}
```

### MCP Server 依赖

```bash
cd investigate_lens
uv venv .venv --python 3.12
uv pip install --python .venv/bin/python mcp  # v1.28.1
```

---

## 文件清单

| 文件 | 行数 | 说明 |
|------|------|------|
| `config.py` | ~80 | WorkspaceConfig |
| `types.py` | ~120 | 8 个 dataclass |
| `__main__.py` | ~130 | CLI 入口 |
| `scanners/base.py` | ~60 | BaseScanner ABC |
| `scanners/conda_env.py` | ~250 | Conda 环境扫描 |
| `scanners/venv_uv.py` | ~200 | venv/uv 扫描 |
| `scanners/models_weights.py` | ~350 | 模型权重扫描（5 来源） |
| `scanners/datasets.py` | ~200 | 数据集扫描 |
| `scanners/cloud.py` | ~300 | 云资源扫描（三级降级） |
| `scanners/pipelines.py` | ~250 | 流水线扫描 |
| `storage/db.py` | ~300 | SQLite 持久化 |
| `storage/fingerprint.py` | ~100 | 指纹函数 |
| `reporters/json_reporter.py` | ~80 | JSON 快照 |
| `reporters/markdown_reporter.py` | ~250 | Markdown 报告 |
| `reporters/query_engine.py` | ~200 | 查询引擎 |
| `mcp_server/server.py` | ~330 | MCP Server（5 Tool） |
| `run_investigate_lens.sh` | 144 | 定时执行脚本 |
| **合计** | **~3,994** | **Python + Shell** |

---

## 适用场景

Investigate Lens 诞生于 DiVo Gen²AI 团队——一个专注生物计算（蛋白质结构预测、新抗原预测、mRNA 设计、酶工程）的 AI 工程团队。但它不限于生物计算，任何拥有以下特征的 AI 工程团队都可以使用：

- **多 Python 环境共存**（conda + venv + uv），需要知道哪个包在哪个环境
- **大量本地模型权重**（HuggingFace 缓存 + 自定义权重），需要快速检索和可达性检查
- **云 + 本地混合部署**，需要统一视角查看资源分布
- **AI 辅助编程**（Trae / Cursor / Claude Code 等），需要让 AI 实时查询环境信息而非依赖过期文档
- **多人协作**，需要单点真相避免"你本地能跑我跑不了"

---

*DiVo Gen²AI · Investigate Lens v1.0.0 · 2026-06-30*
