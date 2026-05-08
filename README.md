# Decision boundary visualization

A tool for visualizing how machine learning classifiers partition two-dimensional feature space. Train models on synthetic datasets and render their decision boundaries to understand geometric properties of different algorithms.

```bash
python main.py
```

## Overview

This implementation provides decision boundary visualization for six classification algorithms across four synthetic datasets. Each experiment produces accuracy metrics, timing data, and spatial renderings of the learned decision surfaces.

The tool generates comparative visualizations showing model behavior under parameter variation. All experiments use deterministic seeding for reproducibility.

## Supported models

- Support Vector Machine (kernel, C, gamma)
- Logistic Regression (C)
- Decision Tree (max_depth, min_samples)
- Random Forest (n_estimators, max_depth)
- K-Nearest Neighbors (n_neighbors, weights)
- Multi-layer Perceptron (hidden_layer_sizes, alpha)

## Datasets

Four synthetic binary classification problems from sklearn.datasets:

- Circles: Concentric circular decision boundary
- Moons: Two interleaving crescents
- Blobs: Linearly separable clusters
- XOR: Four quadrants requiring non-linear separation

## Installation

```bash
git clone https://github.com/Jah-yee/ml-decision-boundary.git
cd ml-decision-boundary
pip install -r requirements.txt
```

Requirements: numpy, matplotlib, scikit-learn (see requirements.txt for versions)

## Usage

### Command line interface

Run the full experiment suite:

```bash
python main.py
```

Output directory structure:

```
output/
├── accuracy_heatmap.png          # Model vs dataset accuracy matrix
├── training_time_boxplot.png     # Training time distributions
├── best_models_grid.png          # Optimal configuration per dataset
├── SVM_circles_params.png        # Parameter sweep visualizations
├── Tree_xor_params.png
└── experiment_results.json       # Structured results data
```

### Web interface

Local Flask server with real-time model training:

```bash
cd web
python server.py
# Navigate to http://localhost:5000
```

The server executes sklearn training on POST requests to `/api/train` and returns decision boundary coordinates.

Static demo (no ML computation):

```bash
open web/index.html
```

### Deployment

Vercel serverless deployment via `/api/train` and `/api/health` endpoints:

```bash
vercel deploy
```

Configuration in `vercel.json`. The serverless functions execute sklearn training with a 10-second timeout.

## Project structure

```
ml-decision-boundary/
├── main.py                    # Experiment runner and CLI entry point
├── requirements.txt           # Dependencies
├── api/
│   ├── train.py              # Vercel serverless: POST /api/train
│   └── health.py             # Vercel serverless: GET /api/health
├── web/
│   ├── index.html            # Interactive interface
│   └── server.py             # Flask development server
├── output/                   # Generated visualizations and data
└── docs/                     # Reference images
```

## Implementation details

Decision boundaries are computed using meshgrid evaluation at 200x200 resolution. The mesh spans training data bounds with 0.5-unit padding. Models predict on flattened grid coordinates, results reshape to 2D for contour plotting.

Training uses sklearn defaults with explicit random_state seeding. Timing measured via time.perf_counter() surrounding fit() calls. Accuracy computed on 20% holdout test sets.

Parameter sweeps iterate over predefined configurations. For each, the tool trains the model, computes accuracy, extracts model-specific metadata (support vector count, tree depth, etc.), and stores structured results.

## Customization

Add a dataset:

```python
def custom_dataset():
    from sklearn.datasets import make_classification
    X, y = make_classification(
        n_samples=500, n_features=2, 
        n_informative=2, n_redundant=0,
        n_classes=2, random_state=42
    )
    return X, y

# Update generate_dataset() in main.py
```

Run single experiment:

```python
from main import train_model, generate_dataset

X, y = generate_dataset("circles", n_samples=500)
model, train_time = train_model("SVM", {"C": 10.0, "gamma": "scale"}, X, y)
accuracy = model.score(X, y)
```

Extend model set:

```python
from sklearn.ensemble import GradientBoostingClassifier

# Add to models dict in train_model()
"GradientBoosting": lambda: GradientBoostingClassifier(**params)
```

## Results

Running `python main.py` executes 48 experiments (6 models × 4 datasets × 2-3 parameter configurations each).

Typical outcomes:
- XOR + Decision Tree (depth=15): 100% accuracy
- Circles + SVM (RBF kernel): ~95% accuracy
- Fastest: KNN (~0.001s)
- Slowest: MLP (~0.4s)

Full results stored in `output/experiment_results.json` with accuracy, timing, and model metadata.

## Educational applications

This tool demonstrates:
- Decision boundary geometry for different model classes
- Overfitting behavior (deep trees memorizing training data)
- Hyperparameter effects on learned surfaces
- Model selection based on problem structure
- Trade-offs between accuracy and computational cost

Useful for teaching classification fundamentals, parameter tuning intuition, and visual debugging of model behavior.

## License

MIT License. See LICENSE file.

Copyright (c) 2024
