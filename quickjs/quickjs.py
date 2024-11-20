__all__ = [
    'JSTag',
    'JSEval',
    'JSRuntime',
    'JSContext',
    'JSError',
]

import os
import re
import inspect
import tempfile
import urllib.request
from enum import Enum
from weakref import WeakSet
from typing import Any, NewType

from ._quickjs import ffi, lib


_void_p = NewType('void*', ffi.typeof('void*'))
_char_p = NewType('char*', ffi.typeof('char*'))
_const_char_p = NewType('const char*', ffi.typeof('const char*'))
_JSContext = NewType('JSContext', ffi.typeof('JSContext'))
_JSContext_P = NewType('JSContext*', ffi.typeof('JSContext*'))
_JSValue = NewType('JSValue', ffi.typeof('JSValue'))
_JSValue_P = NewType('JSValue*', ffi.typeof('JSValue*'))
_JSValueConst = NewType('JSValueConst', ffi.typeof('JSValue'))
_JSValueConst_P = NewType('JSValueConst*', ffi.typeof('JSValue*'))
_JSString_P = NewType('JSString*', ffi.typeof('void*'))
_JSObject_P = NewType('JSObject*', ffi.typeof('JSObject*'))
_JSModuleDef = NewType('JSModuleDef', ffi.typeof('JSModuleDef'))
_JSModuleDef_P = NewType('JSModuleDef*', ffi.typeof('JSModuleDef*'))


_c_temp: set[Any] = set()

# Regular expression pattern to match URLs
url_pattern = re.compile(r'^(?:http|ftp|https)://')

# /* all tags with a reference count are negative */
JS_TAG_FIRST       = -11 # /* first negative tag */
JS_TAG_BIG_DECIMAL = -11
JS_TAG_BIG_INT     = -10
JS_TAG_BIG_FLOAT   = -9
JS_TAG_SYMBOL      = -8
JS_TAG_STRING      = -7
JS_TAG_MODULE      = -3 # /* used internally */
JS_TAG_FUNCTION_BYTECODE = -2 # /* used internally */
JS_TAG_OBJECT      = -1
JS_TAG_INT         = 0
JS_TAG_BOOL        = 1
JS_TAG_NULL        = 2
JS_TAG_UNDEFINED   = 3
JS_TAG_UNINITIALIZED = 4
JS_TAG_CATCH_OFFSET = 5
JS_TAG_EXCEPTION   = 6
JS_TAG_FLOAT64     = 7
# /* any larger tag is FLOAT64 if JS_NAN_BOXING */


class JSTag(Enum):
    FIRST = JS_TAG_FIRST
    BIG_DECIMAL = JS_TAG_BIG_DECIMAL
    BIG_INT = JS_TAG_BIG_INT
    BIG_FLOAT = JS_TAG_BIG_FLOAT
    SYMBOL = JS_TAG_SYMBOL
    STRING = JS_TAG_STRING
    MODULE = JS_TAG_MODULE
    FUNCTION_BYTECODE = JS_TAG_FUNCTION_BYTECODE
    OBJECT = JS_TAG_OBJECT
    INT = JS_TAG_INT
    BOOL = JS_TAG_BOOL
    NULL = JS_TAG_NULL
    UNDEFINED = JS_TAG_UNDEFINED
    UNINITIALIZED = JS_TAG_UNINITIALIZED
    CATCH_OFFSET = JS_TAG_CATCH_OFFSET
    EXCEPTION = JS_TAG_EXCEPTION
    FLOAT64 = JS_TAG_FLOAT64


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


class JSEval(Enum):
    TYPE_GLOBAL = JS_EVAL_TYPE_GLOBAL
    TYPE_MODULE = JS_EVAL_TYPE_MODULE
    TYPE_DIRECT = JS_EVAL_TYPE_DIRECT
    TYPE_INDIRECT = JS_EVAL_TYPE_INDIRECT
    TYPE_MASK = JS_EVAL_TYPE_MASK
    FLAG_STRICT = JS_EVAL_FLAG_STRICT
    FLAG_STRIP = JS_EVAL_FLAG_STRIP
    FLAG_COMPILE_ONLY = JS_EVAL_FLAG_COMPILE_ONLY
    FLAG_BACKTRACE_BARRIER = JS_EVAL_FLAG_BACKTRACE_BARRIER
    FLAG_ASYNC = JS_EVAL_FLAG_ASYNC


# special values
JS_NULL: _JSValue = lib._macro_JS_MKVAL(JSTag.NULL.value, 0)
JS_UNDEFINED: _JSValue = lib._macro_JS_MKVAL(JSTag.UNDEFINED.value, 0)
JS_FALSE: _JSValue = lib._macro_JS_MKVAL(JSTag.BOOL.value, 0)
JS_TRUE: _JSValue = lib._macro_JS_MKVAL(JSTag.BOOL.value, 1)
JS_EXCEPTION: _JSValue = lib._macro_JS_MKVAL(JSTag.EXCEPTION.value, 0)
JS_UNINITIALIZED: _JSValue = lib._macro_JS_MKVAL(JSTag.UNINITIALIZED.value, 0)


def _JS_ToCString(_ctx: _JSContext_P, _val: _JSValue) -> _char_p:
    return lib._inline_JS_ToCString(_ctx, _val)


def _JS_DupValue(_ctx: _JSContext_P, _val: _JSValue):
    # p->ref_count++
    lib._inline_JS_DupValue(_ctx, _val)

def _JS_FreeValue(_ctx: _JSContext_P, _val: _JSValue):
    # --p->ref_count, and possibly free
    lib._inline_JS_FreeValue(_ctx, _val)


def _JS_Eval(_ctx: _JSContext_P, buf: str, filename: str='<inupt>', eval_flags: int | JSEval=JSEval.TYPE_GLOBAL) -> Any:
    eval_flags = eval_flags if isinstance(eval_flags, int) else eval_flags.value
    _buf: bytes = buf.encode()
    _buf_len: int = len(_buf)
    _filename: bytes = filename.encode()
    _val: _JSValue = lib.JS_Eval(_ctx, _buf, _buf_len, _filename, eval_flags)
    return _val


def stringify_object(_ctx: _JSContext_P, _obj: _JSValue) -> str:
    _this: _JSValue = lib.JS_GetGlobalObject(_ctx)
    _func = lib.JS_GetPropertyStr(_ctx, _this, b'__stringifyObject')
    jsargs_len = 1
    _jsargs: _JSValue_P = ffi.new('JSValue[]', [_obj])

    _val = lib.JS_Call(_ctx, _func, _this, jsargs_len, _jsargs)
    _c_str: _char_p = _JS_ToCString(_ctx, _val)
    val: bytes = ffi.string(_c_str)
    val: str = val.decode()
    lib.JS_FreeCString(_ctx, _c_str)

    ffi.release(_jsargs)
    _JS_FreeValue(_ctx, _val)
    _JS_FreeValue(_ctx, _func)
    _JS_FreeValue(_ctx, _this)
    return val


def convert_jsvalue_to_pyvalue(_ctx: _JSContext_P, _val: _JSValue, _this: _JSValue=JS_UNDEFINED) -> Any:
    is_exception: bool = lib._inline_JS_IsException(_val)

    if is_exception:
        # NOTE: use to debug internal JS errors
        #   lib.js_std_dump_error(_ctx)
        _e_val = lib.JS_GetException(_ctx)
        e = JSError(_ctx, _e_val)
        _JS_FreeValue(_ctx, _val)
        raise e

    if _val.tag == lib.JS_TAG_FIRST:
        raise NotImplementedError('JS_TAG_FIRST')
    elif _val.tag == lib.JS_TAG_BIG_DECIMAL:
        raise NotImplementedError('JS_TAG_BIG_DECIMAL')
    elif _val.tag == lib.JS_TAG_BIG_INT:
        val = JSBigInt(_ctx, _val)
    elif _val.tag == lib.JS_TAG_BIG_FLOAT:
        raise NotImplementedError('JS_TAG_BIG_FLOAT')
    elif _val.tag == lib.JS_TAG_SYMBOL:
        val = JSSymbol(_ctx, _val)
    elif _val.tag == lib.JS_TAG_STRING:
        val = JSString(_ctx, _val)
    elif _val.tag == lib.JS_TAG_MODULE:
        raise NotImplementedError('JS_TAG_MODULE')
    elif _val.tag == lib.JS_TAG_FUNCTION_BYTECODE:
        raise NotImplementedError('JS_TAG_FUNCTION_BYTECODE')
    elif _val.tag == lib.JS_TAG_OBJECT:
        if lib.JS_IsFunction(_ctx, _val):
            val = JSFunction(_ctx, _val, _this)
        elif lib.JS_IsArray(_ctx, _val):
            val = JSArray(_ctx, _val)
        else:
            val = JSObject(_ctx, _val) # Object, Map, Set, etc
    elif _val.tag == lib.JS_TAG_INT:
        val = lib._macro_JS_VALUE_GET_INT(_val)
    elif _val.tag == lib.JS_TAG_BOOL:
        val: int = lib._macro_JS_VALUE_GET_BOOL(_val)
        val: bool = bool(val)
    elif _val.tag == lib.JS_TAG_NULL:
        val = None
    elif _val.tag == lib.JS_TAG_UNDEFINED:
        val = JSUndefined(_ctx, _val)
    elif _val.tag == lib.JS_TAG_UNINITIALIZED:
        raise NotImplementedError('JS_TAG_CATCH_OFFSET')
    elif _val.tag == lib.JS_TAG_CATCH_OFFSET:
        raise NotImplementedError('JS_TAG_CATCH_OFFSET')
    elif _val.tag == lib.JS_TAG_EXCEPTION:
        # FIXME: handle exception
        raise NotImplementedError('JS_TAG_EXCEPTION')
    elif _val.tag == lib.JS_TAG_FLOAT64:
        val = lib._macro_JS_VALUE_GET_FLOAT64(_val)
    else:
        _JS_FreeValue(_ctx, _val)
        raise NotImplementedError('JS_NAN_BOXING')

    return val


def convert_pyvalue_to_jsvalue(_ctx: _JSContext_P, val: Any) -> _JSValue:
    if val is None:
        _val = JS_NULL
    elif isinstance(val, JSValue):
        _val = val._val
    elif isinstance(val, bool):
        _val = JS_TRUE if val else JS_FALSE
    elif isinstance(val, int):
        assert -2 ** 31 <= val < 2 ** 31
        _val = lib._macro_JS_MKVAL(JSTag.INT.value, val)
        # _val = _JS_Eval(_ctx, f'{val}')
    elif isinstance(val, float):
        _val = lib._inline___JS_NewFloat64(_ctx, val)
    elif isinstance(val, str):
        _val = lib.JS_NewString(_ctx, val.encode())
    elif isinstance(val, (list, tuple)):
        _val = lib.JS_NewArray(_ctx)
        _Array_push_atom = lib.JS_NewAtom(_ctx, b'push')

        for n in val:
            _n: _JSValue = convert_pyvalue_to_jsvalue(_ctx, n)
            _n_p: _JSValue_P = ffi.new('JSValue[]', [_n])

            lib.JS_Invoke(_ctx, _val, _Array_push_atom, 1, _n_p)

            ffi.release(_n_p)
            _JS_FreeValue(_ctx, _n)

        lib.JS_FreeAtom(_ctx, _Array_push_atom)
    elif isinstance(val, dict):
        _val = lib.JS_NewObject(_ctx)

        for k, v in val.items():
            assert isinstance(k, str)
            _k: bytes = k.encode()
            _v: _JSValue = convert_pyvalue_to_jsvalue(_ctx, v)

            lib.JS_SetPropertyStr(_ctx, _val, _k, _v)

            # NOTE: line below is not required based on JS_SetPropertyStr logic
            #   _JS_FreeValue(_ctx, _v)
    elif callable(val):
        val_handler: _void_p = ffi.new_handle(val)
        _c_temp.add(val_handler)
        _val_handler: _JSValue = lib._macro_JS_MKPTR(lib.JS_TAG_OBJECT, val_handler)
        # _c_temp.add(_val_handler)

        # val2 = JSValue(_ctx, _val_handler)

        _func = lib._quikcjs_cffi_py_func_wrap
        _length = len(inspect.signature(val).parameters)
        _magic = 0
        _data_len = 1
        _data = ffi.addressof(_val_handler)
        # _data = ffi.new('JSValue[]', [_val_handler])
        _val = lib.JS_NewCFunctionData(_ctx, _func, _length, _magic, _data_len, _data)

        # val2 = JSValue(_ctx, _val)
    else:
        raise ValueError(f'Unsupported Python value {type(val)}')

    # _c_temp.add(_val) # ???
    return _val


# typedef JSValue JSCFunctionData(JSContext *ctx, JSValueConst this_val, int argc, JSValueConst *argv, int magic, JSValue *func_data);
@ffi.def_extern()
def _quikcjs_cffi_py_func_wrap(_ctx: _JSContext_P, _this_val: _JSValueConst, _argc: int, _argv: _JSValueConst_P, _magic: int, _func_data: _JSValue_P):
    _val_handler: _JSValue = _func_data[0]
    _val_p: _void_p = lib._macro_JS_VALUE_GET_PTR(_val_handler)
    val_handler = ffi.from_handle(_val_p)
    py_func = val_handler

    _jsargs = [_argv[i] for i in range(_argc)]

    # NOTE: this is necessary to inc ref_count, so GC does not clean JS objects during function call
    for _jsarg in _jsargs:
        _JS_DupValue(_ctx, _jsarg)

    # pyargs = [_argv[i] for i in range(_argc)]
    # pyargs = [convert_jsvalue_to_pyvalue(_ctx, n) for n in pyargs]
    pyargs = [convert_jsvalue_to_pyvalue(_ctx, _jsarg) for _jsarg in _jsargs]
    ret = py_func(*pyargs)
    _ret = convert_pyvalue_to_jsvalue(_ctx, ret)

    _c_temp.discard(_val_p)
    return _ret


def download_file_to_tempfile(url: str) -> str:
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        with urllib.request.urlopen(url) as response:
            temp_file.write(response.read())
            temp_file.seek(0)

        # print(f'download_file_to_tempfile {temp_file.name=}')
        return temp_file.name


def read_script(path_or_url: str, is_remote_file: bool=False) -> tuple[str, str]:
    if is_remote_file:
        path = download_file_to_tempfile(path_or_url)
    elif path_or_url.startswith('http://') or path_or_url.startswith('https://'):
        path = download_file_to_tempfile(path_or_url)
    elif os.path.exists(path_or_url):
        path = path_or_url
    else:
        for ext in ['', '.js', '.mjs']:
            p = os.path.join('node_modules', path_or_url + ext)

            if os.path.exists(p):
                path = p
                break
        else:
            raise ValueError(path_or_url)

    with open(path) as f:
        data: str = f.read()

    return path, data


# JSModuleDef *js_module_loader(JSContext *ctx, const char *module_name, void *opaque);
@ffi.def_extern()
def _quikcjs_cffi_js_module_loader(_ctx: _JSContext_P, _module_name: _const_char_p, _opaque: _void_p) -> _JSModuleDef_P:
    # print(f'!!! _quikcjs_cffi_js_module_loader {_ctx=} {ffi.string(_module_name)=} {_opaque=}')
    module_name: bytes = ffi.string(_module_name)
    module_name: str = module_name.decode()
    is_remote_file: bool = module_name.startswith('http://') or module_name.startswith('https://')
    # print(f'_quikcjs_cffi_js_module_loader [0] {module_name=} {is_remote_file=}')

    path: str
    data: str
    path, data = read_script(module_name, is_remote_file)
    _path: bytes = path.encode()

    _module_def: _JSModuleDef_P = lib.js_module_loader(_ctx, _path, _opaque)
    # print(f'_quikcjs_cffi_js_module_loader [1] {path=} {_module_def=}')
    return _module_def


class JSRuntime:
    def __init__(self):
        self._rt = lib.JS_NewRuntime()
        self.ctxs: WeakSet['JSContext'] = WeakSet()
        lib.js_std_init_handlers(self._rt)

        lib.JS_SetModuleLoaderFunc(
            self._rt,
            ffi.cast('JSModuleNormalizeFunc*', 0),
            # lib.js_module_loader,
            lib._quikcjs_cffi_js_module_loader,
            ffi.cast('void*', 0),
        )


    def __del__(self):
        for ctx in self.ctxs:
            ctx.free()

        self.ctxs = None
        lib.js_std_free_handlers(self._rt)
        lib.JS_FreeRuntime(self._rt)


    free = __del__


    def new_context(self) -> 'JSContext':
        ctx = JSContext(self)
        return ctx


    def add_qjscontext(self, ctx: 'JSContext'):
        self.ctxs.add(ctx)


    def del_qjscontext(self, ctx: 'JSContext'):
        self.ctxs.discard(ctx)


class JSContext:
    c_to_py_context_map: dict[_JSContext_P, 'JSContext'] = {}


    def __init__(self, rt: JSRuntime):
        self.rt = rt
        self._ctx = _ctx = lib.JS_NewContext(self.rt._rt)
        rt.add_qjscontext(self)
        JSContext.set_qjscontext(_ctx, self)
        self.qjsvalues: WeakSet[JSValue] = WeakSet()
        self.cffi_handle_rc: dict[_void_p, int] = {}
        lib.JS_AddIntrinsicBigFloat(_ctx)
        lib.JS_AddIntrinsicBigDecimal(_ctx)
        lib.JS_AddIntrinsicOperators(_ctx)
        lib.JS_EnableBignumExt(_ctx, True)
        lib.js_init_module_std(_ctx, b'std')
        lib.js_init_module_os(_ctx, b'os')

        # stringify object
        code = '''
        /*
         * crypto - minimal polyfill for Yjs
         */
        if (!globalThis.crypto) {
            globalThis.crypto = {
                getRandomValues: function(array) {
                    for (let i = 0; i < array.length; i++) {
                        array[i] = Math.floor(Math.random() * 256);
                    }

                    return array;
                }
            };
        }

        /*
         * browser console.log/toString like polyfill
         */
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

                // Handle Symbol type
                if (typeof obj === 'symbol') {
                    return `"${obj.description || obj.toString()}"`;
                }

                // Handle BigInt
                if (typeof obj === 'bigint') {
                    return obj.toString(); // NOTE: 'n' at the end is not returned
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

        if (!globalThis.__stringifyObject) {
            globalThis.__stringifyObject = stringifyObject;
        }
        '''

        _val: _JSValue = _JS_Eval(_ctx, code)
        _JS_FreeValue(_ctx, _val)


    def __del__(self):
        _ctx = self._ctx

        for js_val in self.qjsvalues:
            js_val.free()

        self.qjsvalues = None
        self._ctx = None
        self.rt.del_qjscontext(self)
        JSContext.del_qjscontext(_ctx)
        lib.JS_FreeContext(_ctx)


    free = __del__


    def __getitem__(self, key: str) -> Any:
        return self.get(key)


    def __setitem__(self, key: str, value: Any):
        self.set(key, value)


    def add_qjsvalue(self, js_value: 'JSValue'):
        self.qjsvalues.add(js_value)


    @classmethod
    def get_qjscontext(cls, _ctx: _JSContext_P) -> 'JSContext':
        ctx = cls.c_to_py_context_map[_ctx]
        return ctx


    @classmethod
    def set_qjscontext(cls, _ctx: _JSContext_P, ctx: 'JSContext'):
        cls.c_to_py_context_map[_ctx] = ctx


    @classmethod
    def del_qjscontext(cls, _ctx: _JSContext_P):
        del cls.c_to_py_context_map[_ctx]


    def get(self, key: str) -> Any:
        _ctx = self._ctx
        _this: _JSValue = lib.JS_GetGlobalObject(_ctx)
        _key = key.encode()
        _key_atom = lib.JS_NewAtom(_ctx, _key)

        _val = lib._inline_JS_GetProperty(_ctx, _this, _key_atom)
        val = convert_jsvalue_to_pyvalue(_ctx, _val)

        if isinstance(val, JSValue):
            self.add_qjsvalue(val)

        lib.JS_FreeAtom(_ctx, _key_atom)
        _JS_FreeValue(_ctx, _this)
        return val


    def set(self, key: str, val: Any):
        _ctx = self._ctx
        _this: _JSValue = lib.JS_GetGlobalObject(_ctx)
        _key = key.encode()
        _key_atom = lib.JS_NewAtom(_ctx, _key)
        _val = convert_pyvalue_to_jsvalue(_ctx, val)

        lib._inline_JS_SetProperty(_ctx, _this, _key_atom, _val)

        # NOTE: do not free _val because set does not increase ref count
        # _JS_FreeValue(_ctx, _val)
        lib.JS_FreeAtom(_ctx, _key_atom)
        _JS_FreeValue(_ctx, _this)


    def eval(self, buf: str, filename: str='<inupt>', eval_flags: JSEval | int=JSEval.TYPE_GLOBAL) -> Any:
        eval_flags = eval_flags if isinstance(eval_flags, int) else eval_flags.value
        _ctx = self._ctx

        _val: _JSValue = _JS_Eval(_ctx, buf, filename, eval_flags)
        # lib.js_std_dump_error(_ctx)

        val: Any = convert_jsvalue_to_pyvalue(_ctx, _val)

        if isinstance(val, JSValue):
            self.add_qjsvalue(val)

        return val


    def load(self, path_or_url: str, eval_flags: JSEval | int=JSEval.TYPE_GLOBAL) -> Any:
        path: str
        data: str
        path, data = read_script(path_or_url)
        val: Any = self.eval(data, path, eval_flags)
        return val


class JSValue:
    def __init__(self, _ctx: _JSContext_P, _val: _JSValue=None):
        self._ctx = _ctx
        self._val = _val

        ctx = JSContext.get_qjscontext(_ctx)
        ctx.add_qjsvalue(self)


    def __del__(self):
        # print('JSValue.__del__', self)
        _ctx = self._ctx
        _val = self._val
        _rt = lib.JS_GetRuntime(_ctx)

        if lib.JS_IsLiveObject(_rt, _val):
            _JS_FreeValue(_ctx, _val)


    free = __del__


    def __repr__(self) -> str:
        _ctx = self._ctx
        _val = self._val
        tag = JSTag(_val.tag)
        val: str = stringify_object(_ctx, _val)

        if lib._macro_JS_VALUE_HAS_REF_COUNT(_val):
            ref_count: int = lib._macro_JS_VALUE_GET_REF_COUNT(_val)

            if lib.JS_IsFunction(_ctx, _val):
                return f'<{self.__class__.__name__} at {hex(id(self))} tag={tag.name} ptr={_val.u.ptr} {ref_count=}>'
            else:
                return f'<{self.__class__.__name__} at {hex(id(self))} tag={tag.name} ptr={_val.u.ptr} {ref_count=} val={val}>'
        else:
            return f'<{self.__class__.__name__} at {hex(id(self))} tag={tag.name} val={val}>'


    def __getattr__(self, attr: str) -> Any:
        _ctx = self._ctx
        _val = self._val
        _attr: bytes = attr.encode()
        _ret = lib.JS_GetPropertyStr(_ctx, _val, _attr)
        ret: Any = convert_jsvalue_to_pyvalue(_ctx, _ret, _val)
        return ret



class JSUndefined(JSValue):
    pass


class JSBigInt(JSValue):
    pass


class JSString(JSValue):
    def __str__(self) -> str:
        _ctx = self._ctx
        _val = self._val
        val: str = stringify_object(_ctx, _val)
        return val


class JSSymbol(JSValue):
    pass


class JSArray(JSValue):
    pass


class JSObject(JSValue):
    pass


class JSFunction(JSValue):
    def __init__(self, _ctx: _JSContext_P, _val: _JSValue=None, _this: _JSValue=JS_UNDEFINED):
        self._ctx = _ctx
        self._val = _val
        self._this = _this # NOTE: this might be useful lib.JS_GetGlobalObject(_ctx)

        # NOTE: required so GC does not collect it
        _JS_DupValue(_ctx, _this)

        ctx = JSContext.get_qjscontext(_ctx)
        ctx.add_qjsvalue(self)


    def __call__(self, *pyargs) -> Any:
        _ctx = self._ctx
        _val = self._val
        _this = self._this
        # print(f'JSFunction.__call__ {_val=} {_val.tag=} {lib.JS_IsFunction(_ctx, _val)=} {lib._macro_JS_VALUE_GET_REF_COUNT(_val)=}')

        _jsargs_len: int = len(pyargs)
        _jsargs = [convert_pyvalue_to_jsvalue(_ctx, n) for n in pyargs]
        # print(f'{_jsargs_len=} {_jsargs=}', [n.tag for n in _jsargs], [n.u.int32 for n in _jsargs])

        # NOTE: this is necessary to inc ref_count, so GC does not clean JS objects during function call
        _JS_DupValue(_ctx, _val)
        _JS_DupValue(_ctx, _this)

        for _jsarg in _jsargs:
            _JS_DupValue(_ctx, _jsarg)

        _jsargs_a: _JSValue_P = ffi.new('JSValue[]', _jsargs)

        _ret: _JSValue = lib.JS_Call(_ctx, _val, _this, _jsargs_len, _jsargs_a)
        ret = convert_jsvalue_to_pyvalue(_ctx, _ret)
        # print(f'JSFunction.__call__ {_ret=} {_ret.tag=} {lib.JS_IsArray(_ctx, _ret)=} {lib._macro_JS_VALUE_GET_REF_COUNT(_ret)=}')
        # print(f'JSFunction.__call__ {ret=}')

        ffi.release(_jsargs_a)
        _JS_FreeValue(_ctx, _this)
        _JS_FreeValue(_ctx, _val)
        return ret


    def __del__(self):
        # print('JSFunction.__del__', self)
        _ctx = self._ctx
        _val = self._val
        _this = self._this
        _rt = lib.JS_GetRuntime(_ctx)

        if lib.JS_IsLiveObject(_rt, _val):
            _JS_FreeValue(_ctx, _val)

        if lib._inline_JS_IsObject(_this) and lib.JS_IsLiveObject(_rt, _this):
            _JS_FreeValue(_ctx, _this)


    free = __del__


class JSError(JSValue, Exception):
    def __init__(self, _ctx: _JSContext_P, _val: _JSValue):
        super().__init__(_ctx, _val)


    def __str__(self) -> str:
        return repr(self)


    def __repr__(self) -> str:
        _ctx = self._ctx
        _val: _JSValue = self._val
        tag = JSTag(_val.tag)

        # ???
        # is_error = lib.JS_IsError(_ctx, _val)

        _c_str = _JS_ToCString(_ctx, _val)
        val = ffi.string(_c_str) # ???
        val = val.decode()
        lib.JS_FreeCString(_ctx, _c_str)

        ref_count: int = lib._macro_JS_VALUE_GET_REF_COUNT(_val)
        return f'<{self.__class__.__name__} at {hex(id(self))} tag={tag.name} ptr={_val.u.ptr} {ref_count=} val={val!r}>'
