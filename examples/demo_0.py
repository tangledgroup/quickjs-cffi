import os
import sys
sys.path.append('..')

from quickjs import *


def demo1():
    rt = QJSRuntime()
    ctx: QJSContext = rt.new_context()

    val = ctx.eval('null')
    print(val, type(val))

    val = ctx.eval('2n ** 512n')
    print(val, type(val))

    val = ctx.eval('Symbol("foo bar")')
    print(val, type(val))

    val = ctx.eval('var a = 1 + 1; a')
    print(val, type(val))

    val = ctx.eval('1 + 1')
    print(val, type(val))

    val = ctx.eval('1 + 1.1')
    print(val, type(val))

    val = ctx.eval('true || false')
    print(val, type(val))

    val = ctx.eval('"aaa" + "bbb"')
    print(val, type(val))

    val = ctx.eval('JSON.stringify([1, 2.0, "3"])')
    print(val, type(val))

    val = ctx.eval('[1, 2.0, "3"]')
    print(val, type(val))

    val = ctx.eval('({x: 1, y: 2.0, z: {w: ["3"]}})')
    print(val, type(val))

    val = ctx.eval('var b = [1, 2.0, "3"].map(n => n * 2); b')
    print(val, type(val))

    try:
        val = ctx.eval('const a = 10;')
        print(val, type(val))
    except QJSError as e:
        print(f'QJSError {e = }')


def demo2():
    rt = QJSRuntime()
    ctx: QJSContext = rt.new_context()

    ctx.eval(r'''
        import * as std from 'std';
        import * as os from 'os';
        globalThis.std = std;
        globalThis.os = os;
    ''', eval_flags=JS_EVAL_TYPE_MODULE)

    ctx.eval(r'std.puts("AAA\n");')

    ctx['a0'] = None
    val = ctx['a0']
    print(val, type(val))

    ctx['a1'] = True
    val = ctx['a1']
    print(val, type(val))

    ctx['a2'] = 10
    val = ctx['a2']
    print(val, type(val))

    ctx['a3'] = 123.45
    val = ctx['a3']
    print(val, type(val))

    ctx['a4'] = 'Hello there!'
    val = ctx['a4']
    print(val, type(val))

    ctx['a5'] = "This is demo"
    val = ctx['a5']
    print(val, type(val))

    ctx['b'] = [1, 2.0, '3', [10, [20, 30]]]
    val = ctx['b']
    print(val, type(val))

    ctx.eval('b = b.map(n => n * 2)')
    val = ctx['b']
    print(val, type(val))

    ctx.eval('b = b.map(n => n * 2)')
    val = ctx['b']
    print(val, type(val))

    ctx['c'] = {'x': 1, 'y': 2, 'w': [1, 2, 3], 'v': {'a': True, 'b': False}}
    val = ctx['c']
    print(val, type(val))

    ctx['c'] = {'x': 1, 'y': 2}
    val = ctx['c']
    print(val, type(val))


def demo3():
    rt = QJSRuntime()
    ctx: QJSContext = rt.new_context()

    ctx.eval('''
        import * as std from 'std';
        import * as os from 'os';
        globalThis.std = std;
        globalThis.os = os;

        function g(x, y, z) {
            return x * y * z;
        }

        globalThis.g = g;
    ''', eval_flags=JS_EVAL_TYPE_MODULE)

    ctx.eval('''
        function f(x, y, z) {
            return x * y * z;
        }

        function g(x, y) {
            return [...x, ...y];
        }

        function h(x, y) {
            return Object.assign({}, x, y);
        }
    ''')

    f = ctx['f']
    print(f, type(f))

    r = f(2, 3, 4)
    print(r, type(r))

    g = ctx.get('g')
    print(f, type(f))

    r = g([20, 30], [40, 50, 60])
    print(r, type(r))

    h = ctx.get('h')
    print(f, type(f))

    r = h({'20': 20}, {'40': 40, '50': 50})
    print(r, type(r))


def demo4():
    rt = QJSRuntime()
    ctx: QJSContext = rt.new_context()

    script_url = 'https://raw.githubusercontent.com/lodash/lodash/refs/heads/main/dist/lodash.min.js'
    ctx.load_script(script_url)

    lodash = ctx['_']
    print(lodash, type(lodash))

    # r = lodash.range
    # print(r, type(r))

    # r = lodash.range(10, 100, 10)
    # print(r, type(r))

    # _f0 = ctx.eval('n => n >= 50')
    # r = lodash.filter(lodash.range(10, 100, 10), _f0)
    # print(r, type(r))

    def _f0(n, *args): return n >= 50
    r = lodash.filter(lodash.range(10, 100, 10), _f0)
    print(r, type(r))

    # def _f0(n, *args): return n >= 50
    # ctx['_f0'] = _f0
    # r = lodash.filter(lodash.range(10, 100, 10), ctx.eval('_f0'))
    # print(r, type(r))

    # _f0 = lambda n, *args: n >= 50
    # r = lodash.filter(lodash.range(10, 100, 10), _f0)
    # print(r, type(r))

    # _f0 = lambda n, *args: n >= 50
    # ctx['_f0'] = _f0
    # r = lodash.filter(lodash.range(10, 100, 10), ctx.eval('_f0'))
    # print(r, type(r))

    # r = lodash.filter(lodash.range(10, 100, 10), lambda n, *args: n >= 50)
    # print(r, type(r))


def demo5():
    from tqdm import tqdm

    rt = QJSRuntime()

    for i in tqdm(range(1_000)):
        ctx: QJSContext = rt.new_context()
        ctx.eval('var a = 1 + 1;')


if __name__ == '__main__':
    demo1()
    demo2()
    # demo3()
    # demo4()
    # input('Press any key')
