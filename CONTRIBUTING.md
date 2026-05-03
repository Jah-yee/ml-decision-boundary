# Contributing to ml-decision-boundary

## Quick Start

```bash
# Clone and setup
git clone https://github.com/Jah-yee/ml-decision-boundary.git
cd ml-decision-boundary
pip install -r requirements.txt

# Run the full suite
python3 main.py

# Run benchmarks
python3 -m benchmarks --quick    # smoke test
python3 -m benchmarks             # full suite
python3 -m benchmarks --depth-sweep  # tree depth matrix

# Run tests
pytest tests/ -q
```

## Quality Gates

| Layer | Command | Required |
|-------|---------|----------|
| P0 | `python3 -m compileall . && python3 -c "import main; print('OK')"` | ✅ All commits |
| P1 | `pytest tests/ -q` | ✅ All PRs |
| P2 | `python3 -m benchmarks --quick` | If changing ML code |

## Branch & PR Workflow

1. Create branch: `git checkout -b feature/your-feature-name`
2. Make changes, commit with `Jah-yee <jydu_seven@outlook.com>` author
3. Ensure P0/P1 pass locally
4. Push and open PR with description template
5. PR merged after review approval

## What to Contribute

### High Priority
- New model support (add to `MODELS` dict in `benchmarks/run.py`)
- New dataset support (add to `DATASETS` list + `generate_dataset` in `main.py`)
- Missing test coverage for untested code paths

### Medium Priority
- Documentation improvements
- CLI/UX enhancements
- Benchmark report enhancements

### Low Priority
- Performance optimizations (profile first)
- Additional visualization types

## Coding Style

- Docstrings for all public functions
- Type hints for function signatures
- No `except:` (catch specific exceptions)
- No `traceback.format_exc()` in error responses (security)

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): subject

feat(api): add health check endpoint
fix(cli): correct --help output for benchmarks
docs(readme): update quick start commands
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

## Reporting Issues

- Check existing issues before creating new ones
- Include: Python version, OS, error traceback, command that failed
- For ML issues: include dataset, model, params, and accuracy if applicable
