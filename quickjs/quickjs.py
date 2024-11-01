from typing import Any
from _quickjs import ffi, lib


'''
rt = lib.JS_NewRuntime()
ctx = lib.JS_NewContext(rt)
lib.JS_AddIntrinsicBigFloat(ctx)
lib.JS_AddIntrinsicBigDecimal(ctx)
lib.JS_AddIntrinsicOperators(ctx)
lib.JS_EnableBignumExt(ctx, True)
lib.js_init_module_std(ctx, b"std")
lib.js_init_module_os(ctx, b"os")

# buf = b"var a = 1 + 1;"
buf = b"1 + 1;"
buf_len = len(buf)
filename = b"<input>"
eval_flags = 0
val = lib.JS_Eval(ctx, buf, buf_len, filename, eval_flags)
print(val.tag)

# lib.js_std_free_handlers(rt)
lib.JS_FreeContext(ctx)
lib.JS_FreeRuntime(rt)
'''


def js_likely(x):
    return x


def js_unlikely(x):
    return x


def JS_VALUE_GET_TAG(v: 'JSValue') -> int:
    #define JS_VALUE_GET_TAG(v) (int)((uintptr_t)(v) & 0xf)
    return v.tag & 0xf


def JS_VALUE_GET_PTR(v: 'JSValue') -> 'void*':
    #define JS_VALUE_GET_PTR(v) (void *)((intptr_t)(v) & ~0xf)
    return v.u.ptr


def JS_VALUE_HAS_REF_COUNT(v: 'JSValue') -> bool:
    #define JS_VALUE_HAS_REF_COUNT(v) ((unsigned)JS_VALUE_GET_TAG(v) >= (unsigned)JS_TAG_FIRST)
    return ffi.cast('unsigned', JS_VALUE_GET_TAG(v)) >= ffi.cast('unsigned', lib.JS_TAG_FIRST)


def JS_FreeValue(ctx: '*JSContext', v: 'JSValue'):
    print(f'{JS_VALUE_HAS_REF_COUNT(v) = }')

    if JS_VALUE_HAS_REF_COUNT(v):
        p: '*void' = JS_VALUE_GET_PTR(v)
        print(f'{p = }')
        p: '*JSRefCountHeader' = ffi.cast('JSRefCountHeader*', p)
        print(f'{p = }')
        print(f'{p = } {p.ref_count = }')
        p.ref_count -= 1

        if p.ref_count <= 0:
            lib.__JS_FreeValue(ctx, v)


def JS_IsException(v: 'JSValueConst') -> bool:
    return js_unlikely(v.tag == lib.JS_TAG_EXCEPTION)


class Runtime:
    def __init__(self):
        self._rt = lib.JS_NewRuntime()
        self._ctxs = []


    def __del__(self):
        for _ctx in self._ctxs:
            lib.JS_FreeContext(_ctx)

        lib.JS_FreeRuntime(self._rt)


class Context:
    def __init__(self, rt: Runtime):
        self.rt = rt
        self._ctx = lib.JS_NewContext(self.rt._rt)
        self.rt._ctxs.append(self._ctx)
        lib.JS_AddIntrinsicBigFloat(self._ctx)
        lib.JS_AddIntrinsicBigDecimal(self._ctx)
        lib.JS_AddIntrinsicOperators(self._ctx)
        lib.JS_EnableBignumExt(self._ctx, True)
        lib.js_init_module_std(self._ctx, b"std")
        lib.js_init_module_os(self._ctx, b"os")



    def eval(self, buf: str, filename: str='<inupt>', eval_flags: int=0) -> Any:
        _buf = buf.encode()
        _buf_len = len(_buf)
        _filename = filename.encode()
        _val = lib.JS_Eval(self._ctx, _buf, _buf_len, _filename, eval_flags)

        is_exception: bool = JS_IsException(_val)

        if is_exception:
            raise ValueError(_val.tag)

        if _val.tag == lib.JS_TAG_FIRST:
            raise NotImplementedError('JS_TAG_FIRST')
        elif _val.tag == lib.JS_TAG_BIG_DECIMAL:
            raise NotImplementedError('JS_TAG_BIG_DECIMAL')
        elif _val.tag == lib.JS_TAG_BIG_INT:
            raise NotImplementedError('JS_TAG_BIG_INT')
        elif _val.tag == lib.JS_TAG_BIG_FLOAT:
            raise NotImplementedError('JS_TAG_BIG_FLOAT')
        elif _val.tag == lib.JS_TAG_SYMBOL:
            raise NotImplementedError('JS_TAG_SYMBOL')
        elif _val.tag == lib.JS_TAG_STRING:
            raise NotImplementedError('JS_TAG_STRING')
        elif _val.tag == lib.JS_TAG_MODULE:
            raise NotImplementedError('JS_TAG_MODULE')
        elif _val.tag == lib.JS_TAG_FUNCTION_BYTECODE:
            raise NotImplementedError('JS_TAG_FUNCTION_BYTECODE')
        elif _val.tag == lib.JS_TAG_OBJECT:
            raise NotImplementedError('JS_TAG_OBJECT')
        elif _val.tag == lib.JS_TAG_INT:
            val = _val.u.int32
            JS_FreeValue(self._ctx, _val)
        elif _val.tag == lib.JS_TAG_BOOL:
            raise NotImplementedError('JS_TAG_BOOL')
        elif _val.tag == lib.JS_TAG_NULL:
            val = None
        elif _val.tag == lib.JS_TAG_UNDEFINED:
            val = None
        elif _val.tag == lib.JS_TAG_UNINITIALIZED:
            raise NotImplementedError('JS_TAG_UNINITIALIZED')
        elif _val.tag == lib.JS_TAG_CATCH_OFFSET:
            raise NotImplementedError('JS_TAG_CATCH_OFFSET')
        elif _val.tag == lib.JS_TAG_EXCEPTION:
            raise NotImplementedError('JS_TAG_EXCEPTION')
        elif _val.tag == lib.JS_TAG_FLOAT64:
            raise NotImplementedError('JS_TAG_FLOAT64')
        elif _val.tag == lib.JS_TAG_FIRST:
            raise NotImplementedError('JS_TAG_FIRST')
        else:
            raise NotImplementedError('JS_NAN_BOXING')

        return val


rt = Runtime()
ctx = Context(rt)
# val = ctx.eval('var a = 1 + 1;')
val = ctx.eval('1 + 1;')
print(val, type(val))
