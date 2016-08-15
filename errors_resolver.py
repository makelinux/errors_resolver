#!/usr/bin/python
# -*- coding: UTF-8 -*-

from __future__ import print_function
import fileinput, re, subprocess, os, sys
from pprint import pprint
import inspect

sol = ''

def log(a):
    #if a: print(inspect.stack()[1][3], str(a).rstrip(), file=sys.stderr)
    pass

def solution(s):
    global sol
    sol += s + ';\n'

def popen_readline(cmd):
    log('Running ' + cmd)
    return subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE).stdout.readline().rstrip('\n');

def search_libraries(undefined):
    line = popen_readline('nm --demangle --defined-only --print-file-name $(find -name "*.so") 2> /dev/null \
            | grep -w ".* T ' + undefined + '" | cut -f 1 -d ":"')
    m = re.match(r'.*\/lib(.*)\.so', line)
    if m is not None:
        solution('need_library ' + m.group(1))

def search_lib_path(lib):
    line = popen_readline('find -name "lib*.so" -printf "%P\n" ')
    log(line)
    m = re.match(r'(.*)\/lib.*\.so', line)
    if m is not None:
        log(m.group(1))
        solution('need_lib_path ' + m.group(1))

def search_declarations(undeclared):
    # man undeclared | grep '#include'
    log(undeclared)
    # man 3 $undeclared | grep '#include'
    f = popen_readline('grep "^' + undeclared + '\t" system.tags prototype.tags | cut -f 2  | awk "{ print length, \$0 }" |sort --numeric-sort --stable |cut -d" " -f2- | head -n 1')
    log('f=' + f)
    f = f.replace('/usr/include/', '')
    if f:
        return 'need_header ' + f + ' for ' + undeclared

def error_to_one_solution(line, error, solution_func):
    m = re.match(error, line)
    if m is not None:
        log('line=' + line)
        log('error=' + error)
        s = solution_func(m.group(1));
        if s:
            solution(s)

def parse_errors(l):
    global sol
    error_to_one_solution(l, r'.*warning: implicit declaration of function ‘(.*)’.*', search_declarations)
    error_to_one_solution(l, r'.*warning: incompatible implicit declaration of built-in function ‘(.*)’.*', search_declarations)
    error_to_one_solution(l, r'.*error: ‘(.*)’ undeclared.*', search_declarations)
    error_to_one_solution(l, r'.*undefined reference to `(.*)\'.*', search_libraries)
    error_to_one_solution(l, r'.*ld: cannot find -l(.*)', search_lib_path)
    error_to_one_solution(l, r'.*warning: lib(.*?)\..*, needed by .*, not found .*', search_lib_path)
    error_to_one_solution(l, r'configure:\d+: error: (\w+) is missing', search_lib_path)
    #error while loading shared libraries: (.*): cannot open shared object file
    #s/.*fatal error: (.*): No such file or directory.*/apt-file search $1/ && print;
    # --with-libiconv
    return sol

def parse_fileinput():
    global sol
    for line in fileinput.input():
        #log('line=' + line)
        parse_errors(line)
        if sol:
            sys.stdout.write(sol)

if not os.path.isfile('system.tags'):
    os.system('ctags -uo system.tags -R --c-kinds=+ep ' + os.environ.get('includedir'))

if not os.path.isfile('prototype.tags'):
    os.system('ctags -o prototype.tags -R --c-kinds=p  . ')

parse_fileinput()
