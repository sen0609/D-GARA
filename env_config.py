"""
Path Configuration Module

This module manages all path configurations for the D-GARA project.
It dynamically calculates the project root directory and defines paths
for all major components including logs, ReactBench, AgentFramework,
and SuccessValidator directories.

All paths are defined relative to the project root to ensure consistency
across different environments.
"""

from pathlib import Path

# --- Core: Dynamically calculate project root directory ---
# Path(__file__) points to the current file (path_config.py)
# .resolve() gets its absolute path
# .parent gets its parent directory (our project root directory)
PROJECT_ROOT = Path(__file__).resolve().parent

# --- Now define all other paths based on the root directory ---

# Log directory
LOG_FINAL_DIR = PROJECT_ROOT / "LOGFINAL"

# ReactBench related paths
REACTBENCH_DIR = PROJECT_ROOT / "ReactBench"
RULES_YAML_PATH = REACTBENCH_DIR / "rules.yaml"
INTERFERENCE_LIB_YAML_PATH = REACTBENCH_DIR / "interference_library.yaml"

# AgentFramework directory (if needed)
AGENT_FRAMEWORK_DIR = PROJECT_ROOT / "AgentFramework"

# SuccessValidator related paths
SUCCESS_VALIDATOR_DIR = PROJECT_ROOT / "SuccessValidator"
SUCCESS_CONDITIONS_YAML_PATH = SUCCESS_VALIDATOR_DIR / "success_conditions.yaml"

# Task definition file
TASKS_JSON_PATH = PROJECT_ROOT / "D-GARA-152.json"

# Default screen dimensions for device automation
RESOLUTION_WIDTH = 1440
RESOLUTION_HEIGHT = 2560

# --- Verify paths are correct (optional) ---
if __name__ == '__main__':
    print(f"✅ Path configuration loaded successfully!")
    print(f"   Project root directory: {PROJECT_ROOT}")
    print(f"   Task JSON file path: {TASKS_JSON_PATH}")
    print(f"   Success conditions YAML path: {SUCCESS_CONDITIONS_YAML_PATH}")