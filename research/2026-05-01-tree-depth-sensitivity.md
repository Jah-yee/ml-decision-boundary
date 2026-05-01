# Tree Depth Sensitivity: Key Findings

**日期**: 2026-05-01
**类型**: Research Document
**涉及**: model=Tree, datasets={circles, moons, blobs, xor}, params=max_depth∈{1,2,3,5,10,None}

---

## 核心发现

### 发现1：并非深度越大越好——circles/moons 在 depth=5 达到峰值后下降

| Dataset | d=5 | d=10 | d=None |
|---------|-----|------|--------|
| circles | **0.74** | 0.68 | 0.66 |
| moons | **0.90** | 0.82 | 0.82 |

**原因**：circles 和 moons 数据集有平滑的弧形边界。depth 过大时，树产生过多细碎叶片，对训练数据过度拟合，泛化能力下降。这是一种**反直觉的过拟合现象**。

**建议**：在 REPRODUCE.md 中为 circles/moons 标注推荐 depth 范围（如 depth≤5），避免用户使用默认值（None/unlimited）导致性能下降。

### 发现2：XOR 是唯一对深度饥渴的数据集

| Depth | 1 | 2 | 3 | 5 | 10 | None |
|-------|---|---|---|---|-----|------|
| xor | 0.47 | 0.49 | 0.46 | **0.75** | 0.73 | 0.75 |

- depth=1~3 几乎等于随机猜测（~0.50）
- depth=5 时突然跃升到 0.75（超过 threshold 0.60）
- depth≥5 之后趋于稳定，不再继续提升

**原因**：XOR 需要组合两层轴平行分割才能表达。depth<5 时树的表达能力不足；depth≥5 时树有足够叶片拟合 XOR 结构，但增加深度不再带来额外收益（数据本身有 noise）。

### 发现3：blobs 在 depth=2 就已饱和

| Depth | 1 | 2 | 3-10/None |
|-------|---|---|-----------|
| blobs | 0.60 | **1.00** | 1.00 |

**原因**：blobs 是线性可分的 3 簇数据，两次轴平行分割即可完美分开。额外深度没有意义。

---

## 实证数据矩阵

```
Dataset  │ d=1  │ d=2  │ d=3  │ d=5  │ d=10 │ None │ 推荐depth
---------│------│------│------│------│------│------│-----------
circles  │ 0.60 │ 0.65 │ 0.70 │ 0.74 │ 0.68 │ 0.66 │ 5（峰值）
moons    │ 0.84 │ 0.89 │ 0.89 │ 0.90 │ 0.82 │ 0.82 │ 5（峰值）
blobs    │ 0.60 │ 1.00 │ 1.00 │ 1.00 │ 1.00 │ 1.00 │ 2（饱和）
xor      │ 0.47 │ 0.49 │ 0.46 │ 0.75 │ 0.73 │ 0.75 │ ≥5
```

---

## 可执行建议

### 建议1：为 Tree on circles/moons 添加过拟合警告（高价值）

**现状**：`max_depth=None` 是 benchmark 中 Tree 的默认值，但在 circles/moons 上表现不如 depth=5。

**操作**：在 REPRODUCE.md 添加：
```markdown
## Tree depth 注意事项
- circles/moons: 推荐 max_depth=5，避免使用 None（过拟合）
- xor: 推荐 max_depth≥5
- blobs: max_depth=2 即可饱和，更大无意义
```

### 建议2：benchmark 中 circles/moons 的 Tree 应使用 depth=5 而非 None（高价值）

**现状**：MODELS 配置中 Tree 只有 `max_depth=3` 和 `max_depth=10`，没有 depth=5。

**操作**：在 `benchmarks/run.py` 的 MODELS["Tree"] 列表中，将 `{"max_depth": 10}` 替换为 `{"max_depth": 5}`（更能代表这两类数据的最佳表现）。

### 建议3：depth sweep 报告加入 CI 回归检测（中价值）

**现状**：--depth-sweep 报告已可生成，但未集成到 CI。

**操作**：在 `.github/workflows/benchmarks.yml` 中增加：
```yaml
- name: Tree depth sweep
  run: python3 -m benchmarks --depth-sweep
```

---

## 相关文件

- benchmark JSON: `benchmarks/reports/depth_sweep_2026-05-01.json`
- benchmark MD: `benchmarks/reports/depth_sweep_2026-05-01.md`
- 来源：2026-05-01 晚场 cron 执行

---

## 来源

本发现来自 2026-05-01 晚场（14:02 UTC）深度扫描执行。