# marimol development guidelines

Marimol is a python package that allows the visualization of molecular structures in marimo notebooks.

## Dev commands

All code and dev commands must be run using `uv`. If this a fresh clone, run `uv sync --all-extras` to install the dependencies.

```bash
# All python code must be run inside the uv environment
uv run python <CODE>

# build the docs
uv run just docs-build

# Run lint and tests
uv run just check

# Format code
uv run just format

# Install git hooks
uv run just hooks
```

## Git workflow

- All development should be done on the `dev` branch.
- Pull requests should be opened against the `dev` branch.
- The `main` branch is reserved for stable releases.

## Adding features

- Any new code must be fully documented, all python code must have docstrings and type hints.
- Any new functionality that can be tested must have tests.
- If the changes are significant, update the documentation and examples. The documentation must include the version in which a feature was added and, if it was deprecated, the version in which it will be removed.
