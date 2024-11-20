import sys
sys.path.append('..')

from quickjs import JSRuntime, JSContext


def demo_online():
    rt = JSRuntime()
    ctx: JSContext = rt.new_context()

    ctx.load('https://raw.githubusercontent.com/lodash/lodash/refs/heads/main/dist/lodash.min.js')

    lodash = ctx['_']
    print(lodash)
    print(lodash.range(0, 100, 10))


def demo_offline():
    rt = JSRuntime()
    ctx: JSContext = rt.new_context()

    ctx.load('node_modules/lodash/lodash.min.js')

    lodash = ctx['_']
    print(lodash)
    print(lodash.range(0, 100, 10))


if __name__ == '__main__':
    demo_online()
    demo_offline()
