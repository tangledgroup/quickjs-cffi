import sys
sys.path.append('..')

from tqdm import tqdm
from quickjs import JSRuntime, JSContext


def demo():
    rt = JSRuntime()

    for i in tqdm(range(1_000)):
        ctx: JSContext = rt.new_context()
        a = ctx.eval(f'var a = {i} + 1; a')
        print('Step', i, a)


if __name__ == '__main__':
    demo()
