# ML Decision Boundary Visualizer

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![scikit-learn](https://img.shields.io/badge/scikit--learn-1.3+-orange.svg)
![Matplotlib](https://img.shields.io/badge/Matplotlib-3.7+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

**Interactive visualization of how machine learning models partition feature space**

[Live Demo](https://ml-decision-boundary.vercel.app) · [Quick Start](#quick-start) · [Documentation](#features)

</div>

---

## 🎯 What is This?

A comprehensive machine learning visualization tool that shows **how different ML models draw decision boundaries** in 2D feature space. Perfect for understanding:

- How SVM, Decision Trees, Neural Networks etc. partition space differently
- Effect of hyperparameters on model behavior  
- Model selection and comparison

![Decision Boundary](docs/demo.png)

## ✨ Features

### Core Visualization
- **8+ ML Models**: SVM, Logistic Regression, Decision Tree, Random Forest, KNN, Neural Network, Naive Bayes
- **4 Synthetic Datasets**: Circles, Moons, Blobs, XOR
- **Real-time Parameter Tuning**: See how C, gamma, depth, k-neighbors affect boundaries

### Analysis Tools
- **Accuracy Heatmap**: Model × Dataset performance comparison
- **Training Time Analysis**: Box plot comparison across model types
- **Parameter Sweep**: Visualize parameter effect on model behavior
- **Export Results**: JSON output for further analysis

### Interactive Web Interface
- Click-to-train interface
- Live visualization updates
- Performance metrics dashboard
- Model comparison charts

## 🚀 Quick Start

### Option 1: Python CLI

```bash
# Clone
git clone https://github.com/yourusername/ml-decision-boundary.git
cd ml-decision-boundary

# Install dependencies
pip install -r requirements.txt

# Run experiments
python main.py

# Results saved to output/
```

### Option 2: Web Interface

```bash
# Open in browser
open web/index.html

# Or serve locally
python -m http.server 8000 --directory web
```

### Option 3: Interactive Mode

```bash
python main.py --interactive
```

## 📊 Example Output

```
🎯 ML Decision Boundary Visualizer
====================================

📊 Dataset: circles
  ✅ SVM C=1.0: acc=0.9200 time=0.0845s
  ✅ SVM C=10.0: acc=0.9350 time=0.0892s
  ✅ LR C=1.0: acc=0.8850 time=0.0123s
  ...

📊 Dataset: moons
  ✅ SVM C=1.0: acc=0.9100 time=0.0765s
  ...

📈 Generating plots...
📈 Saved: output/accuracy_heatmap.png
📈 Saved: output/training_time_boxplot.png
📈 Saved: output/best_models_grid.png
```

## 📁 Project Structure

```
ml-decision-boundary/
├── main.py              # Core ML experiments
├── web/
│   └── index.html       # Interactive web interface
├── output/
│   ├── accuracy_heatmap.png
│   ├── training_time_boxplot.png
│   ├── best_models_grid.png
│   └── experiment_results.json
├── docs/
│   └── demo.png
├── requirements.txt
└── README.md
```

## 🎨 Visualizations

| Heatmap | Parameter Effect | Model Grid |
|---------|------------------|------------|
| ![heatmap](docs/heatmap_example.png) | ![params](docs/param_effect.png) | ![grid](docs/grid_example.png) |

## 🔬 Models Supported

| Model | Parameters Explored | Best For |
|-------|---------------------|----------|
| **SVM** | kernel, C, gamma | Non-linear separation |
| **Logistic Regression** | C (regularization) | Linear boundaries, probabilities |
| **Decision Tree** | max_depth, min_samples | Interpretable rules |
| **Random Forest** | n_estimators, max_depth | Ensemble accuracy |
| **KNN** | n_neighbors | Instance-based learning |
| **MLP** | hidden_layer_sizes, alpha | Complex patterns |

## 📈 Datasets

| Dataset | Description | Difficulty |
|---------|-------------|------------|
| **Circles** | Two concentric circles | ⭐⭐ |
| **Moons** | Two interleaving moons | ⭐⭐⭐ |
| **Blobs** | Three Gaussian clusters | ⭐ |
| **XOR** | Classic XOR pattern | ⭐⭐⭐⭐ |

## 🛠️ Customization

### Add Custom Dataset

```python
def my_dataset():
    X = np.random.randn(500, 2)
    y = ((X[:, 0]**2 + X[:, 1]**2) < 0.5).astype(int)
    return X, y

# Add to generate_dataset() function
```

### Add Custom Model

```python
# In train_model() function
models = {
    # ... existing models ...
    "MyModel": lambda: MyModelClassifier(**params)
}
```

## 📦 Requirements

```
numpy>=1.24.0
matplotlib>=3.7.0
scikit-learn>=1.3.0
```

## 🎓 Educational Use

This tool is perfect for:
- ML course demonstrations
- Understanding model behavior
- Hyperparameter intuition building
- Model selection decisions

## 📝 License

MIT License - See [LICENSE](LICENSE) for details.

---

<div align="center">

Made with 🧠 for ML visualization

</div>