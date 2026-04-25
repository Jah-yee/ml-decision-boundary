# REPRODUCE.md — 复现指南

**版本**: v0.1 (Created 2026-04-26)

---

## 快速复现

### 环境要求
- Python 3.8+
- pip

### 安装
```bash
git clone https://github.com/Jah-yee/ml-decision-boundary.git
cd ml-decision-boundary
pip install -r requirements.txt
```

### P0 验证（每次 commit 前必跑）
```bash
python3 -m compileall .
python3 -c "import main; print('main import OK')"
python3 -c "from api import train, health; print('api import OK')"
```

### P2 验证（完整实验）
```bash
python3 main.py
# 预期输出: output/experiment_results.json + 多张 PNG
```

### P3 验证（Web 界面）
```bash
cd web
python3 server.py
# 预期: http://localhost:5000 可访问，/api/health 返回 200
```

---

## 依赖版本（已锁）
```
flask>=3.0.0
numpy>=1.24.0
matplotlib>=3.7.0
scikit-learn>=1.3.0
```
