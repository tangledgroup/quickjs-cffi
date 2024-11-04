__all__ = ['QuickJSError', 'Runtime', 'Context']

import json
from typing import Any
from _quickjs import ffi, lib


class QuickJSError(Exception):
    pass


def js_likely(x):
    return x


def js_unlikely(x):
    return x


def JS_VALUE_GET_TAG(v: 'JSValue') -> int: # noqa
    #define JS_VALUE_GET_TAG(v) (int)((uintptr_t)(v) & 0xf)
    return v.tag & 0xf


def JS_VALUE_GET_PTR(v: 'JSValue') -> 'void *': # noqa
    #define JS_VALUE_GET_PTR(v) (void *)((intptr_t)(v) & ~0xf)
    return v.u.ptr


def JS_VALUE_GET_OBJ(v: 'JSValue') -> 'JSObject *': # noqa
    #define JS_VALUE_GET_OBJ(v) ((JSObject *)JS_VALUE_GET_PTR(v))
    return ffi.cast('JSObject *', JS_VALUE_GET_PTR(v))


def JS_VALUE_GET_STRING(v: 'JSValue') -> 'JSString *': # noqa
    #define JS_VALUE_GET_STRING(v) ((JSString *)JS_VALUE_GET_PTR(v))
    return ffi.cast('JSString *', JS_VALUE_GET_PTR(v))


def JS_VALUE_HAS_REF_COUNT(v: 'JSValue') -> bool: # noqa
    #define JS_VALUE_HAS_REF_COUNT(v) ((unsigned)JS_VALUE_GET_TAG(v) >= (unsigned)JS_TAG_FIRST)
    return abs(JS_VALUE_GET_TAG(v)) >= abs(lib.JS_TAG_FIRST)


def JS_FreeValue(ctx: '*JSContext', v: 'JSValue'): # noqa
    # print(f'{JS_VALUE_HAS_REF_COUNT(v) = }')

    if JS_VALUE_HAS_REF_COUNT(v):
        p: '*void' = JS_VALUE_GET_PTR(v) # noqa
        # print(f'{p = }')
        p: '*JSRefCountHeader' = ffi.cast('JSRefCountHeader*', p) # noqa
        # print(f'{p = }')
        # print(f'{p = } {p.ref_count = }')
        p.ref_count -= 1

        if p.ref_count <= 0:
            lib.__JS_FreeValue(ctx, v)


def JS_IsException(v: 'JSValueConst') -> bool: # noqa
    return js_unlikely(v.tag == lib.JS_TAG_EXCEPTION)


class Runtime:
    def __init__(self):
        self._rt = lib.JS_NewRuntime()
        self.ctxs = []
        lib.js_std_init_handlers(self._rt)

        lib.JS_SetModuleLoaderFunc(
            self._rt,
            ffi.cast('JSModuleNormalizeFunc*', 0),
            lib.js_module_loader,
            ffi.cast('void*', 0),
        )


    def __del__(self):
        for ctx in self.ctxs:
            lib.JS_FreeContext(ctx._ctx)

        lib.js_std_free_handlers(self._rt)
        lib.JS_FreeRuntime(self._rt)


    def new_context(self) -> 'Context':
        ctx = Context(self)
        self.ctxs.append(ctx)
        return ctx


class Context:
    def __init__(self, rt: Runtime):
        self.rt = rt
        self._ctx = lib.JS_NewContext(self.rt._rt)
        lib.JS_AddIntrinsicBigFloat(self._ctx)
        lib.JS_AddIntrinsicBigDecimal(self._ctx)
        lib.JS_AddIntrinsicOperators(self._ctx)
        lib.JS_EnableBignumExt(self._ctx, True)

        lib.js_init_module_std(self._ctx, b'std')
        lib.js_init_module_os(self._ctx, b'os')


    def __getitem__(self, key: str) -> Any:
        val: Any = self.eval(key)
        return val


    def __setitem__(self, key: str, value: Any):
        json_value: str = json.dumps(value)
        self.eval(f'var {key} = {json_value};')


    def _eval(self, buf: str, filename: str='<inupt>', eval_flags: int=0) -> Any:
        _buf: bytes = buf.encode()
        _buf_len: int = len(_buf)
        _filename: bytes = filename.encode()
        _val: 'JSValue' = lib.JS_Eval(self._ctx, _buf, _buf_len, _filename, eval_flags) # noqa
        return _val


    def eval(self, buf: str, filename: str='<inupt>', eval_flags: int=0) -> Any:
        _val: 'JSValue' = self._eval(buf, filename, eval_flags) # noqa
        is_exception: bool = JS_IsException(_val)

        if is_exception:
            lib.js_std_dump_error(self._ctx)
            raise QuickJSError(_val.tag)

        if _val.tag == lib.JS_TAG_FIRST:
            raise NotImplementedError('JS_TAG_FIRST')
        elif _val.tag == lib.JS_TAG_BIG_DECIMAL:
            raise NotImplementedError('JS_TAG_BIG_DECIMAL')
        elif _val.tag == lib.JS_TAG_BIG_INT:
            _str = lib.JS_ToString(self._ctx, _val)
            _c_str = lib._inlined_JS_ToCString(self._ctx, _str)
            val = ffi.string(_c_str)
            val = val.decode()
            val = int(val)
            JS_FreeValue(self._ctx, _str)
        elif _val.tag == lib.JS_TAG_BIG_FLOAT:
            raise NotImplementedError('JS_TAG_BIG_FLOAT')
        elif _val.tag == lib.JS_TAG_SYMBOL:
            _atom = lib.JS_ValueToAtom(self._ctx, _val)
            _c_str = lib.JS_AtomToCString(self._ctx, _atom)
            val = ffi.string(_c_str)
            val = val.decode()
            val = f'Symbol({val})'
            lib.JS_FreeAtom(self._ctx, _atom)
        elif _val.tag == lib.JS_TAG_STRING:
            _c_str = lib._inlined_JS_ToCString(self._ctx, _val)
            val = ffi.string(_c_str)
            val = val.decode()
        elif _val.tag == lib.JS_TAG_MODULE:
            raise NotImplementedError('JS_TAG_MODULE')
        elif _val.tag == lib.JS_TAG_FUNCTION_BYTECODE:
            raise NotImplementedError('JS_TAG_FUNCTION_BYTECODE')
        elif _val.tag == lib.JS_TAG_OBJECT:
            replacer = self._eval('null')
            space0 = self._eval('null')
            _json_val = lib.JS_JSONStringify(self._ctx, _val, replacer, space0)
            _c_str = lib._inlined_JS_ToCString(self._ctx, _json_val) # FIXME: who is owner of this object?
            val = ffi.string(_c_str)
            val = val.decode()
            val = json.loads(val)
            JS_FreeValue(self._ctx, _json_val)
        elif _val.tag == lib.JS_TAG_INT:
            val = _val.u.int32
        elif _val.tag == lib.JS_TAG_BOOL:
            val = bool(_val.u.int32)
        elif _val.tag == lib.JS_TAG_NULL:
            val = None
        elif _val.tag == lib.JS_TAG_UNDEFINED:
            val = None
        elif _val.tag == lib.JS_TAG_UNINITIALIZED:
            val = None
        elif _val.tag == lib.JS_TAG_CATCH_OFFSET:
            raise NotImplementedError('JS_TAG_CATCH_OFFSET')
        elif _val.tag == lib.JS_TAG_EXCEPTION:
            # lib._eval('console.error(_)')
            raise NotImplementedError('JS_TAG_EXCEPTION')
        elif _val.tag == lib.JS_TAG_FLOAT64:
            val = _val.u.float64
        else:
            raise NotImplementedError('JS_NAN_BOXING')

        JS_FreeValue(self._ctx, _val)
        return val


def demo1():
    rt = Runtime()
    ctx: Context = rt.new_context()

    val = ctx.eval('2n ** 512n')
    print(val, type(val))

    val = ctx.eval('Symbol("foo bar")')
    print(val, type(val))

    val = ctx.eval('var a = 1 + 1;')
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
    except QuickJSError as e:
        print(f'QuickJSError {e = }')

    input('Press any key')


def demo2():
    rt = Runtime()
    ctx: Context = rt.new_context()

    ctx['a'] = 10
    val = ctx['a']
    print(val, type(val))

    ctx['b'] = [1, 2.0, '3']
    ctx.eval('b = b.map(n => n * 2)')
    val = ctx['b']
    print(val, type(val))

    # ctx.eval('std.puts("0000")')
    # ctx.eval('import * as std from "std"; console.log("123");', eval_flags=1)
    # ctx.eval('std.puts("0111")', eval_flags=1)
    ctx.eval('import * as std from "std";', eval_flags=1)
    ctx.eval('import * as os from "os";', eval_flags=1)
    ctx.eval('export default 1', eval_flags=1)

    # val = ctx.eval('import * as Handlebars from "/home/mtasic/projects-tg/tangledlabs/app/static/js/handlebars.js";', eval_flags=1)
    # print(val, type(val))

    # ctx.eval('console.log(Handlebars.__esModule);', eval_flags=1)
    # ctx.eval('os.puts("1");', eval_flags=0)
    input('Press any key')


def demo3():
    from tqdm import tqdm

    rt = Runtime()

    for i in tqdm(range(1_000)):
        ctx: Context = rt.new_context()
        val = ctx.eval('var a = 1 + 1;')

    input('Press any key')


if __name__ == '__main__':
    demo2()
