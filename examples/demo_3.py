import sys
sys.path.append('..')

from quickjs import JSEval, JSRuntime, JSContext, JSError


def demo3():
    rt = JSRuntime()
    ctx: JSContext = rt.new_context()

    ctx.eval('''
        import * as std from 'std';
        import * as os from 'os';
        globalThis.std = std;
        globalThis.os = os;

        function g(x, y, z) {
            return x * y * z;
        }

        globalThis.g = g;
    ''', eval_flags=JSEval.TYPE_MODULE)

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


if __name__ == '__main__':
    demo3()
    # input('Press any key')
