import os
import re
import glob
import shutil
import subprocess
from pprint import pprint

from cffi import FFI

from clean import clean


# if 'PYODIDE' in env and env['PYODIDE'] == '1':
#     env['CXXFLAGS'] += ' -msimd128 -fno-rtti -DNDEBUG -flto=full -s INITIAL_MEMORY=2GB -s MAXIMUM_MEMORY=4GB -s ALLOW_MEMORY_GROWTH '
#     env['UNAME_M'] = 'wasm'


def add_prefix_to_function(func_signature: str, prefix: str) -> str:
    # Regular expression pattern to match C function declarations
    pattern = r"""
        (\b[\w\s\*\(\)\[\],]*?)         # Match the return type (words, spaces, pointers, arrays, commas)
        \s*                             # Optional whitespace before the function name
        (\b\w+\b)                       # Match the function name (capturing group for renaming)
        \s*                             # Optional whitespace after the function name
        (\([^)]*?)                      # Match the function parameters (open parentheses but not mandatory closed)
        (\s*__attribute__\s*\(\(.*?\)\))? # Optionally match __attribute__((...)) syntax
        \s*                             # Optional whitespace
        (?=$|;|\n|\))                   # Lookahead for end of line, semicolon, or closing parenthesis
    """

    # Replacement function to add prefix to the function name
    def replacer(match):
        return f"{match.group(1)} {prefix}{match.group(2)}{match.group(3)}{match.group(4) or ''}"

    # Substitute using the pattern and replacement function
    return re.sub(pattern, replacer, func_signature, flags=re.VERBOSE)


def get_func_declarations(source_code: str) -> list[str]:
    def remove_comments(code: str) -> str:
        # Remove multi-line comments
        code = re.sub(r'/\*[^*]*\*+(?:[^/*][^*]*\*+)*/', '', code)
        # Remove single-line comments
        code = re.sub(r'//[^\n]*', '', code)
        return code

    def find_matching_brace(code: str, start: int) -> int:
        """Find the matching closing brace considering nested blocks"""
        count = 1
        i = start

        while i < len(code) and count > 0:
            if code[i] == '{':
                count += 1
            elif code[i] == '}':
                count -= 1

            i += 1

        return i - 1 if count == 0 else -1

    def extract_declarations(code: str) -> list[tuple]:
        results = []
        i = 0

        while i < len(code):
            # Find potential function start
            match = re.search(r'''
                # Return type
                (?:(?:static|extern|inline|const|volatile|unsigned|signed|struct|enum|union|long|short)\s+)*
                [\w_]+                    # Base type
                (?:\s*\*\s*|\s+)         # Pointers or whitespace
                (?:const\s+)*            # Optional const after pointer
                # Function name
                ([\w_]+)                 # Capture function name
                \s*
                # Parameters
                \(
                ((?:[^()]*|\([^()]*\))*)  # Parameters allowing one level of nested parentheses
                \)
                \s*
                (?:{|;)                   # Either opening brace or semicolon
            ''', code[i:], re.VERBOSE)

            if not match:
                break

            start = i + match.start()
            end = i + match.end()

            # Get everything before the function name to extract return type
            func_start = code[i:].find(match.group(1), match.start())
            return_type = code[start:i + func_start].strip()

            # If we found an opening brace, find its matching closing brace
            if code[end-1] == '{':
                closing_brace = find_matching_brace(code, end)

                if closing_brace == -1:
                    break
                # Skip the entire function body
                i = closing_brace + 1
            else:
                i = end

            results.append((return_type, match.group(1), match.group(2)))

        return results

    # Remove comments and normalize whitespace
    source_code = remove_comments(source_code)

    # Extract declarations
    declarations = []

    for return_type, func_name, params in extract_declarations(source_code):
        # Clean up parameters
        params = re.sub(r'\s+', ' ', params.strip())
        # Create declaration
        declaration = f"{return_type} {func_name}({params});"
        declaration = re.sub(r'\s+', ' ', declaration)
        declarations.append(declaration)

    return declarations


def clone_quickjs_repo():
    subprocess.run(['git', 'clone', 'https://github.com/bellard/quickjs.git', 'quickjs-repo'], check=True)


def build_quickjs_repo(*args, **kwargs):
    # build static and shared library
    env = os.environ.copy()
    print('build:')
    pprint(env)

    #
    # build llama.cpp
    #
    env['CFLAGS'] = '-fPIC -ffunction-sections -fdata-sections'
    subprocess.run(['make', '-C', 'quickjs-repo', 'qjs'], check=True, env=env)

    #
    # cffi
    #
    ffibuilder = FFI()

    _source: str = subprocess.check_output(['gcc', '-E', '_quickjs_lib.h'], text=True, env=env)

    _source = '\n'.join([
        line
        for line in [n.rstrip() for n in _source.splitlines()]
        if line
    ])

    # filter out non-quickjs code
    _quickjs_source: list[str] | str = []
    is_quickjs_code = False

    for i, line in enumerate(_source.splitlines()):
        if line.startswith('#'):
            if 'quickjs-repo' in line:
                is_quickjs_code = True
            else:
                is_quickjs_code = False

            continue

        if is_quickjs_code:
            _quickjs_source.append(line)

    _source = '\n'.join(_quickjs_source)

    # filter our attribute code
    _quickjs_source: list[str] | str = []
    scope = 0

    for i, line in enumerate(_source.splitlines()):
        if '__attribute__' in line:
            scope = 0

            for j in range(line.index('__attribute__') + len('__attribute__'), len(line)):
                if line[j] == '(':
                    scope += 1
                    continue
                elif line[j] == ')':
                    scope -= 1

                if scope == 0:
                    line = line[:line.index('__attribute__')] + line[j + 1:]
                    break

        _quickjs_source.append(line)

    _source = '\n'.join(_quickjs_source)

    # filter our static inline code
    _inline_static_source: list[str] | str = []
    _quickjs_source: list[str] | str = []
    is_static_inline_code = False
    is_static_inline_block = False
    scope = 0

    for i, line in enumerate(_source.splitlines()):
        if line.startswith('static inline'):
            is_static_inline_code = True
            is_static_inline_block = '{' in line
            scope = line.count('{')
            scope -= line.count('}')

            line = line[len('static inline '):]
            # print('! ', line)
            line = add_prefix_to_function(line, '_inline_')
            # print('!!', line)
            _inline_static_source.append(line)
            continue

        if is_static_inline_code:
            _inline_static_source.append(line)

            if not is_static_inline_block:
                is_static_inline_block = '{' in line

            scope += line.count('{')
            scope -= line.count('}')

            if is_static_inline_block and scope == 0:
                is_static_inline_code = False
                is_static_inline_block = False
                continue
        else:
            _quickjs_source.append(line)

    _source = '\n'.join(_quickjs_source)
    _inline_static_source = '\n'.join(_inline_static_source)

    print('='* 80)
    print(_inline_static_source)
    print('='* 80)

    # function declarations for inlined definitions
    func_declarations: list[str] | str = get_func_declarations(_inline_static_source)
    func_declarations = '\n'.join(func_declarations)
    print('-'* 80)
    print(func_declarations)
    print('-'* 80)
    _source += '\n\n' + func_declarations

    # extra source declarations
    _source += '\n\n' + '''
    typedef JSValue JSValueConst;

    extern "Python" JSValue _quikcjs_cffi_py_func_wrap(JSContext *ctx, JSValueConst this_val, int argc, JSValueConst *argv, int magic, JSValue *func_data);

    int _macro_JS_VALUE_GET_TAG(JSValue v);
    int _macro_JS_VALUE_GET_NORM_TAG(JSValue v);
    int _macro_JS_VALUE_GET_INT(JSValue v);
    int _macro_JS_VALUE_GET_BOOL(JSValue v);
    double _macro_JS_VALUE_GET_FLOAT64(JSValue v);
    void *_macro_JS_VALUE_GET_PTR(JSValue v);

    JSValue _macro_JS_MKVAL(int64_t tag, int32_t val);
    JSValue _macro_JS_MKPTR(int64_t tag, void *p);

    JSObject *_macro_JS_VALUE_GET_OBJ(JSValue v);
    // void *_macro_JS_VALUE_GET_STRING(JSValue v); /* return is JSString* */
    int _macro_JS_VALUE_HAS_REF_COUNT(JSValue v);
    int _macro_JS_VALUE_GET_REF_COUNT(JSValue v);
    '''

    # print code
    for i, line in enumerate(_source.splitlines()):
        print(i + 1, ':', line)

    # build
    ffibuilder.cdef(_source)

    ffibuilder.set_source(
        '_quickjs',
        '''#include "../_quickjs_lib.h"

        int _macro_JS_VALUE_GET_TAG(JSValue v) { return JS_VALUE_GET_TAG(v); }
        int _macro_JS_VALUE_GET_NORM_TAG(JSValue v) { return JS_VALUE_GET_NORM_TAG(v); }
        int _macro_JS_VALUE_GET_INT(JSValue v) { return JS_VALUE_GET_INT(v); }
        int _macro_JS_VALUE_GET_BOOL(JSValue v) { return JS_VALUE_GET_BOOL(v); }
        double _macro_JS_VALUE_GET_FLOAT64(JSValue v) { return JS_VALUE_GET_FLOAT64(v); }
        void *_macro_JS_VALUE_GET_PTR(JSValue v) { return JS_VALUE_GET_PTR(v); }

        JSValue _macro_JS_MKVAL(int64_t tag, int32_t val) { return JS_MKVAL(tag, val); }
        JSValue _macro_JS_MKPTR(int64_t tag, void *p) { return JS_MKPTR(tag, p); }

        JSObject *_macro_JS_VALUE_GET_OBJ(JSValue v) { return JS_VALUE_GET_OBJ(v); }
        // void *_macro_JS_VALUE_GET_STRING(JSValue v) { return JS_VALUE_GET_STRING(v); }
        int _macro_JS_VALUE_HAS_REF_COUNT(JSValue v) { return JS_VALUE_HAS_REF_COUNT(v); }
        int _macro_JS_VALUE_GET_REF_COUNT(JSValue v) { return ((JSRefCountHeader*)JS_VALUE_GET_PTR(v))->ref_count; } /* quickjs-cffi */

        ''' + _inline_static_source,
        libraries=['m', 'dl', 'pthread'],
        extra_objects=[
            '../quickjs-repo/.obj/cutils.o',
            '../quickjs-repo/.obj/libbf.o',
            '../quickjs-repo/.obj/libregexp.o',
            '../quickjs-repo/.obj/libunicode.o',
            '../quickjs-repo/.obj/quickjs-libc.o',
            '../quickjs-repo/.obj/quickjs.o',
            '../quickjs-repo/.obj/repl.o',
        ],
        extra_compile_args=['-O3', '-fPIC', '-ffunction-sections', '-fdata-sections'],
        extra_link_args=['-flto'],
    )

    ffibuilder.compile(tmpdir='build', verbose=True)

    #
    # copy compiled modules
    #
    for file in glob.glob('build/*.so') + glob.glob('quickjs-repo/*.so'):
        shutil.move(file, 'quickjs/')

    for file in glob.glob('build/*.dll') + glob.glob('quickjs-repo/*.dll'):
        shutil.move(file, 'quickjs/')

    for file in glob.glob('build/*.dylib') + glob.glob('quickjs-repo/*.dylib'):
        shutil.move(file, 'quickjs/')


def build(*args, **kwargs):
    # clean, clone
    clean()
    clone_quickjs_repo()
    build_quickjs_repo(*args, **kwargs)


if __name__ == '__main__':
    build()
