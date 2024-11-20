import sys
sys.path.append('..')

from quickjs import JSEval, JSRuntime, JSContext, JSError


def demo4():
    rt = JSRuntime()
    ctx: JSContext = rt.new_context()

    script_url = 'https://raw.githubusercontent.com/lodash/lodash/refs/heads/main/dist/lodash.min.js'
    ctx.load(script_url)

    lodash = ctx['_']
    print(lodash, type(lodash))

    r = lodash.range
    print(r, type(r))

    r = lodash.range(10, 100, 10)
    print(r, type(r))

    _f0 = ctx.eval('n => n >= 50')
    r = lodash.filter(lodash.range(10, 100, 10), _f0)
    print(r, type(r))

    def _f0(n, *args): return n >= 50
    r0 = lodash.range(10, 100, 10)
    print(r0, type(r0))
    r1 = lodash.filter(r0, _f0)
    print(r1, type(r1))

    def _f0(n, *args): return n >= 50
    r = lodash.range(10, 100, 10)
    print(r, type(r))
    r = lodash.filter(r, _f0)
    print(r, type(r))

    def _f0(n, *args): return n >= 50
    r = lodash.filter(lodash.range(10, 100, 10), _f0)
    print(r, type(r))

    def _f0(n, *args): return n >= 50
    ctx['_f0'] = _f0
    r = lodash.filter(lodash.range(10, 100, 10), ctx.eval('_f0'))
    print(r, type(r))

    _f0 = lambda n, *args: n >= 50 # noqa
    r = lodash.filter(lodash.range(10, 100, 10), _f0)
    print(r, type(r))

    _f0 = lambda n, *args: n >= 50 # noqa
    ctx['_f0'] = _f0
    r = lodash.filter(lodash.range(10, 100, 10), ctx.eval('_f0'))
    print(r, type(r))

    r = lodash.filter(lodash.range(10, 100, 10), lambda n, *args: n >= 50)
    print(r, type(r))


if __name__ == '__main__':
    demo4()
    # input('Press any key')
