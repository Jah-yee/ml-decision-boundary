# Tree Depth Sensitivity Report — 2026-05-08

**Purpose**: Map Tree(max_depth) accuracy across dataset geometries.

**Total experiments**: 24 | **Passed**: 22

## Accuracy by Dataset × Depth

| Dataset | d=1 | d=2 | d=3 | d=5 | d=10 | d=None | Min depth to threshold |
|---------|-----|-----|-----|-----|------|--------|------------------------|
| circles | 0.6 | 0.65 | 0.7 | 0.74 | 0.68 | 0.66 |
| moons | 0.84 | 0.89 | 0.89 | 0.9 | 0.82 | 0.82 |
| blobs | 0.6 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |
| xor | 0.47 | 0.49 | 0.46 | 0.75 | 0.73 | 0.75 |