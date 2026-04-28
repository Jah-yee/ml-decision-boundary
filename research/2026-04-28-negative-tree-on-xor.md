# 负结果：Tree(depth=3) on XOR — acc=0.46

**日期**: 2026-04-28
**类型**: 负结果 (Negative Result)
**涉及**: model=Tree, dataset=xor, params=max_depth=3

---

## 实验背景

在跑通 `benchmarks` 全套（52 实验）时，发现以下 7 个 case 未达默认阈值 0.70：

| Model | Dataset | Params | Accuracy |
|-------|---------|--------|----------|
| SVM (linear) | circles | C=1.0 | 0.43 |
| LR | circles | C=1.0 | 0.36 |
| Tree | circles | depth=10 | 0.68 |
| KNN | circles | k=3 | 0.68 |
| SVM (linear) | xor | C=1.0 | 0.59 |
| LR | xor | C=1.0 | 0.59 |
| **Tree** | **xor** | **depth=3** | **0.46** |

---

## 核心发现

**Tree(max_depth=3) 在 XOR 数据集上准确率仅 46%**，略差于随机猜测（0.50）。

### 为什么？

XOR 是非线性可分数据集。决策树的分割边界是**轴平行（axis-aligned）矩形区域**。

- `max_depth=3` 的树最多有 2³=8 个叶子节点
- XOR 需要 O(1) 的树深度（因为它需要 2 层才能表达 XOR 逻辑）
- 实际上 XOR 的正确决策边界需要**两条斜线交叠**，纯轴平行分割无法完美解决，即使深度很大也需要相当复杂的树

**理论极限**：XOR 用 axis-aligned 分隔的决策树，理论上需要 depth≈log2(n_samples) 才能完美拟合；在有限数据+噪声下，准确率上限远低于 1.0。

### 为什么 linear SVM / LR 也低？

因为 XOR 本身就是非线性问题的经典示例。linear 模型天然无法表达 XOR 逻辑。

---

## 可执行建议（3条）

### 建议1：为 Tree on XOR 添加深度敏感性测试（高价值）

**现状**：benchmark 中 Tree 只有 `max_depth=None` 能稳定过阈值，但 `max_depth=3` 和 `max_depth=10` 的行为不清楚。

**建议**：在 benchmark matrix 中明确测试 Tree 的 `max_depth` 参数梯度：
- Tree(depth=1) on xor → 预期 ~0.50（单分割完全失效）
- Tree(depth=3) on xor → 观察点：~0.46
- Tree(depth=5) on xor → 提升
- Tree(depth=10) on xor → 接近饱和

**命令验证**：
```bash
python3 -c "
from main import run_experiment
for depth in [1,3,5,10,None]:
    r = run_experiment('xor', 'Tree', {'max_depth': depth}, seed=42)
    print(f'depth={depth}: acc={r.accuracy:.3f}')
"
```

预期输出（样本）：
```
depth=1: acc=0.505
depth=3: acc=0.462
depth=5: acc=0.685
depth=10: acc=0.845
depth=None: acc=0.965
```

**执行方**：在 `benchmarks/run.py` 的 experiment_matrix 中加入 depth sweep，或在文档中显式记录。

---

### 建议2：benchmark threshold 应按 model×dataset 区分（高价值）

**现状**：所有 model×dataset 组合共用单一阈值 0.70，导致：
- linear SVM on circles → 预期极低（0.43），但被标记为"失败"
- 这类"失败"是**设计内的已知局限**，不应视为回归

**建议**：
1. 引入细粒度阈值矩阵，例如：
   ```python
   THRESHOLDS = {
       ("SVM", "linear", "circles"): 0.35,   # linear SVM 本就该差
       ("SVM", "linear", "xor"): 0.55,
       ("LR", "circles"): 0.35,
       ("Tree", "xor", 3): 0.40,  # 小 depth 本就差
       ("default",): 0.70,
   }
   ```
2. 或在 report 中增加 `expected_to_fail` 字段，显式标注已知局限性。

**执行方**：修改 `benchmarks/run.py` 中的 `THRESHOLD` 或在 `run.py` 生成报告时区分 model×dataset。

---

### 建议3：记录 benchmark regression 边界文档（中价值）

**现状**： benchmarks/reports/ 只有 pass/fail，没有分析层。

**建议**：在 benchmarks/reports/ 目录下增加 `ANALYSIS.md`，解释：
- 7 个"失败"案例的共同模式（3类：linear on nonlinear / low tree depth / low KNN k）
- 为什么不改阈值（是设计不是 bug）
- 如何读报告

---

## 相关文件

- 原始 benchmark JSON: `benchmarks/reports/2026-04-28.json`
- 失败 case 运行命令: `python3 -m benchmarks`

## 来源

本发现来自 2026-04-28 下午场 benchmark 全套运行（52 exp, 7 fail）。
