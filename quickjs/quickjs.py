__all__ = [
    'JS_EVAL_TYPE_GLOBAL',
    'JS_EVAL_TYPE_MODULE',
    'JS_EVAL_TYPE_DIRECT',
    'JS_EVAL_TYPE_INDIRECT',
    'JS_EVAL_TYPE_MASK',
    'JS_EVAL_FLAG_STRICT',
    'JS_EVAL_FLAG_STRIP',
    'JS_EVAL_FLAG_COMPILE_ONLY',
    'JS_EVAL_FLAG_BACKTRACE_BARRIER',
    'JS_EVAL_FLAG_ASYNC',

    'QJSRuntime',
    'QJSContext',
    'QJSError',
]

import os
import re
import json
import time
import inspect
import tempfile
import urllib.request
from typing import Any
from weakref import WeakSet

from ._quickjs import ffi, lib


_c_temp: set[Any] = set()

# Regular expression pattern to match URLs
url_pattern = re.compile(r'^(?:http|ftp|https)://')

# /* JS_Eval() flags */
#define JS_EVAL_TYPE_GLOBAL   (0 << 0) /* global code (default) */
JS_EVAL_TYPE_GLOBAL = 0 << 0
#define JS_EVAL_TYPE_MODULE   (1 << 0) /* module code */
JS_EVAL_TYPE_MODULE = 1 << 0
#define JS_EVAL_TYPE_DIRECT   (2 << 0) /* direct call (internal use) */
JS_EVAL_TYPE_DIRECT = 2 << 0
#define JS_EVAL_TYPE_INDIRECT (3 << 0) /* indirect call (internal use) */
JS_EVAL_TYPE_INDIRECT = 3 << 0
#define JS_EVAL_TYPE_MASK     (3 << 0)
JS_EVAL_TYPE_MASK = 3 << 0

#define JS_EVAL_FLAG_STRICT   (1 << 3) /* force 'strict' mode */
JS_EVAL_FLAG_STRICT = 1 << 3
#define JS_EVAL_FLAG_STRIP    (1 << 4) /* force 'strip' mode */
JS_EVAL_FLAG_STRIP = 1 << 4
# /* compile but do not run. The result is an object with a
#    JS_TAG_FUNCTION_BYTECODE or JS_TAG_MODULE tag. It can be executed
#    with JS_EvalFunction(). */
#define JS_EVAL_FLAG_COMPILE_ONLY (1 << 5)
JS_EVAL_FLAG_COMPILE_ONLY = 1 << 5
# /* don't include the stack frames before this eval in the Error() backtraces */
#define JS_EVAL_FLAG_BACKTRACE_BARRIER (1 << 6)
JS_EVAL_FLAG_BACKTRACE_BARRIER = 1 << 6
# /* allow top-level await in normal script. JS_Eval() returns a
#    promise. Only allowed with JS_EVAL_TYPE_GLOBAL */
#define JS_EVAL_FLAG_ASYNC (1 << 7)
JS_EVAL_FLAG_ASYNC = 1 << 7


def JS_VALUE_GET_TAG(v: 'JSValue') -> int: # noqa
    #define JS_VALUE_GET_TAG(v) (int)((uintptr_t)(v) & 0xf)
    return v.tag & 0xf


def JS_VALUE_GET_NORM_TAG(v: 'JSValue') -> int: # noqa
    # /* same as JS_VALUE_GET_TAG, but return JS_TAG_FLOAT64 with NaN boxing */
    #define JS_VALUE_GET_NORM_TAG(v) JS_VALUE_GET_TAG(v)
    return JS_VALUE_GET_TAG(v)


def JS_VALUE_GET_INT(v: 'JSValue') -> int: # noqa
    #define JS_VALUE_GET_INT(v) (int)((intptr_t)(v) >> 4)
    return v.u.int32


def JS_VALUE_GET_BOOL(v: 'JSValue') -> bool: # noqa
    #define JS_VALUE_GET_BOOL(v) JS_VALUE_GET_INT(v)
    return bool(v.u.int32)


def JS_VALUE_GET_FLOAT64(v: 'JSValue') -> float: # noqa
    #define JS_VALUE_GET_FLOAT64(v) (double)JS_VALUE_GET_INT(v)
    return v.u.float64


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


def JS_VALUE_GET_REF_COUNT(v: 'JSValue') -> int: # noqa
    _v_p: 'void*' = JS_VALUE_GET_PTR(v) # noqa
    _rfh_p: 'JSRefCountHeader*' = ffi.cast('JSRefCountHeader *', _v_p) # noqa
    return _rfh_p.ref_count


def _JS_ToCString(_ctx: 'JSContext*', _val: 'JSValue') -> 'char*': # noqa
    return lib._inlined_JS_ToCString(_ctx, _val)


def _JS_FreeValue(_ctx: 'JSContext*', _val: 'JSValue'): # noqa
    lib._inlined_JS_FreeValue(_ctx, _val)


def _JS_Eval(_ctx: 'JSContext*', buf: str, filename: str='<inupt>', eval_flags: int=JS_EVAL_TYPE_GLOBAL) -> Any: # noqa
    _buf: bytes = buf.encode()
    _buf_len: int = len(_buf)
    _filename: bytes = filename.encode()
    _val: 'JSValue' = lib.JS_Eval(_ctx, _buf, _buf_len, _filename, eval_flags) # noqa
    return _val


def convert_jsvalue_to_pystr(_ctx: 'JSContext*', _val: 'JSValue') -> str: # noqa
    _c_str: 'char*' = _JS_ToCString(_ctx, _val) # noqa
    val: bytes = ffi.string(_c_str)
    val: str = val.decode()
    lib.JS_FreeCString(_ctx, _c_str)
    return val


def stringify_object(_ctx: 'JSContext*', _obj: 'JSValue') -> str: # noqa
    _this: 'JSValue' = lib.JS_GetGlobalObject(_ctx) # noqa
    _func = lib.JS_GetPropertyStr(_ctx, _this, b'__stringifyObject')
    jsargs_len = 1
    _jsargs: 'JSValue*' = ffi.new('JSValue[]', [_obj]) # noqa

    _val = lib.JS_Call(_ctx, _func, _this, jsargs_len, _jsargs)
    val = convert_jsvalue_to_pystr(_ctx, _val)

    ffi.release(_jsargs)
    _JS_FreeValue(_ctx, _val)
    _JS_FreeValue(_ctx, _func)
    _JS_FreeValue(_ctx, _this)
    return val


def convert_jsvalue_to_pyvalue(_ctx: 'JSContext*', _val: 'JSValue') -> Any: # noqa
    is_exception: bool = lib._inlined_JS_IsException(_val)

    if is_exception:
        _e_val = lib.JS_GetException(_ctx)
        _JS_FreeValue(_ctx, _val)
        e = QJSError(_ctx, _e_val)
        raise e

    if _val.tag == lib.JS_TAG_FIRST:
        raise NotImplementedError('JS_TAG_FIRST')
    elif _val.tag == lib.JS_TAG_BIG_DECIMAL:
        raise NotImplementedError('JS_TAG_BIG_DECIMAL')
    elif _val.tag == lib.JS_TAG_BIG_INT:
        val: str = convert_jsvalue_to_pystr(_ctx, _val)
        val: int = int(val)
    elif _val.tag == lib.JS_TAG_BIG_FLOAT:
        raise NotImplementedError('JS_TAG_BIG_FLOAT')
    elif _val.tag == lib.JS_TAG_SYMBOL:
        val = QJSSymbol(_ctx, _val)
    elif _val.tag == lib.JS_TAG_STRING:
        val = QJSString(_ctx, _val)
    elif _val.tag == lib.JS_TAG_MODULE:
        raise NotImplementedError('JS_TAG_MODULE')
    elif _val.tag == lib.JS_TAG_FUNCTION_BYTECODE:
        raise NotImplementedError('JS_TAG_FUNCTION_BYTECODE')
    elif _val.tag == lib.JS_TAG_OBJECT:
        if lib.JS_IsFunction(_ctx, _val):
            val = QJSFunction(_ctx, _val, None)
        elif lib.JS_IsArray(_ctx, _val):
            val = QJSArray(_ctx, _val)
        else:
            val = QJSObject(_ctx, _val) # Object, Map, Set, etc
    elif _val.tag == lib.JS_TAG_INT:
        val = JS_VALUE_GET_INT(_val)
        _JS_FreeValue(_ctx, _val)
    elif _val.tag == lib.JS_TAG_BOOL:
        val = JS_VALUE_GET_BOOL(_val)
        _JS_FreeValue(_ctx, _val)
    elif _val.tag == lib.JS_TAG_NULL:
        val = None
        _JS_FreeValue(_ctx, _val)
    elif _val.tag == lib.JS_TAG_UNDEFINED:
        val = None # FIXME: use special value
        _JS_FreeValue(_ctx, _val)
    elif _val.tag == lib.JS_TAG_UNINITIALIZED:
        raise NotImplementedError('JS_TAG_CATCH_OFFSET')
    elif _val.tag == lib.JS_TAG_CATCH_OFFSET:
        raise NotImplementedError('JS_TAG_CATCH_OFFSET')
    elif _val.tag == lib.JS_TAG_EXCEPTION:
        # FIXME: handle exception
        raise NotImplementedError('JS_TAG_EXCEPTION')
    elif _val.tag == lib.JS_TAG_FLOAT64:
        val = JS_VALUE_GET_FLOAT64(_val)
        _JS_FreeValue(_ctx, _val)
    else:
        _JS_FreeValue(_ctx, _val)
        raise NotImplementedError('JS_NAN_BOXING')

    return val


def convert_pyargs_to_jsargs(_ctx: 'JSContext*', pyargs: list[Any]) -> (int, 'JSValue'): # noqa
    _filename: 'char*' = ffi.cast('char*', 0) # noqa
    val_length = len(pyargs)
    _val = [convert_pyvalue_to_jsvalue(_ctx, n) for n in pyargs]
    _val = ffi.new('JSValue[]', _val)
    return val_length, _val


def convert_pyvalue_to_jsvalue(_ctx: 'JSContext*', val: Any) -> 'JSValue': # noqa
    if val is None:
        _val = _JS_Eval(_ctx, 'null')
    elif isinstance(val, QJSValue):
        _val = val._val
    elif isinstance(val, bool):
        _val = _JS_Eval(_ctx, json.dumps(val))
    elif isinstance(val, int):
        _val = _JS_Eval(_ctx, json.dumps(val))
    elif isinstance(val, float):
        _val = _JS_Eval(_ctx, json.dumps(val))
    elif isinstance(val, str):
        _val = _JS_Eval(_ctx, json.dumps(val))
    elif isinstance(val, (list, tuple)):
        _val = lib.JS_NewArray(_ctx)
        val2 = QJSValue(_ctx, _val)
        _Array_push_atom = lib.JS_NewAtom(_ctx, b'push')

        for n in val:
            _n: 'JSValue' = convert_pyvalue_to_jsvalue(_ctx, n) # noqa
            _n_p: 'JSValue*' = ffi.new('JSValue[]', [_n]) # noqa

            lib.JS_Invoke(_ctx, _val, _Array_push_atom, 1, _n_p)

            ffi.release(_n_p)
            _JS_FreeValue(_ctx, _n)

        lib.JS_FreeAtom(_ctx, _Array_push_atom)
    elif isinstance(val, dict):
        _val = lib.JS_NewObject(_ctx)
        val2 = QJSValue(_ctx, _val)

        for k, v in val.items():
            assert isinstance(k, str)
            _k: bytes = k.encode()
            _v: 'JSValue' = convert_pyvalue_to_jsvalue(_ctx, v)

            lib.JS_SetPropertyStr(_ctx, _val, _k, _v)

            # NOTE: line below is not required based on JS_SetPropertyStr logic
            #   _JS_FreeValue(_ctx, _v)
    elif callable(val):
        val_handler: 'void*' = ffi.new_handle(val) # noqa
        _c_temp.add(val_handler)
        _val_handler: 'JSValue' = lib._quikcjs_cffi_JS_MKPTR(lib.JS_TAG_OBJECT, val_handler) # noqa
        # _c_temp.add(_val_handler)

        # val2 = QJSValue(_ctx, _val_handler)

        _func = lib._quikcjs_cffi_py_func_wrap
        _length = len(inspect.signature(val).parameters)
        _magic = 0
        _data_len = 1
        _data = ffi.addressof(_val_handler)
        # _data = ffi.new('JSValue[]', [_val_handler])
        _val = lib.JS_NewCFunctionData(_ctx, _func, _length, _magic, _data_len, _data)

        # val2 = QJSValue(_ctx, _val)
    else:
        raise ValueError(f'Unsupported Python value {type(val)}')

    return _val


def download_file_to_tempfile(url: str) -> str:
    file_extension = os.path.splitext(url)[-1]

    with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
        with urllib.request.urlopen(url) as response:
            temp_file.write(response.read())

        return temp_file.name


def is_url(path_or_url: str) -> bool:
    if url_pattern.match(path_or_url):
        return True
    elif os.path.exists(path_or_url):
        return False
    else:
        raise ValueError(path_or_url)


# typedef JSValue JSCFunctionData(JSContext *ctx, JSValueConst this_val, int argc, JSValueConst *argv, int magic, JSValue *func_data);
@ffi.def_extern()
def _quikcjs_cffi_py_func_wrap(_ctx, _this_val, _argc, _argv, _magic, _func_data):
    _val_handler: 'JSValue' = _func_data[0] # noqa
    _val_p: 'void*' = JS_VALUE_GET_PTR(_val_handler) # noqa
    val_handler = ffi.from_handle(_val_p)
    py_func = val_handler

    pyargs = [_argv[i] for i in range(_argc)]
    pyargs = [convert_jsvalue_to_pyvalue(_ctx, n) for n in pyargs]
    ret = py_func(*pyargs)

    _ret = convert_pyvalue_to_jsvalue(_ctx, ret)
    # _c_temp.discard(_val_p)
    print(f'{_c_temp = }')
    return _ret


class QJSValue:
    def __init__(self, _ctx: 'JSContext*', _val: 'JSValue'=None): # noqa
        self._ctx = _ctx
        self._val = _val

        ctx = QJSContext.get_qjscontext(_ctx)
        ctx.add_qjsvalue(self)


    def __del__(self):
        _ctx = self._ctx
        _val = self._val
        _rt = lib.JS_GetRuntime(_ctx)

        if lib.JS_IsLiveObject(_rt, _val):
            _JS_FreeValue(_ctx, _val)


    free = __del__


    def __repr__(self) -> str:
        _ctx = self._ctx
        _val = self._val
        val: str = stringify_object(_ctx, _val)
        return f'<{self.__class__.__name__} at {hex(id(self))} {_val.u.ptr} {val}>'


    def __getattr__(self, attr: str) -> Any:
        _ctx = self._ctx
        _val = self._val
        _c_attr: bytes = attr.encode()
        _ret = lib.JS_GetPropertyStr(_ctx, _val, _c_attr)
        ret: Any = convert_jsvalue_to_pyvalue(_ctx, _ret)

        # if isinstance(ret, QJSValue):
        #     pass
        # else:
        #     _JS_FreeValue(_ctx, _ret)

        return ret




class QJSString(QJSValue):
    pass


class QJSSymbol(QJSValue):
    def __repr__(self) -> str:
        _ctx = self._ctx
        _val = self._val

        _atom = lib.JS_ValueToAtom(_ctx, _val)
        _c_str = lib.JS_AtomToCString(_ctx, _atom)
        val = ffi.string(_c_str)
        val = val.decode()
        val = f'Symbol({val})'
        lib.JS_FreeCString(_ctx, _c_str)
        lib.JS_FreeAtom(_ctx, _atom)
        return f'<{self.__class__.__name__} at {hex(id(self))} {_val.u.ptr} {val}>'


class QJSArray(QJSValue):
    pass


class QJSObject(QJSValue):
    pass


class QJSFunction(QJSValue):
    def __init__(self, _ctx: 'JSContext*', _val: 'JSValue'=None, _this: 'JSValue'=None): # noqa
        self._ctx = _ctx
        self._val = _val # _func
        self._this = _this if _this else lib.JS_GetGlobalObject(_ctx)

        ctx = QJSContext.get_qjscontext(_ctx)
        ctx.add_qjsvalue(self)


    def __repr__(self) -> str:
        _ctx = self._ctx
        _val = self._val
        return f'<{self.__class__.__name__} at {hex(id(self))} {_val.u.ptr}>'


    def __call__(self, *pyargs) -> Any:
        _ctx = self._ctx
        _val = self._val
        _this = self._this

        jsargs_len, _jsargs = convert_pyargs_to_jsargs(_ctx, pyargs)
        _ret = lib.JS_Call(_ctx, _val, _this, jsargs_len, _jsargs)
        ret = convert_jsvalue_to_pyvalue(_ctx, _ret)
        ffi.release(_jsargs)

        # if isinstance(ret, QJSValue):
        #     pass
        # else:
        #     _JS_FreeValue(_ctx, _ret)

        return ret


    def free(self):
        _ctx = self._ctx
        _val = self._val
        _this = self._this
        _JS_FreeValue(_ctx, _val)
        _JS_FreeValue(_ctx, _this)


class QJSError(QJSValue, Exception):
    def __init__(self, _ctx: 'JSContext*', _val: 'JSValue', verbose: bool=False): # noqa
        self._ctx = _ctx
        self._val = _val
        self.verbose = verbose

        ctx = QJSContext.get_qjscontext(_ctx)
        ctx.add_qjsvalue(self)


    def __repr__(self) -> str:
        _ctx = self._ctx
        _val: 'JSValue' = self._val # noqa

        is_error = lib.JS_IsError(_ctx, _val)

        _c_str = _JS_ToCString(_ctx, _val)
        val = ffi.string(_c_str)
        val = val.decode()
        lib.JS_FreeCString(_ctx, _c_str)

        if self.verbose:
            return f'<{self.__class__.__name__} at {hex(id(self))} {_val.u.ptr} {is_error=} {val=}>'
        else:
            return f'<{self.__class__.__name__} at {hex(id(self))} {val!r}>'


class QJSRuntime:
    def __init__(self):
        self._rt = lib.JS_NewRuntime()
        self.ctxs: WeakSet['QJSContext'] = WeakSet()
        lib.js_std_init_handlers(self._rt)

        lib.JS_SetModuleLoaderFunc(
            self._rt,
            ffi.cast('JSModuleNormalizeFunc*', 0),
            lib.js_module_loader,
            ffi.cast('void*', 0),
        )


    def __del__(self):
        for ctx in self.ctxs:
            ctx.free()

        self.ctxs = None
        lib.js_std_free_handlers(self._rt)
        lib.JS_FreeRuntime(self._rt)


    free = __del__


    def new_context(self) -> 'QJSContext':
        ctx = QJSContext(self)
        return ctx


    def add_qjscontext(self, ctx: 'QJSContext'):
        self.ctxs.add(ctx)


    def del_qjscontext(self, ctx: 'QJSContext'):
        self.ctxs.discard(ctx)


class QJSContext:
    c_to_py_context_map: dict['Context*', 'QJSContext'] = {} # noqa


    def __init__(self, rt: QJSRuntime):
        self.rt = rt
        self._ctx = _ctx = lib.JS_NewContext(self.rt._rt)
        rt.add_qjscontext(self)
        QJSContext.set_qjscontext(_ctx, self)
        self.qjsvalues: WeakSet[QJSValue] = WeakSet()
        self.cffi_handle_rc: dict['void*', int] = {} # noqa
        lib.JS_AddIntrinsicBigFloat(_ctx)
        lib.JS_AddIntrinsicBigDecimal(_ctx)
        lib.JS_AddIntrinsicOperators(_ctx)
        lib.JS_EnableBignumExt(_ctx, True)
        lib.js_init_module_std(_ctx, b'std')
        lib.js_init_module_os(_ctx, b'os')

        # stringify object
        code = '''
        function stringifyObject(obj) {
            // Use a WeakSet for tracking seen objects to allow garbage collection
            const seen = new WeakSet();

            function stringifyHelper(obj) {
                // If we've already seen this object, return a placeholder to avoid circular reference
                if (typeof obj === 'object' && obj !== null) {
                    if (seen.has(obj)) {
                        return '[Circular]';
                    }
                    seen.add(obj);
                }

                // Handle non-object types
                if (typeof obj !== 'object' || obj === null) {
                    return JSON.stringify(obj);
                }

                // Handle arrays
                if (Array.isArray(obj)) {
                    return '[' + obj.map(stringifyHelper).join(',') + ']';
                }

                // Handle Date objects
                if (obj instanceof Date) {
                    return `"${obj.toISOString()}"`;
                }

                // Handle general objects
                let result = '{';
                let first = true;
                for (let key in obj) {
                    if (obj.hasOwnProperty(key)) {
                        if (!first) result += ',';
                        result += `"${key}":${stringifyHelper(obj[key])}`;
                        first = false;
                    }
                }
                result += '}';
                return result;
            }

            return stringifyHelper(obj);
        }

        globalThis.__stringifyObject = stringifyObject;
        '''

        _val: 'JSValue' = _JS_Eval(_ctx, code) # noqa
        _JS_FreeValue(_ctx, _val)


    def __del__(self):
        _ctx = self._ctx

        for js_val in self.qjsvalues:
            js_val.free()

        self.qjsvalues = None
        self._ctx = None
        self.rt.del_qjscontext(self)
        QJSContext.del_qjscontext(_ctx)
        lib.JS_FreeContext(_ctx)


    free = __del__


    def __getitem__(self, key: str) -> Any:
        return self.get(key)


    def __setitem__(self, key: str, value: Any):
        self.set(key, value)


    def add_qjsvalue(self, js_value: QJSValue):
        self.qjsvalues.add(js_value)


    @classmethod
    def get_qjscontext(cls, _ctx: 'Context*') -> 'QJSContext':
        ctx = cls.c_to_py_context_map[_ctx]
        return ctx


    @classmethod
    def set_qjscontext(cls, _ctx: 'Context*', ctx: 'QJSContext'):
        cls.c_to_py_context_map[_ctx] = ctx


    @classmethod
    def del_qjscontext(cls, _ctx: 'Context*'):
        del cls.c_to_py_context_map[_ctx]


    def get(self, key: str) -> Any:
        _ctx = self._ctx
        _this: 'JSValue' = lib.JS_GetGlobalObject(_ctx) # noqa
        _key = key.encode()

        _val = lib.JS_GetPropertyStr(_ctx, _this, _key)
        val = convert_jsvalue_to_pyvalue(_ctx, _val)

        if isinstance(val, QJSValue):
            self.add_qjsvalue(val)
        else:
            _JS_FreeValue(_ctx, _val)

        _JS_FreeValue(_ctx, _this)
        return val


    def set(self, key: str, val: Any):
        _ctx = self._ctx
        _this: 'JSValue' = lib.JS_GetGlobalObject(_ctx) # noqa
        _key = key.encode()
        _val = convert_pyvalue_to_jsvalue(_ctx, val)

        lib.JS_SetPropertyStr(_ctx, _this, _key, _val)

        # NOTE: do not free _val because set does not increase ref count
        #   _JS_FreeValue(_ctx, _val)
        _JS_FreeValue(_ctx, _this)


    def eval(self, buf: str, filename: str='<inupt>', eval_flags: int=JS_EVAL_TYPE_GLOBAL) -> Any:
        _ctx = self._ctx
        _val: 'JSValue' = _JS_Eval(_ctx, buf, filename, eval_flags) # noqa
        # if JS_VALUE_HAS_REF_COUNT(_val): print('*** [0]', JS_VALUE_GET_REF_COUNT(_val))
        val: Any = convert_jsvalue_to_pyvalue(_ctx, _val)

        if isinstance(val, QJSValue):
            # if JS_VALUE_HAS_REF_COUNT(_val): print('*** [1]', JS_VALUE_GET_REF_COUNT(val._val))
            self.add_qjsvalue(val)
            # if JS_VALUE_HAS_REF_COUNT(_val): print('*** [2]', JS_VALUE_GET_REF_COUNT(val._val))

        else:
            _JS_FreeValue(_ctx, _val)

        return val


    def load_script(self, path_or_url: str):
        if is_url(path_or_url):
            path = download_file_to_tempfile(path_or_url)
        else:
            path = path_or_url

        with open(path) as f:
            data: str = f.read()

        val = self.eval(data, path)
        return val
