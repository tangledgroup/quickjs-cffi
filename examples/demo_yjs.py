import sys
sys.path.append('..')

from quickjs import JSRuntime, JSContext, JSError, JSEval


def demo():
    rt = JSRuntime()
    ctx: JSContext = rt.new_context()

    # script_url = 'https://cdn.jsdelivr.net/npm/yjs@13.6.20/src/types/YText.min.js'
    # ctx.load_script(script_url)
    # ctx.eval('''
    #     import * as Y from "http://unpkg.com/yjs@13.6.20/dist/yjs.mjs?module";
    # ''', eval_flags=JSEval.TYPE_MODULE)
    ctx.eval('''
        import * as std from 'std';
        import * as os from 'os';
        import * as Y from "node_modules/yjs/dist/yjs.mjs";

        globalThis.std = std;
        globalThis.os = os;
        // globalThis.Y = Y;
    ''', eval_flags=JSEval.TYPE_MODULE)

    std = ctx['std']
    print(std.puts)

    Y = ctx['Y']
    print(Y)


if __name__ == '__main__':
    demo()
    # input('Press any key')
