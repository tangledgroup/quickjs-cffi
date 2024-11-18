import sys
sys.path.append('..')

from quickjs import JSEval, JSRuntime, JSContext, JSError


def demo2():
    rt = JSRuntime()
    ctx: JSContext = rt.new_context()

    ctx.eval(r'''
        import * as std from 'std';
        import * as os from 'os';
        globalThis.std = std;
        globalThis.os = os;
    ''', eval_flags=JSEval.TYPE_MODULE)

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

    val = ctx.eval('"Hello there!!!"')
    print(val, type(val))

    ctx['a4'] = 'Hello there!'
    val = ctx['a4']
    print(val, type(val))

    ctx['a5'] = "This is demo"
    val = ctx['a5']
    print(val, type(val))

    # ctx['b0'] = [1, 2.0, '3']
    # val = ctx['b0']
    # print(val, type(val))

    # ctx['b'] = [1, 2.0, '3', [10, [20, 30]]]
    # val = ctx['b']
    # print(val, type(val))

    # ctx.eval('b = b.map(n => n * 2)')
    # val = ctx['b']
    # print(val, type(val))

    # ctx.eval('b = b.map(n => n * 2)')
    # val = ctx['b']
    # print(val, type(val))

    # ctx['c'] = {'x': 1, 'y': 2, 'w': [1, 2, 3], 'v': {'a': True, 'b': False}}
    # val = ctx['c']
    # print(val, type(val))

    # ctx['c'] = {'x': 1, 'y': 2}
    # val = ctx['c']
    # print(val, type(val))


if __name__ == '__main__':
    demo2()
    # input('Press any key')
