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

First setup temp node project, so node modules can be installed and used inside QuickJS examples:

```bash
npm init -y
npm install esbuild
```

Huge number of isoloted JavaScript contexts:

```bash
python -B examples/demo_contexts.py
```

Lodash example:

```bash
npm install lodash
python -B examples/demo_lodash.py
```

Handlebas example:

```bash
npm install handlebars
python -B examples/demo_handlebars.py
```

Yjs example:

```bash
npm install yjs
esbuild node_modules/yjs/src/index.js --bundle --outfile=examples/yjs.js --format=iife --loader:.ts=ts --global-name="Y"
python -B examples/demo_yjs.py
```
