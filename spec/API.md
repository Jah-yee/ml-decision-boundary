# API Contract — ml-decision-boundary

**Status**: Active (v13 in progress)
**Last updated**: 2026-10-26 (v13 DoD #1 provenance)

本文件记录 HTTP API 的行为契约。P3 验收要求「API/Web 行为在 spec 中记录」。

---

## 部署形态

| 形态 | 入口 | 说明 |
|------|------|------|
| Vercel Serverless | `api/*.py` | 每个文件导出一个 `handle(req, res)`；`res.json(...)` 返回 JSON，`res.status` 设置状态码 |
| 本地 Flask | `web/server.py` | `@app.route(...)`，与 serverless 保持同一 URL 与响应结构 |

同一 URL 在本地与生产环境返回**相同结构**的响应。

> **Registry 根目录重定向**：设置环境变量 `MLDB_REGISTRY_BASE=/path/to/registry` 可让 CLI、SDK
> 与本地 Flask 一起指向同一个 registry 根目录（便于本地验证与测试隔离）。
> 未设置时使用默认路径 `~/.ml-decision-boundary/registry`。

---

## 端点总览

| 方法 | 路径 | 用途 | 引入版本 |
|------|------|------|----------|
| GET | `/api/health` | 健康检查 | 初始 |
| POST | `/api/train` | 同步训练，返回决策边界 | 初始 |
| GET | `/api/models/<model_name>` | 模型元数据目录 | v53 |
| GET | `/api/datasets` | 数据集目录 | v53 |
| POST | `/api/predict/batch` | 批量预测 | v56 |
| POST | `/api/train_async` | 异步训练，返回 202 + `task_id` | v12 DoD #2 |
| GET | `/api/tasks` | 任务状态查询 / 列表 | v12 DoD #2 |
| GET | `/api/registry` | Registry 查询（版本 / 家族 / 批量标签） | **v12 DoD #3** |

---

## `GET /api/health`

健康检查。恒返回 200。

**请求**: 无参数。

**响应 200**:
```json
{ "status": "ok" }
```

**说明**: 本地 Flask 额外保留 `/health` 别名，两者行为一致。

---

## `GET /api/registry`

Registry 查询端点。覆盖三类查询：单模型元数据、模型版本/家族、标签批量查询。

### 查询参数

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `id` | string | — | 模型 ID。存在时返回该模型元数据 |
| `tags` | string | — | 逗号分隔的标签名列表，如 `?tags=prod,best`。一旦显式传入（即使是空串）即视为按标签过滤；解析后为空返回 400 |
| `match` | string | `any` | 标签匹配模式：`any`（至少命中一个）/ `all`（必须全部命中） |
| `versions` | `1`/`true`/`yes` | — | 与 `id` 联用，返回该模型所属 family 的全部版本 |
| `families` | `1`/`true`/`yes` | — | 返回模型家族分组 |

### 响应

**无参数** — 列出全部模型：
```json
{ "models": [ { "id": "...", "version": 1, "family": "...", ... } ], "count": 2 }
```

**`?id=<model_id>`** — 单模型元数据（200）：
```json
{
  "id": "2026-10-25_abc123",
  "model_type": "SVM",
  "version": 1,
  "family": "SVM|circles|C=1.0|gamma='scale'",
  "tags": ["prod"],
  "accuracy": 0.88
}
```

**`?id=<model_id>&versions=1`** — 该 family 的全部版本（200），`version` 升序：
```json
{
  "id": "2026-10-25_abc123",
  "family": "SVM|circles|C=1.0|gamma='scale'",
  "count": 2,
  "versions": [ { "version": 1, ... }, { "version": 2, ... } ]
}
```

**`?families=1`** — 家族分组（200）：
```json
{
  "families": { "SVM|circles|C=1.0": [ { "version": 1, ... }, { "version": 2, ... } ] },
  "count": 1,
  "version_total": 2
}
```

**`?tags=prod,best&match=all`** — 标签批量查询（200）：
```json
{
  "models": [ ... ],
  "count": 1,
  "tags": ["prod", "best"],
  "match": "all"
}
```

- `match=any`（默认）：模型**至少命中一个**标签 → 并集。
- `match=all`：模型**必须全部命中** → 交集。
- 结果按 `created_at` **降序**（最新在前）。

### 错误响应

| 状态码 | 场景 | 响应 |
|--------|------|------|
| `400` | `match` 非法（既非 `any` 也非 `all`） | `{"error": "Invalid tag match mode 'bogus'. Expected 'any' or 'all'."}` |
| `400` | `tags` 解析后为空 | `{"error": "Query parameter 'tags' must not be empty."}` |
| `404` | `id` 指定的模型不存在 | `{"error": "Model '<id>' not found ..."}` |
| `500` | 其他未预期异常 | `{"error": "<exception message>"}` |

---

## 版本化语义（v12 DoD #3）

**family key** = `model_type|dataset_name|<sorted hyperparameters>`。
超参键按字典序排序，值用 `repr` 渲染 —— 因此 `{"C": 1.0}` 与 `{"C": 1}` 属于**不同** family（可能训练出不同结果）。

**版本号**：同一 family 内重新训练时版本递增 `v1 → v2 → v3 ...`；不同 family 各自从 `v1` 开始。

**向后兼容**：v12 之前注册的模型元数据**不会被重写**。读取时由 `_normalize()` 动态补齐：

- 缺失 `version` → 视为 `1`
- 缺失 `family` → 由 `model_type` / `dataset.name` / `hyperparameters` 派生

因此旧 registry 无需迁移即可使用，新注册进旧 family 的模型版本号为 `max(现有版本) + 1`。

> **写入不变量**：`tag_model()` / `untag_model()` 使用原始（未规范化）元数据，只写回 `tags` 字段。
> 因此给旧模型打标签**不会**把派生的 `version` / `family` 写入旧 JSON 文件——旧文件形状保持不变。
> 派生值仍可通过读取路径（`get_metadata()` / `list_models()`）正常访问。

**模型 ID 格式不变**：`YYYY-MM-DD_<6位十六进制>`，与 v12 之前完全一致。

---

## Provenance 语义（v13 DoD #1）

新注册的模型元数据包含 `provenance` 对象：

```json
{
  "seed": 42,
  "dataset": {"name": "circles", "n_samples": 500, "noise": 0.3, "test_size": 0.2},
  "hyperparameters": {"C": 1.0},
  "model_type": "SVM",
  "environment": {"python": "3.12.3", "numpy": "...", "scikit_learn": "...", "joblib": "..."},
  "git": {"commit": "...", "branch": "...", "dirty": false},
  "captured_at": "2026-10-26T01:30:00+00:00",
  "fingerprint": "sha256:0123456789abcdef"
}
```

Fingerprint 使用 canonical JSON + SHA-256，覆盖 seed、dataset、hyperparameters、环境版本与 git commit；不覆盖 `captured_at` 与 `git.dirty`。v13 前的旧模型读取时返回空 `{}`，原 JSON 文件不重写。

本轮先通过 Registry / SDK / CLI 暴露 provenance；HTTP 端点列入下一轮，避免扩张已冻结的 API 契约。

---

## 相关文档

- ADR: `docs/adr/ADR-0018-v13-dod.md`
- 阶段状态: `spec/phases.md`
- SDK 用法: `ml_db/client.py`
