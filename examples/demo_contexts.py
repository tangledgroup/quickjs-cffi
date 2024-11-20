import sys
sys.path.append('..')

from tqdm import tqdm
from quickjs import JSRuntime, JSContext


def demo():
    rt = JSRuntime()

    for i in tqdm(range(1_000)):
        ctx: JSContext = rt.new_context()
        ctx.eval('var a = 1 + 1;')


if __name__ == '__main__':
    demo()
