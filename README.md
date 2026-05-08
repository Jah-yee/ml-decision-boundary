# ML Decision Boundary Visualizer

<div align="center">

<a href="https://vercel.com/new/clone?repository-url=https://github.com/Jah-yee/ml-decision-boundary">
  <img src="https://vercel.com/button" alt="Deploy with Vercel" height="20">
</a>
<img src="https://img.shields.io/badge/Python-3.8+-blue.svg">
<img src="https://img.shields.io/badge/scikit--learn-1.3+-orange.svg">
<img src="https://img.shields.io/badge/Matplotlib-3.7+-green.svg">
<img src="https://img.shields.io/badge/License-MIT-yellow.svg">
<img src="https://img.shields.io/badge/build-passing-green.svg">

</div>

---

## 🎯 What is This?

An interactive machine learning visualization tool for exploring **how different classifiers partition 2D feature space**.

Train real scikit-learn models on synthetic datasets, visualize their decision boundaries, compare accuracy and training time, and see how model geometry changes as hyperparameters vary.

```bash
python main.py
```

Example output:

```text
📊 Dataset: circles
  ✅ SVM C=1.0: acc=0.9200 time=0.0840s
  ✅ RF C=10:   acc=0.9600 time=0.2310s
  ✅ KNN C=N/A: acc=0.9100 time=0.0110s

📊 Dataset: xor
  ✅ SVM C=1.0:  acc=0.7900 time=0.0190s
  ✅ Tree C=10:  acc=1.0000 time=0.0030s
```

![Decision Boundary Grid](docs/grid_example.png)

---

## ✨ Features

### 🔬 Core Visualization

- **6 benchmark model families** — SVM, Logistic Regression, Decision Tree, Random Forest, KNN, and MLP
- **4 synthetic 2D datasets** — Circles, Moons, Blobs, and XOR
- **Decision boundary rendering** — meshgrid prediction + matplotlib contour plots
- **Parameter sweeps** — compare how boundaries change with C, gamma, depth, k, and more
- **Reproducible experiments** — fixed random seeds for deterministic runs

### 📊 Analysis Tools

- **Accuracy heatmap** — best model performance across datasets
- **Training time boxplot** — runtime distribution by model family
- **Best-model grid** — visual comparison of the strongest configuration per dataset
- **Parameter-effect plots** — side-by-side boundary changes for SVM, Tree, and KNN
- **JSON export** — structured experiment results for further analysis

### 🌐 Interactive Web Interface

- Click-to-train interface
- Real sklearn training when the Flask server is running
- Live parameter sliders
- Accuracy and training-time metrics
- Canvas-based decision boundary rendering
- Demo-mode fallback when no backend is available

### 🛠️ Engineering

- Single-command CLI experiment runner
- Local Flask backend for real-time training
- Vercel serverless API endpoints
- Type-annotated experiment result dataclass
- Offline core ML workflow

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/Jah-yee/ml-decision-boundary.git
cd ml-decision-boundary
pip install -r requirements.txt
```

### 2. Run CLI Experiments

```bash
python main.py
```

Generated files are written to `output/`:

```text
output/
├── accuracy_heatmap.png          # Model × dataset accuracy heatmap
├── training_time_boxplot.png     # Training time comparison
├── best_models_grid.png          # Best model per dataset
├── SVM_circles_params.png        # Parameter sweep examples
├── SVM_moons_params.png
├── SVM_xor_params.png
├── Tree_circles_params.png
├── Tree_moons_params.png
├── Tree_xor_params.png
├── KNN_circles_params.png
├── KNN_moons_params.png
├── KNN_xor_params.png
└── experiment_results.json       # Full structured results
```

You can also run:

```bash
bash run.sh
```

---

## 🌐 Interactive Web Interface

### Local Flask Server

Run the local web server for real sklearn training:

```bash
cd web
python server.py
# Open http://localhost:5000
```

Local routes:

```text
GET  /health   # health check
POST /train    # train model and return decision boundary grid
```

The Flask backend trains real scikit-learn models, evaluates accuracy on a holdout split, and returns boundary grid data for the frontend.

### Standalone HTML Demo

You can also open the HTML file directly:

```bash
open web/index.html
```

When no backend is available, the UI falls back to demo mode. This is useful for previewing the interface, but it does not run real ML training.

---

## 🚀 Deploy to Vercel

One-click deploy:

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/Jah-yee/ml-decision-boundary)

Or via CLI:

```bash
npm i -g vercel
vercel
```

Serverless API endpoints:

```text
POST /api/train    # serverless sklearn training endpoint
GET  /api/health   # health check
```

Vercel routing is configured in `vercel.json`.

> Note: The local Flask app uses `/train` and `/health`. The Vercel serverless functions live under `/api/train` and `/api/health`.

---

## 📁 Project Structure

```text
ml-decision-boundary/
├── main.py                 # CLI experiment runner and visualization pipeline
├── requirements.txt        # Python dependencies
├── requirements.lock       # Locked dependency versions, if used
├── run.sh                  # Convenience runner
├── vercel.json             # Vercel routing config
├── api/
│   ├── train.py            # Vercel serverless: POST /api/train
│   └── health.py           # Vercel serverless: GET /api/health
├── web/
│   ├── index.html          # Interactive web UI
│   └── server.py           # Local Flask server for real training
├── output/                 # Generated plots and experiment JSON
├── docs/                   # README screenshots and visual examples
├── tests/                  # Test suite
├── benchmarks/             # Benchmark-related files
├── data/                   # Data or generated artifacts
├── research/               # Notes / research materials
├── spec/                   # Project specs
├── strategy/               # Planning docs
├── CHANGELOG.md
├── REPRODUCE.md
├── SPEC.md
├── THREAT_MODEL.md
├── LICENSE
└── README.md
```

---

## 🎨 Visualizations

| Accuracy Heatmap | Parameter Sweep | Best Models Grid |
|-----------------|-----------------|-----------------|
| ![heatmap](docs/heatmap_example.png) | ![params](docs/param_effect.png) | ![grid](docs/grid_example.png) |

| Dataset | What it Shows |
|---------|---------------|
| **Circles** | Concentric circular regions that require non-linear separation |
| **Moons** | Two interleaving crescent shapes |
| **Blobs** | Gaussian clusters in 2D space |
| **XOR** | Quadrant-based non-linear separation |

---

## 🔬 Models Supported

| Model | Key Parameters | Strengths | Weaknesses |
|-------|----------------|-----------|------------|
| **SVM** | `kernel`, `C`, `gamma` | Strong non-linear boundaries with RBF kernel | Can be slower on large datasets |
| **Logistic Regression** | `C` | Simple, fast, interpretable linear baseline | Struggles with non-linear boundaries |
| **Decision Tree** | `max_depth`, `min_samples_split` | Interpretable, fast, captures sharp regions | Can overfit easily |
| **Random Forest** | `n_estimators`, `max_depth` | Robust ensemble behavior | Less interpretable than a single tree |
| **KNN** | `n_neighbors`, `weights` | Simple, flexible local boundaries | Inference cost grows with dataset size |
| **MLP** | `hidden_layer_sizes`, `alpha` | Learns complex non-linear patterns | Sensitive to tuning and training time |

---

## 📚 Datasets

The project uses generated 2D datasets so decision boundaries can be visualized directly.

| Dataset | Generator | Description |
|---------|-----------|-------------|
| **Circles** | `sklearn.datasets.make_circles` | Concentric circular classes |
| **Moons** | `sklearn.datasets.make_moons` | Interleaving crescent-shaped classes |
| **Blobs** | `sklearn.datasets.make_blobs` | Clustered Gaussian data |
| **XOR** | custom generator | Quadrant-based non-linear pattern |

In the CLI experiment runner, `blobs` is generated with three centers. In the web/API path, the blob dataset is filtered to the first two clusters for a binary interactive demo.

---

## ⚙️ How It Works

The CLI pipeline does the following:

1. Generate a synthetic 2D dataset.
2. Split the data into training and test sets with a 20% holdout test split.
3. Train a classifier with a predefined parameter configuration.
4. Measure training time with `time.perf_counter()`.
5. Evaluate accuracy on the holdout test set.
6. Compute a decision boundary by predicting over a 2D mesh grid.
7. Save visualizations and structured JSON results.

Decision boundary computation:

```text
training data bounds
        ↓
add 0.5-unit padding
        ↓
create meshgrid
        ↓
predict class for every grid point
        ↓
reshape predictions into a 2D surface
        ↓
render contour plot
```

Grid resolution:

| Mode | Grid Resolution |
|------|-----------------|
| CLI matplotlib plots | `200 × 200` |
| Local Flask API | `40 × 40` |
| Vercel serverless API | `40 × 40` |

---

## 📈 Experiment Results

Running:

```bash
python main.py
```

executes the main benchmark suite:

| Metric | Value |
|--------|-------|
| Main CLI benchmark experiments | 72 |
| Model families | 6 |
| Datasets | 4 |
| Parameter configurations per model | 3 |
| Holdout test split | 20% |
| Output format | PNG plots + JSON |

The exact accuracy and timing values can vary by machine and dependency versions. Full reproducible results are saved to:

```text
output/experiment_results.json
```

The JSON includes:

- experiment name
- model parameters
- accuracy
- training time
- model-specific metadata such as support vector count, tree depth, number of trees, and MLP layer count

---

## 🛠️ Customization

### Add a Custom Dataset

Add a generator function and register it inside `generate_dataset()` in `main.py`.

```python
def make_custom_dataset(n, noise, seed):
    from sklearn.datasets import make_classification

    X, y = make_classification(
        n_samples=n,
        n_features=2,
        n_informative=2,
        n_redundant=0,
        n_classes=2,
        random_state=seed,
    )
    return X, y
```

Then add it to the dataset dispatch dictionary:

```python
datasets = {
    "circles": lambda: make_circles(n_samples, noise, seed),
    "moons": lambda: make_moons(n_samples, noise, seed),
    "blobs": lambda: make_blobs(n_samples, seed),
    "xor": lambda: make_xor(n_samples, noise, seed),
    "custom": lambda: make_custom_dataset(n_samples, noise, seed),
}
```

### Run a Specific Experiment

```python
from main import generate_dataset, train_model

X, y = generate_dataset("circles", n_samples=500)

model, train_time = train_model(
    "SVM",
    {"kernel": "rbf", "C": 10.0, "gamma": "scale"},
    X,
    y,
)

accuracy = model.score(X, y)

print(f"Accuracy: {accuracy:.4f}")
print(f"Train time: {train_time:.4f}s")
```

### Add a New Model

Add the classifier to the model factory in `train_model()`:

```python
from sklearn.ensemble import GradientBoostingClassifier

models = {
    "SVM": lambda: SVC(**params, random_state=42),
    "LR": lambda: LogisticRegression(**params, random_state=42, max_iter=1000),
    "Tree": lambda: DecisionTreeClassifier(**params, random_state=42),
    "RF": lambda: RandomForestClassifier(**params, random_state=42),
    "KNN": lambda: KNeighborsClassifier(**params),
    "MLP": lambda: MLPClassifier(**params, random_state=42, max_iter=2000),
    "GradientBoosting": lambda: GradientBoostingClassifier(**params, random_state=42),
}
```

To include it in the full benchmark suite, also add parameter configurations in `run_all_experiments()` and update the comparison plot model list if needed.

---

## 📦 Requirements

Core:

```text
numpy>=1.24.0
matplotlib>=3.7.0
scikit-learn>=1.3.0
```

Web/dev:

```text
flask>=3.0.0
pytest>=7.0.0
```

Install everything with:

```bash
pip install -r requirements.txt
```

---

## 🧪 Testing

Run tests with:

```bash
pytest
```

---

## 🎓 Educational Use

This project is useful for:

- **ML courses** — visual demonstrations of decision boundaries
- **Model intuition** — compare linear, tree-based, kernel, neighbor, and neural approaches
- **Overfitting demos** — watch deep trees create sharp, fragmented regions
- **Hyperparameter learning** — see how C, gamma, depth, k, and alpha affect the surface
- **Model selection** — compare accuracy, geometry, and training cost on the same dataset
- **Portfolio projects** — practical ML, visualization, and lightweight web deployment in one repo

---

## 📝 License

MIT License — free to use, modify, and distribute. See [LICENSE](LICENSE).

---

<div align="center">

Built with 🧠 for ML visualization

*Questions? Open an issue on GitHub.*

</div>
