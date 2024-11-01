import glob
import subprocess


def clean_quickjs():
    files = glob.glob('quickjs/*.so') + glob.glob('quickjs/*.a') + glob.glob('quickjs/*.dylib') + glob.glob('quickjs/*.dll')
    subprocess.run(['rm', '-fv'] + files, check=True)


def clean_quickjs_repo():
    subprocess.run(['make', '-C', 'quickjs-repo', 'clean'], check=True)


def clean():
    clean_quickjs()
    subprocess.run(['rm', '-fr', 'build'], check=True)
    subprocess.run(['rm', '-fr', 'dist'], check=True)
    subprocess.run(['rm', '-fr', 'quickjs-repo'], check=True)
    subprocess.run(['rm', '-fr', 'wheelhouse'], check=True)
