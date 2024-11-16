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
import inspect
import tempfile
import urllib.request
from weakref import WeakSet
from typing import Any, NewType

from ._quickjs import ffi, lib


_void_p = NewType('void*', ffi.typeof('void*'))
_char_p = NewType('char*', ffi.typeof('char*'))
_JSContext = NewType('JSContext', ffi.typeof('JSContext'))
_JSContext_P = NewType('JSContext*', ffi.typeof('JSContext*'))
_JSValue = NewType('JSValue', ffi.typeof('JSValue'))
_JSValue_P = NewType('JSValue*', ffi.typeof('JSValue*'))
_JSString_P = NewType('JSString*', ffi.typeof('void*'))
_JSObject_P = NewType('JSObject*', ffi.typeof('JSObject*'))


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


def _JS_ToCString(_ctx: _JSContext_P, _val: _JSValue) -> _char_p:
    return lib._inline_JS_ToCString(_ctx, _val)


def _JS_FreeValue(_ctx: _JSContext_P, _val: _JSValue):
    lib._inline_JS_FreeValue(_ctx, _val)


def _JS_Eval(_ctx: _JSContext_P, buf: str, filename: str='<inupt>', eval_flags: int=JS_EVAL_TYPE_GLOBAL) -> Any:
    _buf: bytes = buf.encode()
    _buf_len: int = len(_buf)
    _filename: bytes = filename.encode()
    _val: _JSValue = lib.JS_Eval(_ctx, _buf, _buf_len, _filename, eval_flags)
    return _val


def convert_jsvalue_to_pystr(_ctx: _JSContext_P, _val: _JSValue) -> str:
    _c_str: _char_p = _JS_ToCString(_ctx, _val)
    val: bytes = ffi.string(_c_str)
    val: str = val.decode()
    lib.JS_FreeCString(_ctx, _c_str)
    return val


def stringify_object(_ctx: _JSContext_P, _obj: _JSValue) -> str:
    _this: _JSValue = lib.JS_GetGlobalObject(_ctx)
    _func = lib.JS_GetPropertyStr(_ctx, _this, b'__stringifyObject')
    jsargs_len = 1
    _jsargs: _JSValue_P = ffi.new('JSValue[]', [_obj])

    _val = lib.JS_Call(_ctx, _func, _this, jsargs_len, _jsargs)
    val = convert_jsvalue_to_pystr(_ctx, _val)

    ffi.release(_jsargs)
    _JS_FreeValue(_ctx, _val)
    _JS_FreeValue(_ctx, _func)
    _JS_FreeValue(_ctx, _this)
    return val


def convert_jsvalue_to_pyvalue(_ctx: _JSContext_P, _val: _JSValue) -> Any:
    is_exception: bool = lib._inline_JS_IsException(_val)

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
        val = lib._macro_JS_VALUE_GET_INT(_val)
        _JS_FreeValue(_ctx, _val)
    elif _val.tag == lib.JS_TAG_BOOL:
        val = lib._macro_JS_VALUE_GET_BOOL(_val)
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
        val = lib._macro_JS_VALUE_GET_FLOAT64(_val)
        _JS_FreeValue(_ctx, _val)
    else:
        _JS_FreeValue(_ctx, _val)
        raise NotImplementedError('JS_NAN_BOXING')

    return val


def convert_pyargs_to_jsargs(_ctx: _JSContext_P, pyargs: list[Any]) -> (int, _JSValue):
    _filename: _char_p = ffi.cast(_char_p, 0)
    val_length = len(pyargs)
    _val = [convert_pyvalue_to_jsvalue(_ctx, n) for n in pyargs]
    _val = ffi.new('JSValue[]', _val)
    return val_length, _val


def convert_pyvalue_to_jsvalue(_ctx: _JSContext_P, val: Any) -> _JSValue:
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
            _n: _JSValue = convert_pyvalue_to_jsvalue(_ctx, n)
            _n_p: _JSValue_P = ffi.new('JSValue[]', [_n])

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
            _v: _JSValue = convert_pyvalue_to_jsvalue(_ctx, v)

            lib.JS_SetPropertyStr(_ctx, _val, _k, _v)

            # NOTE: line below is not required based on JS_SetPropertyStr logic
            #   _JS_FreeValue(_ctx, _v)
    elif callable(val):
        val_handler: _void_p = ffi.new_handle(val)
        _c_temp.add(val_handler)
        _val_handler: _JSValue = lib._macro_JS_MKPTR(lib.JS_TAG_OBJECT, val_handler)
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
    _val_handler: _JSValue = _func_data[0]
    _val_p: _void_p = lib._macro_JS_VALUE_GET_PTR(_val_handler)
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
    def __init__(self, _ctx: _JSContext_P, _val: _JSValue=None):
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
    def __init__(self, _ctx: _JSContext_P, _val: _JSValue=None, _this: _JSValue=None):
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
    def __init__(self, _ctx: _JSContext_P, _val: _JSValue, verbose: bool=False):
        self._ctx = _ctx
        self._val = _val
        self.verbose = verbose

        ctx = QJSContext.get_qjscontext(_ctx)
        ctx.add_qjsvalue(self)


    def __repr__(self) -> str:
        _ctx = self._ctx
        _val: _JSValue = self._val

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
    c_to_py_context_map: dict[_JSContext_P, 'QJSContext'] = {}


    def __init__(self, rt: QJSRuntime):
        self.rt = rt
        self._ctx = _ctx = lib.JS_NewContext(self.rt._rt)
        rt.add_qjscontext(self)
        QJSContext.set_qjscontext(_ctx, self)
        self.qjsvalues: WeakSet[QJSValue] = WeakSet()
        self.cffi_handle_rc: dict[_void_p, int] = {}
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

        _val: _JSValue = _JS_Eval(_ctx, code)
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
    def get_qjscontext(cls, _ctx: _JSContext_P) -> 'QJSContext':
        ctx = cls.c_to_py_context_map[_ctx]
        return ctx


    @classmethod
    def set_qjscontext(cls, _ctx: _JSContext_P, ctx: 'QJSContext'):
        cls.c_to_py_context_map[_ctx] = ctx


    @classmethod
    def del_qjscontext(cls, _ctx: _JSContext_P):
        del cls.c_to_py_context_map[_ctx]


    def get(self, key: str) -> Any:
        _ctx = self._ctx
        _this: _JSValue = lib.JS_GetGlobalObject(_ctx)
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
        _this: _JSValue = lib.JS_GetGlobalObject(_ctx)
        _key = key.encode()
        _val = convert_pyvalue_to_jsvalue(_ctx, val)

        lib.JS_SetPropertyStr(_ctx, _this, _key, _val)

        # NOTE: do not free _val because set does not increase ref count
        #   _JS_FreeValue(_ctx, _val)
        _JS_FreeValue(_ctx, _this)


    def eval(self, buf: str, filename: str='<inupt>', eval_flags: int=JS_EVAL_TYPE_GLOBAL) -> Any:
        _ctx = self._ctx
        _val: _JSValue = _JS_Eval(_ctx, buf, filename, eval_flags)
        if lib._macro_JS_VALUE_HAS_REF_COUNT(_val): print('*** [0]', lib._macro_JS_VALUE_GET_REF_COUNT(_val))
        val: Any = convert_jsvalue_to_pyvalue(_ctx, _val)

        if isinstance(val, QJSValue):
            if lib._macro_JS_VALUE_HAS_REF_COUNT(_val): print('*** [1]', lib._macro_JS_VALUE_GET_REF_COUNT(val._val))
            self.add_qjsvalue(val)
            if lib._macro_JS_VALUE_HAS_REF_COUNT(_val): print('*** [2]', lib._macro_JS_VALUE_GET_REF_COUNT(val._val))

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
