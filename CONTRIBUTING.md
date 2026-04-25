# Contributing

Thank you for improving DungeonGrid.

## Development Setup

```bash
python -m pip install -e ".[dev,render,server]"
pre-commit install
pytest
```

## Pull Request Checklist

- Add or update tests for behavior changes.
- Run `ruff check .`.
- Run `ruff format .`.
- Run `pytest`.
- Update docs when changing public action, observation, dungeon, or benchmark behavior.
- Mention expected benchmark-score changes in the PR description.

## Benchmark Stability

DungeonGrid is intended to be usable as an LLM and multi-agent benchmark. Avoid changing existing
dungeon semantics, rewards, hidden information, or action contracts without documenting the
compatibility impact.
