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

## Install

```bash
pip install quickjs-cffi
```

## Features

<pre>
✅ Use **npm** to install packages and use them directly
✅ In case you need to use complex **ECMAScript** or **TypeScript** modules/libraries/packages see [Yjs](https://github.com/yjs/yjs) example below how to use [esbuild](https://esbuild.github.io/) to transpile their code to [QuickJS](https://bellard.org/quickjs/) compatible ECMAScript modules
✅ Import remote and local ECMAScript scripts/modules
✅ Define Python objects and pass them to JavaScript
✅ Define JavaScript objects and pass them to Python
✅ Python objects live in Python environment
✅ JavaScript objects live in JavaScript environment
✅ Freely use Python objects in JavaScript
✅ Freely use JavaScript objects in Python
</pre>

## Usage

```python
from quickjs import JSEval, JSRuntime, JSContext, JSError

# create runtime and context
rt = JSRuntime()
ctx: JSContext = rt.new_context()

# load lodash from remote location; it also accepts local JavaScript files
ctx.load('https://raw.githubusercontent.com/lodash/lodash/refs/heads/main/dist/lodash.min.js')
lodash: JSValue = ctx['_']

# call lodash.range to create array JavaScript side, and return its handler to Python side
r: JSValue = lodash.range(10, 100, 10)

# on Python side, define JavaScript function and use it to filter JavaScript array
f0: JSValue = ctx.eval('n => n >= 50')
r: JSValue = lodash.filter(lodash.range(10, 100, 10), f0)

# on Python side, define Python function and use on JavaScript side to filter array
def f1(n, *args):
    return n >= 50

r: JSValue = lodash.filter(lodash.range(10, 100, 10), f1)

# on Python side, define Python lambda function and use on JavaScript side to filter array
f2 = lambda n, *args: n >= 50 # noqa
r: JSValue = lodash.filter(lodash.range(10, 100, 10), f2)

# on Python side, define pass inplace Python lambda function and use on JavaScript side to filter array
r: JSValue = lodash.filter(lodash.range(10, 100, 10), lambda n, *args: n >= 50)

# on Python side, define Python lambda function
# then set it as global function in JavaScript
# and use it on JavaScript side to filter array
ctx['f3'] = lambda n, *args: n >= 50
r: JSValue = lodash.filter(lodash.range(10, 100, 10), ctx.eval('f3'))
```

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
