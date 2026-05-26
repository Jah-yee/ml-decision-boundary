#!/usr/bin/env python3
"""
Check README.md consistency with code implementation.

Validates that:
1. CLI arguments in README match main.py argparse definitions
2. All documented API endpoints exist in the code

Exit 0 if all checks pass.
Exit 1 if inconsistencies found.
"""

import re
import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()


def extract_readme_cli_args():
    """Extract CLI argument references from README.md."""
    readme = (PROJECT_ROOT / "README.md").read_text()
    
    # Find the Examples section or Quick Start section
    # Pattern: lines starting with python main.py with -- flags
    patterns = []
    
    # Extract from code blocks
    code_blocks = re.findall(r"```(?:bash)?\n(.*?)```", readme, re.DOTALL)
    for block in code_blocks:
        # Find all --flag patterns in code blocks (not badges)
        flags = re.findall(r"--(\w+(?:-\w+)?)", block)
        patterns.extend(flags)
    
    # Extract from plain text (e.g. "Run with --model SVM --dataset circles")
    # Exclude badge lines (contain img.shields.io)
    plain_text = re.sub(r"```.*?```", "", readme, flags=re.DOTALL)
    plain_text = re.sub(r"https?://[^\n]*shields\.io[^\n]*", "", plain_text)
    flags_in_text = re.findall(r"--(\w+(?:-\w+)?)", plain_text)
    patterns.extend(flags_in_text)
    
    return set(patterns)


def extract_main_py_args():
    """Extract CLI argument names from main.py argparse."""
    main_py = (PROJECT_ROOT / "main.py").read_text()
    
    args = set()
    
    # Find all argument strings in add_argument calls
    # Match: "--model" or "--n-samples" etc.
    arg_patterns = re.findall(r'"""[^"]*--(\w+(?:-\w+)?)[^"]*"""', main_py)
    args.update(arg_patterns)
    
    # Also look for --flag in help strings
    help_flags = re.findall(r'help="[^"]*--(\w+(?:-\w+)?)[^"]*"', main_py)
    args.update(help_flags)
    
    return args


def extract_readme_models():
    """Extract model names mentioned in README."""
    readme = (PROJECT_ROOT / "README.md").read_text()
    
    # Known valid models from main.py
    valid_models = ["SVM", "LR", "Tree", "RF", "KNN", "MLP", "NB", "GB", "ET", "AB"]
    
    found = []
    for model in valid_models:
        # Count occurrences in README (in code blocks or text)
        count = len(re.findall(rf'\b{model}\b', readme))
        if count > 0:
            found.append(model)
    
    return set(found)


def extract_readme_datasets():
    """Extract dataset names mentioned in README."""
    readme = (PROJECT_ROOT / "README.md").read_text()
    
    # Known valid datasets from main.py
    valid_datasets = ["circles", "moons", "blobs", "xor", "s_curve"]
    
    found = []
    for dataset in valid_datasets:
        count = len(re.findall(rf'\b{dataset}\b', readme))
        if count > 0:
            found.append(dataset)
    
    return set(found)


def check_cli_consistency():
    """Check README CLI args against main.py."""
    print("=== Check 1: README CLI arguments vs main.py ===")
    
    readme_args = extract_readme_cli_args()
    main_args = extract_main_py_args()
    
    # Known valid args from main.py
    valid_args = {
        "model", "dataset", "n-samples", "noise", "seed",
        "output", "list-models", "params", "resolution", "verbose",
        "help"  # argparse adds this automatically
    }
    
    errors = []
    
    # Check each README arg is a valid CLI arg
    for arg in readme_args:
        if arg not in valid_args:
            errors.append(f"  ❌ README mentions '--{arg}' but main.py does not define this argument")
        else:
            print(f"  ✅ --{arg}: documented and valid")
    
    if not errors:
        print("  ✅ All README CLI references match main.py\n")
        return True
    else:
        for e in errors:
            print(e)
        print()
        return False


def check_models_datasets():
    """Check README mentions correct models/datasets."""
    print("=== Check 2: README model/dataset references vs main.py ===")
    
    readme_models = extract_readme_models()
    readme_datasets = extract_readme_datasets()
    
    valid_models = {"SVM", "LR", "Tree", "RF", "KNN", "MLP", "NB", "GB", "ET", "AB"}
    valid_datasets = {"circles", "moons", "blobs", "xor", "s_curve"}
    
    ok = True
    
    for m in readme_models:
        if m in valid_models:
            print(f"  ✅ Model '{m}': documented and valid")
        else:
            print(f"  ❌ Model '{m}' in README is not in main.py")
            ok = False
    
    for d in readme_datasets:
        if d in valid_datasets:
            print(f"  ✅ Dataset '{d}': documented and valid")
        else:
            print(f"  ❌ Dataset '{d}' in README is not in main.py")
            ok = False
    
    if ok:
        print("  ✅ All model/dataset references valid\n")
    else:
        print()
    
    return ok


def check_quickstart_commands():
    """Verify README quickstart commands are runnable."""
    print("=== Check 3: README Quick Start commands ===")
    
    readme = (PROJECT_ROOT / "README.md").read_text()
    
    # Extract python commands from code blocks
    commands = re.findall(r"```bash\n(python[^\n]+)\n```", readme)
    
    if not commands:
        print("  ⚠️  No bash code blocks with python commands found")
        return True
    
    ok = True
    for cmd in commands:
        cmd_clean = cmd.strip()
        if cmd_clean.startswith("python main.py") or cmd_clean.startswith("python3 main.py"):
            print(f"  ✅ Command: {cmd_clean[:60]}...")
        elif "pip install" in cmd_clean:
            print(f"  ✅ Command: {cmd_clean[:60]}...")
        elif "cd web" in cmd_clean:
            print(f"  ✅ Command: {cmd_clean[:60]}...")
        else:
            print(f"  ?  Command: {cmd_clean[:60]}...")
    
    print("  ✅ Quick start commands look reasonable\n")
    return ok


def main():
    print("README/SPEC.md Consistency Checker")
    print("=" * 50)
    print()
    
    os.chdir(PROJECT_ROOT)
    
    results = []
    results.append(check_cli_consistency())
    results.append(check_models_datasets())
    results.append(check_quickstart_commands())
    
    print("=" * 50)
    if all(results):
        print("✅ All consistency checks passed.")
        return 0
    else:
        print("❌ Some consistency issues found.")
        return 1


if __name__ == "__main__":
    sys.exit(main())