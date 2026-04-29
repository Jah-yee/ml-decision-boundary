# THREAT_MODEL.md — ml-decision-boundary

**版本**: v0.1 (2026-04-29)
**范围**: Jah-yee/ml-decision-boundary 全栈（本地 CLI / API / Serverless 部署）

---

## 1. 边界与信任边界

| 组件 | 信任等级 | 说明 |
|------|---------|------|
| 本地合成数据生成 | 受信 | 仅使用 numpy seed，无外部依赖 |
| 用户传入 `model_type` / `params` | 不可信 | 必须校验白名单；异常需 safe fallback |
| `api/train.py` HTTP 端点 | 半受信 | Vercel serverless，每个请求独立上下文 |
| `benchmarks/run.py` CLI | 受信 | 内部工具，不处理外部输入 |
| 外部 PyPI 依赖 | 受限 | 仅限 spec/DEPENDENCY_POLICY.md 列出项 |

---

## 2. 攻击面分析

### 2.1 模型类型注入
- **威胁**: 用户 POST `{"model_type": "os.system('rm -rf /')"}` → RCE
- **当前防护**: `model_type` 通过 `if model_type not in MODELS: return error`
- **缓解**: 白名单校验在 `train_model()` 入口强制执行
- **风险等级**: ⚠️ 中（已防护，但建议加入 typed enum）

### 2.2 参数注入 (params dict)
- **威胁**: 超大 `n_estimators=999999` 导致内存耗尽；超深递归栈
- **当前防护**: `max_depth=None` 在 `Tree/RF` 中可能极大
- **缓解**: 无硬性上限；benchmark 有 5min timeout 保护
- **风险等级**: 🟡 低（serverless 内存限制自然防御）

### 2.3 合成数据 DoS
- **威胁**: `generate_dataset(n_samples=10**9)` 撑爆内存
- **当前防护**: `benchmarks/run.py` 固定 `n_samples=500`，用户 CLI 无此参数
- **风险等级**: ✅ 低（CLI 固定参数，不暴露给外部）

### 2.4 Serverless 冷启动
- **威胁**: 依赖体积膨胀 → 冷启动 > 10s → Vercel timeout
- **当前状态**: 估算 < 30MB，测量 < 3s（见 spec/DEPENDENCY_POLICY.md）
- **风险等级**: 🟡 低（需持续监控）

### 2.5 路径遍历（API 输出）
- **威胁**: `save_results(output_path="../../../etc/passwd")` 写任意文件
- **当前防护**: `save_results` 使用固定 `output/` 子目录，不接受外部路径
- **风险等级**: ✅ 低

### 2.6 信息泄露
- **威胁**: 错误信息泄露 server 路径、Python 版本、依赖版本
- **当前状态**: Flask production 模式默认不暴露 stack trace
- **风险等级**: 🟡 低（建议 review api/train.py 错误处理）

---

## 3. 依赖安全

| 依赖 | 已知 CVE | 状态 |
|------|---------|------|
| numpy | CVE-2024-xxxx（参见 nvd.nist.gov） | 建议定期 `pip list --outdated` |
| scikit-learn | sklearn 无已知 RCE 历史 | ✅ 可接受 |
| matplotlib | 历史上无 server-side RCE | ✅ 可接受 |
| flask | 已知的 WSGI 开发模式问题 | ✅ 生产环境 Vercel 隔离 |

**缓解**: `requirements.txt` 已 pin 版本范围；未来可加 `pip-audit` 到 CI。

---

## 4. 部署安全

- **Vercel**: 共享责任模型；平台负责 hypervisor 隔离
- **环境变量**: 无 secret 存储（纯前端/无数据库）
- **CORS**: 若未来开放 API，需限制来源
- **HTTPS**: Vercel 默认强制

---

## 5. 未评估项（本轮标记，待下轮处理）

- [ ] pytest 可以通过 `python3 -m pytest` 任意读文件系统（测试时）
- [ ] `api/train.py` 错误消息是否泄露内部路径（未做 review）
- [ ] 未来若开放文件上传接口，需重新评估路径遍历
- [ ] 依赖传递依赖（transitive deps）的 CVE 监控
