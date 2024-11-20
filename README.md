# quickjs-cffi

Python QuickJS CFFI

## Build

```bash
python -m venv venv
source venv/bin/activate
pip install poetry
poetry install
pip install tqdm
```

## Demos

Huge number of isoloted JavaScript contexts.

```bash
python -B examples/demo_contexts.py
```
