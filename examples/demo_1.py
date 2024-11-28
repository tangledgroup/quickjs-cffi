import sys
sys.path.append('..')

from quickjs import JSEval, JSRuntime, JSContext, JSError


def demo1():
    rt = JSRuntime()
    ctx: JSContext = rt.new_context()

    val = ctx.eval('undefined')
    print(val, type(val))

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

    val = ctx.eval('"aaa" + "bbb"')
    val = str(val)
    print(val, type(val))

    val = ctx.eval('JSON.stringify([1, 2.0, "3"])')
    print(val, type(val))

    val = ctx.eval('[1, 2.0, "3"]')
    print(val, type(val))

    val = ctx.eval('({x: 1, y: 2.0, z: {w: ["3"]}})')
    print(val, type(val))

    val = ctx.eval('var b = [1, 2.0, "3"].map(n => n * 2); b')
    print(val, type(val))

    val = ctx.eval('[1, 2.0, "3"].map(n => n * 2)')
    print(val, type(val))

    val = ctx.eval('Array.from')
    print(val, type(val))

    val = ctx.eval('[].map')
    print(val, type(val))

    try:
        val = ctx.eval('const a = 10;')
        print(val, type(val))
    except JSError as e:
        print(f'{e = }')


if __name__ == '__main__':
    demo1()
    # input('Press any key')
