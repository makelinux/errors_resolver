#!/usr/bin/python
# -*- coding: UTF-8 -*-

from __future__ import print_function
from pprint import pprint
import fileinput, re, subprocess, os, sys, inspect

lib_path = os.environ.get('lib_path', 'a:q').replace(':', ' ')

def log(*args, **kwargs):
    print(inspect.stack()[1][3], str(*args).rstrip(), file=sys.stderr, **kwargs)
    pass

def popen_readline(cmd):
    log(cmd)
    return subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE).stdout.readline().rstrip('\n');

def search_libraries(undefined):
    # TODO
    line = popen_readline(
            'nm --demangle --defined-only --print-file-name $(find ' + lib_path + ' -name "lib*.so" -o -name "lib*.so.*") 2> /dev/null \
            | grep --word-regexp ".* T ' + undefined + '" | cut --fields=1 --delimiter=":"')
    m = re.match(r'.*\/lib(.*)\.so', line)
    if m is not None:
        return "LDLIBS+=' -l %s';" % m.group(1)

def search_lib_path(lib):
    line = popen_readline('find ' + lib_path + ' -name "lib' + lib + '.so" -printf "%P\n" ')
    log(line)
    m = re.match(r'(.*)\/lib.*\.so', line)
    if m is not None:
        log(m.group(1))
        return ["LDFLAGS+=' -L %s';" % m.group(1), "LD_LIBRARY_PATH+=':%s';" % m.group(1)]

def search_declarations(undeclared):
    log(undeclared)
    # TODO: man 3 $undeclared | grep '#include'
    f = popen_readline('grep "^' + undeclared + '\t" system.tags prototype.tags \
            | cut --fields=2 \
            | awk "{ print length, \$0 }" \
            | sort --numeric-sort --stable \
            | cut --delimiter=" " --fields=2- \
            | head --lines 1')
    log('f=' + f)
    f = f.replace('/usr/include/', '') # TODO: generalize with includedir
    if f:
        return "CPPFLAGS+=' -include %s';" % f

def add(l1, l2):
    if isinstance(l2, list):
        for e in l2:
            if not e in l1:
                l1.append(e)
    else:
        if not l2 in l1:
            l1.append(l2)

# TODO: new concept: parse errors to dict
def parse_error(line, error, _type):
    log('line=' + line)
    log('error=' + error)
    m = re.match(error, line)
    log('match=' + str(m))
    if m:
        log('line=' + line)
        log('error=' + error)
        return {status: 'error', 'type': _type, 'name': m.group(1)}

def parse_err(solutions, line, error, solution_func):
    m = re.match(error, line)
    if m is not None:
        log('line=' + line)
        log('error=' + error)
        add(solutions, solution_func(m.group(1)))

def parse_line_for_errors(l):
    s = []
    #log(parse_error(l, r'.*warning: implicit declaration of function ‘(.*)’.*', 'declaration'))
    parse_err(s, l, r'.*warning: implicit declaration of function ‘(.*)’.*', search_declarations)
    parse_err(s, l, r'.*warning: incompatible implicit declaration of built-in function ‘(.*)’.*', search_declarations)
    parse_err(s, l, r'.*error: ‘(.*)’ undeclared.*', search_declarations)
    parse_err(s, l, r'.*undefined reference to `(.*)\'.*', search_libraries)
    parse_err(s, l, r'.*ld: cannot find -l(.*)', search_lib_path)
    parse_err(s, l, r'.*warning: lib(.*?)\..*, needed by .*, not found .*', search_lib_path)
    parse_err(s, l, r'configure:\d+: error: (\w+) is missing', search_lib_path)
    #error while loading shared libraries: (.*): cannot open shared object file
    #s/.*fatal error: (.*): No such file or directory.*/apt-file search $1/ && print;
    # --with-libiconv
    return s

def parse_fileinput():
    solutions = []
    for line in fileinput.input():
        #log('line=' + line)
        for s in parse_line_for_errors(line):
            add(solutions, s)
    for s in solutions:
        print(s)

if not os.path.isfile('system.tags'):
    os.system('ctags --sort=no -o system.tags --recurse --c-kinds=+ep ' + os.environ.get('includedir'))

if not os.path.isfile('prototype.tags'):
    # TODO: optional current dir (-C ...)
    os.system('ctags -o prototype.tags --recurse --c-kinds=p . ')

parse_fileinput()
