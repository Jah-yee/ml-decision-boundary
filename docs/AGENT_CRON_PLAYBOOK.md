# AGENT_CRON_PLAYBOOK.md — ml-decision-boundary 深度维护版

> **版本**: v3 (深度维护版)
> **核心改变**: 从「每天两次快速闭环」改为「每天1-2次深度维护」
> **发布时间**: 2026-05-01

---

## 🎯 核心理念：深度刷 (Deep Maintenance)

### 旧模式的问题
| 问题 | 表现 |
|------|------|
| 唯一主题 | 每轮只做一个PR，遇到困难就跳过 |
| 时间太短 | 60秒/主题，无法深入 |
| research必做 | 每轮写研究文档，消耗大量时间但产出有限 |
| 5分叉虚设 | 每轮选一个，但没时间深入 |
| PR闭环压力 | 为了闭环而做小PR，不是为了价值 |

### 新模式：深度刷
```
每次 cron = 一次有意义的维护日
不是"完成任务"，是"真正改善项目"
2-3个相关commit > 1个孤立小PR
```

---

## ⏱️ 时间预算（核心改变）

### 之前
```
每天两次，每次30分钟
= 时间稀缺，每轮只能做一点点
```

### 现在
```
timeoutSeconds: 7200 (2小时)
每次cron = 深度工作单元

时间分配：
- 前30分钟：扫描、发现问题、规划
- 中间90分钟：执行核心工作
- 最后30分钟：验证、文档、收尾
```

### 为什么这样分配
- 真正有价值的维护需要深度，不是快速检查
- 2-3个相关commit比1个孤立PR更有意义
- 写研究文档不是每轮必做，是有真正发现时才写

---

## 📋 深度扫描：发现真正的问题

### 之前
```
只读 NEXT_ROUND_THEME.md 的待办列表
= 被动响应，不是主动发现
```

### 现在：主动扫描3个层面

#### 层面1：代码深处（30分钟）
```bash
# 1. 语法/类型问题
python3 -m py_compile **/*.py 2>&1 | head -50

# 2. 缺失的边界处理
grep -r "except:" --include="*.py" . | grep -v test | head -20
grep -r "raise NotImplementedError" --include="*.py" . | head -20

# 3. 测试盲区
pytest --collect-only 2>&1 | tail -20
find tests/ -name "*.py" -empty | head -10

# 4. 类型注解缺失（如果项目用类型注解）
grep -L "-> " $(find . -name "*.py" -not -path "*/test*") | head -10

# 5. 潜在bug模式
grep -rn "if True:" --include="*.py" . | head -10
grep -rn "pass  # TODO" --include="*.py" . | head -10
grep -rn "\.format(" --include="*.py" . | head -10  # f-string迁移机会
```

#### 层面2：文档与契约（15分钟）
```bash
# 1. docstring缺失
grep -rL '"""' --include="*.py" $(find . -name "*.py" -not -path "*/test*" -not -path "*/__pycache__/*") | head -10

# 2. README过时
head -20 README.md  # 检查是否有过时信息

# 3. spec与实现不一致
diff <(grep -h "def \|class " spec/*.md 2>/dev/null | sed 's/.*def \|class //;s/(.*//') \
     <(grep -h "def \|class " api/ main.py 2>/dev/null | sed 's/def \|class //;s/(.*//') 2>/dev/null | head -20

# 4. CHANGELOG vs 实际commit
git log --oneline -20 | head -10
grep -A2 "Unreleased" CHANGELOG.md | head -10
```

#### 层面3：治理与依赖（15分钟）
```bash
# 1. 依赖安全
pip list --outdated 2>/dev/null | head -20
grep -r "require" requirements.txt | head -10

# 2. CI/CD健康
gh run list --limit 10 2>/dev/null | head -10

# 3. issue清理
gh issue list --state open --limit 20 2>/dev/null | head -20
gh issue list --state closed --since "2026-01-01" 2>/dev/null | tail -10

# 4. 长期未动的文件
find . -name "*.py" -mtime +30 -not -path "*/test*" -not -path "*/__pycache__/*" | head -10
```

### 输出：问题清单
```
深度扫描发现（{timestamp}）：

【高优先级】
1. [文件] — [问题描述] — 估计修复时间
2. ...

【中优先级】
1. ...
【低优先级】
1. ...
```

---

## 🔄 工作模式：2种深度会话

### 会话A：专项深挖（主模式）

当扫描发现明确的问题域时，专注深挖：

```
扫描 → 发现问题域 → 规划3个相关commit → 执行 → 验证
```

**特征**：
- 3个相关commit（不是3个独立PR）
- 围绕同一个问题域（如"API错误处理全面review"）
- commit之间有依赖关系
- 最终1个PR包含3个commit

**举例：API错误处理深挖**
```
commit 1: api/train.py — 移除 traceback.format_exc()（已完成）
commit 2: api/train.py — 统一错误响应格式
commit 3: api/train.py — 添加错误类型枚举 + 文档更新
→ 1个PR，3个相关commit
```

### 会话B：多线并行（次模式）

当多个不相关的问题同时存在，且都重要时：

```
扫描 → 发现多个问题域 → 按重要性排序 → 选择2个 → 并行执行
```

**特征**：
- 2个独立问题域
- 2个独立PR
- 可以并行思考，但不能并行写代码
- 需要良好的上下文切换

**时间分配**：
```
问题域A：60分钟
问题域B：60分钟
验证+收尾：30分钟
缓冲：30分钟
```

---

## 🎯 5分叉深度执行

### 之前
```
每轮选1个分叉，说"为什么选这个" + "为什么不选其他"
= 形式大于实质
```

### 现在：每个分叉都有挖掘空间

#### 分叉1：Harness/可复现实验平台化
**可挖掘内容**：
- benchmark报告自动化（JSON schema → HTML报告）
- 回归阈值可视化（阈值变化趋势图）
- 实验配置版本化（.benchmarks/目录）
- 并行实验支持（多进程跑实验）
- CI中集成smoke benchmark

**每轮可选动作**：
- [ ] 新增1个benchmark报告生成器
- [ ] 优化benchmark输出格式
- [ ] 添加新的回归测试用例
- [ ] 改善benchmark可复现性（固定种子文档）

#### 分叉2：模型与数据科学深化
**可挖掘内容**：
- Tree depth敏感性矩阵（已计划但未做）
- 模型超参数调优实验
- 失败模式分析（research文档）
- 新数据集支持（更多合成数据场景）
- 模型可解释性改进

**每轮可选动作**：
- [ ] 跑一次完整benchmark矩阵
- [ ] 分析失败实验，写research文档
- [ ] 新增一个模型评估协议
- [ ] 优化训练收敛速度

#### 分叉3：产品交互与契约
**可挖掘内容**：
- API错误信息标准化
- CLI输出格式优化
- Web界面改进
- 文档完整性检查
- 示例代码更新

**每轮可选动作**：
- [ ] API错误响应格式统一
- [ ] CLI帮助文本改进
- [ ] README增加新使用场景
- [ ] 补充API使用示例

#### 分叉4：部署与运行时工程
**可挖掘内容**：
- 冷启动优化（减少依赖体积）
- 内存分析（找出内存占用来源）
- 并发限制（serverless并发数）
- 健康检查端点增强
- 环境变量校验

**每轮可选动作**：
- [ ] 依赖裁剪（移除未用import）
- [ ] 冷启动时间测量
- [ ] 内存profiling
- [ ] 添加健康检查详细指标

#### 分叉5：治理与社区工程
**可挖掘内容**：
- CONTRIBUTING.md完善
- CODEOWNERS配置
- GitHub Actions优化
- release流程自动化
- 安全漏洞响应流程

**每轮可选动作**：
- [ ] 完善CONTRIBUTING.md
- [ ] 添加CODEOWNERS
- [ ] GitHub Actions缓存优化
- [ ] 安全漏洞报告流程
- [ ] 依赖审查（pip-audit集成）

---

## 📊 交付物标准（精简版）

### 之前（太多必做）
```
A) strategy/runs/YYYY-MM-DD-HHMM.md（必做）
B) research/YYYY-MM-DD-<slug>.md（必做）← 负担
C) CHANGELOG.md Unreleased（必做）
+ 7.2轮换（至少2项产生diff）
+ 7.3额外挖掘资产（每3轮检查）
= 每轮写4-5个文档，太重
```

### 现在（精简版）
```
【每轮必须】
1. strategy/runs/YYYY-MM-DD-HHMM.md（完整流水账）
2. CHANGELOG.md Unreleased（至少一条）
3. P0/P1/P2通过层级验证

【轮换（每3轮至少覆盖2个）】
- research文档（有真正发现时才写，不硬造）
- spec拆分/更新
- benchmark报告
- phases.md更新
- DEPENDENCY_POLICY.md审查
```

### research文档降级为"有发现才写"
```
之前：每轮必须写research文档
→ 结果：为了写而写，产出质量低

现在：有真正的新发现才写
标准：
  - 发现了新的失败模式（实验验证）
  - 发现了一个重要的设计问题
  - 发现了一个重要的技术债务
  - 不确定=先不做，等信息充分
```

---

## 🔧 七步闭环：深度版

### (a) 获取信息 → 深度扫描
```
之前：读几个文件，快速判断
现在：
  1. git fetch + status
  2. 运行深度扫描（见"深度扫描"章节）
  3. 读NEXT_ROUND_THEME + THREAT_MODEL
  4. 扫描research/目录，看是否有未完成的发现
  5. 扫描docs/和spec/目录，看是否有不一致
  输出：问题清单（高/中/低优先级）
```

### (b) 分析拆解 → 多问题规划
```
之前：选"今日唯一主题"
现在：
  1. 从问题清单中选2-3个相关问题
  2. 确定是"专项深挖"还是"多线并行"
  3. 规划每个问题的commit结构
  4. 预估时间（每个问题 ≤ 60分钟）
  5. 选择主攻分叉 + 说明
  输出：
    - 问题1：X（主攻）— 分叉#n — 3个commit
    - 问题2：Y（可选）— 分叉#m — 2个commit
    - 不做：Z（原因）
```

### (c) 行动方案 → 详细规划
```
之前：简单列文件清单
现在：
  1. 每个问题创建独立分支
  2. 列每个commit的：
     - 文件列表
     - 预期diff行数
     - 验证命令
  3. 确定并行/串行执行顺序
  4. 回滚策略（每个问题）
  输出：详细的执行计划
```

### (d) 执行 → 深度编码
```
之前：快速改完就提交
现在：
  1. 每个commit：
     - 先想后写（karpathy-claude.md原则）
     - 写完自review（diff够小吗？有无副作用？）
     - 运行验证命令
  2. 如果发现新问题：
     - 评估是否在scope
     - 小问题：立即修
     - 大问题：记录，下轮做
  3. 保持工作区干净（每完成一个commit就stage）
  输出：多个staged commits
```

### (e) 提交前核查 → 多层验证
```
之前：只过Golden Rule
现在：
  1. P0: compileall + import smoke
  2. P1: pytest（确保不破坏现有功能）
  3. P2: benchmark smoke（如果改了ML路径）
  4. 5+3检查：
     - [ ] diff行数合理（≤200行/问题）
     - [ ] 无意外改动
     - [ ] commit message清晰
     - [ ] author正确
     - [ ] 无秘密泄露
     - [ ] 测试覆盖充分（改了代码就有测试吗？）
     - [ ] 文档更新（改了公开API/行为就要更新文档）
     - [ ] CHANGELOG条目
  5. 如果是多个commit：确认每个commit独立可理解
```

### (f) 集成发送 → 多PR策略
```
之前：1个PR就结束
现在：
  1. 如果是"专项深挖"（3个相关commit）：
     → 1个PR，squash merge或regular merge都可以
  2. 如果是"多线并行"（2个独立PR）：
     → 按优先级顺序创建PR
     → 每个PR包含1-2个commit
  3. PR描述要包含：
     - 解决的问题
     - 改动范围
     - 通过层级状态
     - 测试结果
  4. 如果有对应的外部issue：关联
```

### (g) 发送后核查 → 完整确认
```
之前：只确认PR创建
现在：
  1. git status干净
  2. git log确认commit正确
  3. gh pr list确认所有PR创建
  4. gh run list看CI状态（如果配置了）
  5. 如果CI失败：
     - 分析失败原因
     - 决定是立即修还是下轮
  6. 更新CHANGELOG Unreleased
  7. 更新NEXT_ROUND_THEME（如果需要）
```

---

## 📐 会话类型决策树

```
开始扫描
    ↓
发现N个问题
    ↓
N >= 2 且 问题相关？
    ↓
是 → 专项深挖模式（1个PR，3个commit）
    ↓
N >= 2 且 问题独立？
    ↓
是 → 多线并行模式（2个PR）
    ↓
N == 1 且 问题复杂（需要多个commit才能完整修复）？
    ↓
是 → 专项深挖模式（1个PR，2-3个commit）
    ↓
N == 1 且 问题简单（一个commit就够）？
    ↓
是 → 快速闭环模式（1个PR，1个commit）
```

---

## ⏱️ 时间分配指南

| 会话类型 | 总时间 | 扫描 | 规划 | 执行 | 验证 |
|---------|--------|------|------|------|------|
| 专项深挖 | 120分钟 | 20分钟 | 15分钟 | 60分钟 | 25分钟 |
| 多线并行 | 180分钟 | 20分钟 | 15分钟 | 120分钟 | 25分钟 |
| 快速闭环 | 60分钟 | 10分钟 | 5分钟 | 30分钟 | 15分钟 |

---

## 📋 报告格式（精简版）

### 之前（太长）
```
每轮写5-6页文档，包括：
- 现状快照12条
- 5分叉表格
- ML动作详细描述
- 文档轮换2项
- 7步闭环每步都写
- 通过层级表格
- PR收尾评估
= 文档负担重，执行时间少
```

### 现在（精简版）
```
## 本轮执行摘要 — {timestamp}

### 深度扫描发现
- 高优先级：{n}个
- 中优先级：{n}个
- 低优先级：{n}个

### 本轮工作（{n}个问题，{m}个commit）
1. **问题域X**（分叉#n）
   - commit 1: {描述}
   - commit 2: {描述}
   - commit 3: {描述}
   - PR: {链接}

2. **问题域Y**（分叉#m）[可选]
   - commit 1: {描述}
   - PR: {链接}

### 通过层级
- P0: {pass/fail}
- P1: {pass/fail} ({n}个测试)
- P2: {pass/fail} ({benchmark结果})

### 本轮完成
- [x] {交付1}
- [x] {交付2}

### 下轮待办
- [ ] {待办1}（来源：{本轮发现/上轮遗留}）
- [ ] {待办2}（来源：{}）

### 风险
- {无/有：描述}
```

---

## 🔄 与现有cron任务集成

### 更新 cron message
```json
{
  "message": "你是 ml-decision-boundary 的 Owner 代理。\n\n【深度维护模式】\n本轮使用深度扫描 + 多commit工作流。\ntimeoutSeconds: 7200（2小时）。\n\n授权规范（必须先读）：\n/home/ubuntu/.openclaw/workspace-taizi/ml-decision-boundary/docs/AGENT_CRON_PLAYBOOK.md\n\n本轮主题入口（读完 playbook 后立刻读）：\n/home/ubuntu/.openclaw/workspace-taizi/ml-decision-boundary/strategy/NEXT_ROUND_THEME.md\n\n工作目录：\n/home/ubuntu/.openclaw/workspace-taizi/ml-decision-boundary\n\n从 playbook 的「开始口令」进入；严格完成 playbook 规定的交付物与验收层级。",
  "timeoutSeconds": 7200
}
```

---

## 📝 实施过渡

### 第一轮（立即）
1. 更新 cron message 的 timeoutSeconds 到 7200
2. 应用本 playbook 的"深度扫描"和"多commit"逻辑
3. 保持现有的 strategy/runs 格式（可以精简）
4. 观察2-3轮的效果

### 第二轮（3-5轮后）
1. 根据实际执行情况调整时间分配
2. 精简必做文档列表
3. 固化"会话类型决策树"的使用

### 第三轮（10轮后）
1. 评估是否需要进一步调整
2. 可能的优化方向：
   - 自动化深度扫描脚本
   - 问题优先级排序算法
   - 多PR并行创建的CI支持

---

## 🎯 成功标准

### 之前
```
每轮1个PR就算成功
= 容易达到，但产出有限
```

### 现在
```
每轮产出评估（每10轮评估一次）：
- 平均commit数：≥2
- 真正解决问题的比例：≥80%
- 文档质量（有无硬造）：≥90%
- P0/P1通过率：100%
- P2通过率（如果适用）：≥90%
```

---

**版本历史**：
- v1: 初始版（快速闭环）
- v2: 增加七步闭环
- v3: 深度维护版（多commit + 深度扫描 + 精简文档）
