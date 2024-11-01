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
    # Regular expression to match function name
    pattern = r'(\w+)\s*\(([^)]*)\)'

    # Function to add prefix to the function name
    def add_prefix(match):
        func_name = match.group(1)
        args = match.group(2)
        return f"{prefix}{func_name}({args})"

    # Use re.sub to replace the function name with the prefixed one
    new_signature = re.sub(pattern, add_prefix, func_signature)
    return new_signature


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
    # env['CFLAGS'] = '-fPIC'
    env['CFLAGS'] = '-fPIC -fno-inline'
    # env['CFLAGS'] = '-fPIC -Djs_force_inline="inline __attribute__((visibility("default")))"'
    # env['CFLAGS'] = '-fPIC -Dstatic= -Dinline='
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

            # line = line[len('static inline '):]
            # line = add_prefix_to_function(line, '__cffi_')
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

    # print code
    for i, line in enumerate(_source.splitlines()):
        print(i + 1, ':', line)

    # build
    ffibuilder.cdef(_source)

    ffibuilder.set_source(
        '_quickjs',
        '''
        #include "../_quickjs_lib.h"
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
        extra_compile_args=['-O3', '-fno-inline'],
        extra_link_args=['-flto', '-fno-inline'],
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
