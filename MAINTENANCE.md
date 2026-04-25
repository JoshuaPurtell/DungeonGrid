# Maintenance

## Release Process

1. Run CI on `main`.
2. Run benchmark smoke checks.
3. Update changelog or release notes.
4. Tag a release.
5. Publish to PyPI from the GitHub release workflow.

## Compatibility Policy

Patch releases should not intentionally change benchmark scores. Minor releases may add dungeons,
actions, or metrics. Breaking changes require a migration note.

## Errata

If a bug affected benchmark results, document affected versions, affected dungeons, whether old
scores should be considered stale, and the first fixed version.
