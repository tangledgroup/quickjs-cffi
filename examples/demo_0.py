import sys
sys.path.append('..')

from quickjs import JSEval, JSRuntime, JSContext, JSError


def demo0():
    from tqdm import tqdm

    rt = JSRuntime()

    for i in tqdm(range(1_000)):
        ctx: JSContext = rt.new_context()
        ctx.eval('var a = 1 + 1;')


if __name__ == '__main__':
    demo0()
    # input('Press any key')
