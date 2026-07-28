"""Add current AI and Python ecosystem skills to the matching taxonomy.

This is a one-time, idempotent data migration. It intentionally adds only
conservative implication edges: a Python package implies Python, and an
extension package implies its direct framework dependency.

Run from the repository root:
    python3 app/data/add_ai_python_skills.py
    python3 app/data/close_implies.py
"""

from __future__ import annotations

import json
from pathlib import Path


DATA_DIR = Path(__file__).parent
SKILL_DATA_FILE = DATA_DIR / "skill_data.json"
IMPLIES_FILE = DATA_DIR / "skill_implies.json"

# Platforms and protocols do not imply Python. The remaining entries are
# current Python-first libraries and tooling across AI, MLOps, and data work.
CANONICAL_SKILLS: set[str] = {
    "accelerate",
    "ag2",
    "anthropic",
    "bentoml",
    "bitsandbytes",
    "catboost",
    "chromadb",
    "crewai",
    "deepspeed",
    "diffusers",
    "dspy",
    "duckdb",
    "evidently",
    "faiss",
    "fastmcp",
    "feast",
    "flash-attn",
    "flax",
    "great-expectations",
    "guidance",
    "haystack",
    "huggingface",
    "huggingface-hub",
    "imbalanced-learn",
    "instructor",
    "jax",
    "langgraph",
    "lightgbm",
    "lightning",
    "litellm",
    "llama-cpp-python",
    "llama-index",
    "mcp",
    "mlflow",
    "ollama",
    "openai",
    "optax",
    "optuna",
    "outlines",
    "peft",
    "polars",
    "prophet",
    "pydantic-ai",
    "pydantic-settings",
    "pymc",
    "pymilvus",
    "qdrant-client",
    "ray",
    "ruff",
    "safetensors",
    "sentence-transformers",
    "shap",
    "smolagents",
    "torch-geometric",
    "torchaudio",
    "torchvision",
    "transformers",
    "trl",
    "tiktoken",
    "tokenizers",
    "umap-learn",
    "uv",
    "vllm",
    "wandb",
    "weaviate-client",
    "xgboost",
}

ALIASES: dict[str, str] = {
    "ag-2": "ag2",
    "anthropic-api": "anthropic",
    "bento-ml": "bentoml",
    "chroma": "chromadb",
    "chroma-db": "chromadb",
    "crew-ai": "crewai",
    "dspy-ai": "dspy",
    "faiss-cpu": "faiss",
    "faiss-gpu": "faiss",
    "fast-mcp": "fastmcp",
    "flash-attention": "flash-attn",
    "great-expectation": "great-expectations",
    "hugging-face": "huggingface",
    "hugging-face-transformers": "transformers",
    "huggingface-transformers": "transformers",
    "lang-graph": "langgraph",
    "lite-llm": "litellm",
    "llama_index": "llama-index",
    "llamaindex": "llama-index",
    "model-context-protocol": "mcp",
    "openai-api": "openai",
    "openai-python": "openai",
    "openai-sdk": "openai",
    "pydantic_ai": "pydantic-ai",
    "pydanticai": "pydantic-ai",
    "pydantic_settings": "pydantic-settings",
    "pytorch-geometric": "torch-geometric",
    "pytorch-lightning": "lightning",
    "qdrant-python": "qdrant-client",
    "sentence-transformer": "sentence-transformers",
    "torch-geometric": "torch-geometric",
    "transformer": "transformers",
    "v-llm": "vllm",
    "wandb-ai": "wandb",
    "weights-&-biases": "wandb",
    "weights-and-biases": "wandb",
}

IMPLIES: dict[str, list[str]] = {
    "accelerate": ["python", "pytorch"],
    "ag2": ["python"],
    "bentoml": ["python"],
    "bitsandbytes": ["python", "pytorch"],
    "catboost": ["python"],
    "chromadb": ["python"],
    "crewai": ["python"],
    "dask": ["python"],
    "deepspeed": ["python", "pytorch"],
    "diffusers": ["python", "huggingface"],
    "dspy": ["python"],
    "duckdb": ["python"],
    "evidently": ["python"],
    "fastmcp": ["python", "mcp"],
    "flash-attn": ["python", "pytorch"],
    "flax": ["python", "jax"],
    "great-expectations": ["python"],
    "guidance": ["python"],
    "haystack": ["python"],
    "huggingface-hub": ["python", "huggingface"],
    "imbalanced-learn": ["python", "scikit-learn"],
    "instructor": ["python", "pydantic"],
    "jax": ["python"],
    "langgraph": ["python"],
    "lightgbm": ["python"],
    "lightning": ["python", "pytorch"],
    "litellm": ["python"],
    "llama-cpp-python": ["python"],
    "llama-index": ["python"],
    "mlflow": ["python"],
    "optax": ["python", "jax"],
    "optuna": ["python"],
    "outlines": ["python"],
    "peft": ["python", "transformers"],
    "polars": ["python"],
    "prophet": ["python"],
    "pydantic-ai": ["python", "pydantic"],
    "pydantic-settings": ["python", "pydantic"],
    "pymc": ["python"],
    "pymilvus": ["python"],
    "pyarrow": ["python"],
    "qdrant-client": ["python"],
    "ray": ["python"],
    "safetensors": ["python"],
    "sentence-transformers": ["python", "transformers"],
    "shap": ["python"],
    "smolagents": ["python", "huggingface"],
    "statsmodels": ["python"],
    "tiktoken": ["python"],
    "tokenizers": ["python", "huggingface"],
    "torch-geometric": ["python", "pytorch"],
    "torchaudio": ["python", "pytorch"],
    "torchvision": ["python", "pytorch"],
    "transformers": ["python", "huggingface"],
    "trl": ["python", "transformers"],
    "umap-learn": ["python"],
    "vllm": ["python"],
    "wandb": ["python"],
    "weaviate-client": ["python"],
    "xgboost": ["python"],
}


def is_canonical(skill_data: dict[str, str | None], name: str) -> bool:
    return name in skill_data and skill_data[name] in (None, name)


def main() -> int:
    skill_data: dict[str, str | None] = json.loads(
        SKILL_DATA_FILE.read_text(encoding="utf-8")
    )
    implies: dict[str, list[str]] = json.loads(
        IMPLIES_FILE.read_text(encoding="utf-8")
    )

    added_canonical = added_aliases = added_edges = 0
    errors: list[str] = []

    for name in sorted(CANONICAL_SKILLS):
        if name not in skill_data:
            skill_data[name] = None
            added_canonical += 1
        elif not is_canonical(skill_data, name):
            errors.append(f"{name!r} exists but is not canonical: {skill_data[name]!r}")

    for alias, canonical in ALIASES.items():
        if not is_canonical(skill_data, canonical):
            errors.append(f"alias target {canonical!r} is not canonical")
        elif alias not in skill_data:
            skill_data[alias] = canonical
            added_aliases += 1

    for source, targets in IMPLIES.items():
        if not is_canonical(skill_data, source):
            errors.append(f"implies source {source!r} is not canonical")
            continue
        for target in targets:
            if not is_canonical(skill_data, target):
                errors.append(f"implies target {target!r} is not canonical")

    if errors:
        print("Data invariant errors; no files written:")
        for error in errors:
            print(f"  {error}")
        return 1

    for source, targets in IMPLIES.items():
        current = implies.setdefault(source, [])
        for target in targets:
            if target not in current:
                current.append(target)
                added_edges += 1

    SKILL_DATA_FILE.write_text(
        json.dumps(skill_data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    IMPLIES_FILE.write_text(
        json.dumps(implies, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        "Added "
        f"{added_canonical} canonical skills, {added_aliases} aliases, "
        f"and {added_edges} implication edges."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
