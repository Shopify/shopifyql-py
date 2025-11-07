# Contributing to shopifyql

Thanks for your interest in contributing! We welcome issues and pull requests to make this library better for everyone.

By participating in this project, you agree to abide by our [Code of Conduct](./CODE_OF_CONDUCT.md).

## How to contribute

- Open an issue describing the bug fix or feature you’d like to work on.
- For small fixes, feel free to open a pull request directly and reference the issue if one exists.

## Development setup

This project targets Python 3.11+.

Using uv:

```bash
uv venv
uv sync --group dev
```

Using pip:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

## Testing

```bash
pytest -q
```

## Linting & type checking

```bash
ruff check .
pyright
```

## Release process

- We follow semantic versioning.
- Maintainers will publish releases to PyPI.

## License

By contributing, you agree that your contributions will be licensed under the terms of the [MIT License](./LICENSE.md).
