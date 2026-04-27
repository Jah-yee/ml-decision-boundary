# DEPENDENCY_POLICY.md

**版本**: v0.1 (2026-04-27)  
**范围**: Jah-yee/ml-decision-boundary 的所有直接或传递依赖

---

## 1. 原则

| # | 原则 | 说明 |
|---|------|------|
| D1 | **最小依赖集** | 只引入达成 Mission 所需的最小依赖；禁止引入等效替代品 |
| D2 | **版本稳定性** | 必须指定上界（`>=`）；禁止无上界裸 `>=` 引发午夜破坏性升级 |
| D3 | **可复现性** | 所有依赖变更必须同步到 `requirements.txt`；禁止跳过 lock step |
| D4 | **零隐蔽依赖** | 禁止引入不在 `requirements.txt` 中的隐蔽依赖（ transitive deps 除外） |
| D5 | **测试可隔离** | pytest 必须在 `requirements.txt` 中声明，以便 CI 和本地一致 |

---

## 2. 环境约束（硬边界）

由于本项目运行在以下受限环境，引入依赖前必须评估：

| 约束 | 上限 | 当前状态 |
|------|------|----------|
| **Serverless 冷启动** | Vercel Hobby 10s / Pro 60s | ✅ 全部 < 3s |
| **依赖总体积** | 参考 Vercel 50MB 软限 | ✅ 估算 < 30MB |
| **纯 CPU 推理** | 无 GPU/CUDA | N/A（sklearn 全 CPU） |
| **无 Rust 工具链** | 纯 Python + C-extension | ✅ 当前全是 |
| **Python 版本** | >= 3.9（OpenClaw runtime） | ✅ 3.9+ |

---

## 3. 依赖分级

### 3.1 P0 — 核心依赖（必须始终可用）

| 包 | 版本约束 | 用途 |
|---|----------|------|
| `numpy` | `>=1.24.0` | 数据基础 |
| `scikit-learn` | `>=1.3.0` | 所有 ML 模型 |
| `matplotlib` | `>=3.7.0` | 可视化 |

### 3.2 P1 — 可选扩展（按需引入）

| 包 | 版本约束 | 引入条件 |
|---|----------|----------|
| `flask` | `>=3.0.0` | 仅当启用 HTTP API 时 |
| `pytest` | `>=7.0.0` | 测试框架，CI 必须 |

### 3.3 禁止引入的依赖

| 包/类 | 原因 |
|--------|------|
| `torch`, `tensorflow`, `jax` | 体积 > 500MB，冷启动不可接受 |
| `transformers`, `diffusers` | 需要 GPU，不适合 serverless |
| `dask`, `ray` | 分布式，非本项目定位 |
| `xgboost`, `catboost` | 与 RF/Tree 功能重叠，引入需评审 |
| `pandas` | 数据规模小（合成 2D），引入过度设计 |
| `polars` | 同上，且生态较小 |

---

## 4. 变更流程

任何依赖变更（增/删/升级）必须：

1. **本地验证**: `pip install -r requirements.txt` 成功
2. **P0 通过**: `python3 -m compileall .` 无错误
3. **P1 通过**: `pytest -q` 通过
4. **Benchmark 检查**: `python3 main.py` 冷启动 < 10s
5. **写入 CHANGELOG.md**: 注明变更内容
6. **Commit**: commit message 包含 `deps:` 前缀

---

## 5. 当前依赖快照（2026-04-27）

```
flask>=3.0.0        # HTTP API（serverless）
numpy>=1.24.0       # 数据基础
matplotlib>=3.7.0   # 可视化
scikit-learn>=1.3.0 # ML模型
pytest>=7.0.0       # 测试框架
```

**总体积估算**: ~25MB（numpy 15MB + sklearn 8MB + matplotlib 10MB + flask 1MB = 34MB，实际有 overlap，净估算 < 30MB）

---

## 6. 待办（与依赖相关）

- [ ] 评估 sklearn 1.3+ 的 `MLPClassifier` max_iter 默认值变化（已在本仓库设为 2000）
- [ ] 添加 `pip-compile` 或 `pip-lock` 流程（防止传递依赖隐性升级）
- [ ] 监控 Vercel cold start 时间（当前 < 3s，若超 10s 需砍 matplotlib）
