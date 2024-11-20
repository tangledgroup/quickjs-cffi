# quickjs-cffi

<!--
[![Build][build-image]]()
[![Status][status-image]][pypi-project-url]
[![Stable Version][stable-ver-image]][pypi-project-url]
[![Coverage][coverage-image]]()
[![Python][python-ver-image]][pypi-project-url]
[![License][mit-image]][mit-url]
-->
[![PyPI](https://img.shields.io/pypi/v/quickjs-cffi)](https://pypi.org/project/quickjs-cffi/)
[![Supported Versions](https://img.shields.io/pypi/pyversions/quickjs-cffi)](https://pypi.org/project/quickjs-cffi)
[![PyPI Downloads](https://img.shields.io/pypi/dm/quickjs-cffi)](https://pypistats.org/packages/quickjs-cffi)
[![Github Downloads](https://img.shields.io/github/downloads/tangledgroup/quickjs-cffi/total.svg?label=Github%20Downloads)]()
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)

**Python** binding for [QuickJS Javascript Engine](https://bellard.org/quickjs/) using **cffi**. Supports **x86_64** and **aarch64** platforms.

NOTE: Currently supported operating system is Linux (`manylinux_2_28` and `musllinux_1_2`)

## Build

```bash
python -m venv venv
source venv/bin/activate
pip install poetry
poetry install --all-extras
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
