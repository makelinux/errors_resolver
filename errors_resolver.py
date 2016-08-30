#!/usr/bin/python
# -*- coding: UTF-8 -*-

from __future__ import print_function
from pprint import pprint
import fileinput, re, subprocess, os, sys, inspect
from subprocess import check_output
from errno import errorcode

lib_path = os.environ.get('lib_path', '').replace(':', ' ')
verbose = int(os.environ.get('verbose', '0'))

def log(*args, **kwargs):
    if verbose:
        print(inspect.stack()[1][3], str(*args).rstrip(), file=sys.stderr, **kwargs)
    pass

def popen_readline(cmd):
    log(cmd)
    #return check_output(cmd, shell=True)
    return subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE).stdout.readline().rstrip('\n');

def search_libraries(undefined):
    # TODO
    log(lib_path)
    line = popen_readline(
            'nm --demangle --defined-only --print-file-name $(find ' + lib_path + ' -name "lib*.so" -o -name "lib*.so.*") 2> /dev/null'
            '| grep --word-regexp ".* T ' + undefined + '" | cut --fields=1 --delimiter=":"')
    m = re.match(r'.*\/lib(.*)\.so', line)
    if m is not None:
        return "LDLIBS+=' -l %s';" % m.group(1)

def search_lib_path(lib):
    log(lib_path)
    line = popen_readline('find ' + lib_path + ' -name "lib' + lib + '.so" -printf "%P\n" ')
    log(line)
    m = re.match(r'(.*)\/lib.*\.so', line)
    if m is not None:
        log(m.group(1))
        return ["LDFLAGS+=' -L %s';" % m.group(1), "LD_LIBRARY_PATH+=':%s';" % m.group(1)]

def search_declarations(undeclared):
    log(undeclared)
    # TODO: man 3 $undeclared | grep '#include'
    proc = subprocess.Popen(
            'grep "^' + undeclared + '\t" system.tags prototype.tags '
            '| cut --fields=2'
            '| awk "{ print length, \$0 }"'
            '| sort --numeric-sort --stable'
            '| cut --delimiter=" " --fields=2-'
            , shell=True, stdout=subprocess.PIPE)
    #return subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE).stdout.readline().rstrip('\n');
    ret = []
    for line in proc.stdout:
        log('proc line=' + line)
        line = line.rstrip().replace('/usr/include/', '') # TODO: generalize with includedir
        #ret += "# for %s:\n" % undeclared
        add(ret, "CPPFLAGS+=' -include %s';" % line)
        # for demo the first risult is enogth
        break
    if ret:
        return ret
    return "# unresolved " + undeclared

def search_command(command):
    log(command)
    proc = subprocess.Popen('/usr/lib/command-not-found ' + command + ' 2>&1 ',
        shell=True, stdout=subprocess.PIPE)
    res = []
    for line in proc.stdout:
        log(line)
        m = re.match('.*apt-get install ([\w-]+)', line)
        if m:
            log('{'+ m.group(1) + '}')
            add(res, "packages+=' %s';" % m.group(1))
        m = re.match('^ \* ([\w-]+)\n', line)
        if m:
            log('{'+ m.group(1) + '}')
            add(res, "packages+=' %s';" % m.group(1))
    return res

def search_file(f):
    # apt-file search $1
    log(f)
    res = []
    #find_opt = ''
    #for e in os.environ.get('exclude_path', '').split(':'):
    #    find_opt += ' ! -path ' + e
    #log(find_opt)
    for p in os.environ.get('file_search_path', '.').split(':'):
        log(p)
        log('find ' + p + ' ' + os.environ.get('find_flags', '') + ' -name .pc -prune -o -path */' + f + ' -print')
        proc = subprocess.Popen('find ' + p + ' ' + os.environ.get('find_flags', '') + ' -name .pc -prune -o -path "*/' + f + '" -print',
            shell=True, stdout=subprocess.PIPE)
        for line in proc.stdout:
            log(line)
            m = re.match('(.*)/' + f, line)
            if m:
                log('{'+ m.group(1) + '}')
                dir = m.group(1)
                for subst in os.environ.get('substitute_paths',':').split(':'):
                    if os.environ.get(subst):
                        dir = dir.replace(os.environ.get(subst), '${%s}' % subst)
                add(res, 'CPPFLAGS+=" -I%s";' % dir)
    return res


def need_package(package):
    #return 'sudo apt-get install ' + package
    return "packages+=' %s'" % package

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
    m = re.match('.*?' + error, line)
    if m is not None:
        log('line=' + line)
        log('error=' + error)
        add(solutions, solution_func(m.group(1)))

def err2cmd(solutions, line, error, command):
    if '%s' in command:
        m = re.match('.*?' + error, line)
        if m is not None:
            add(solutions, command % m.group(1))
    else:
        if re.match('.*?' + error, line):
            add(solutions, command)
def errno(n):
    # TODO: provide context
    return os.strerror(abs(int(n)))

def parse_line_for_errors(l):
    s = []
    parse_err(s, l, '/usr/lib/(command-not-found): No such file or directory', need_package)
    parse_err(s, l, 'fatal error: ([^:^ ]+): No such file or directory', search_file)
    parse_err(s, l, 'error: unknown type name ‘(.*)’.*', search_declarations)
    parse_err(s, l, 'warning: implicit declaration of function ‘(.*)’.*', search_declarations)
    parse_err(s, l, 'warning: incompatible implicit declaration of built-in function ‘(.*)’.*', search_declarations)
    parse_err(s, l, 'error: ‘(.*)’ undeclared.*', search_declarations)
    parse_err(s, l, 'undefined reference to `(.*)\'.*', search_libraries)
    parse_err(s, l, 'configure:\d+: error: (\w+) is missing', search_lib_path)
    parse_err(s, l, 'ld: cannot find -l(.*)', search_lib_path)
    parse_err(s, l, 'warning: lib(.*?)\..*, needed by .*, not found .*', search_lib_path)
    parse_err(s, l, 'error while loading shared libraries: lib(.*?)\..*: cannot open shared object file', search_lib_path)
    parse_err(s, l, '([^:^ ]+): command not found', search_command)

    parse_err(s, l, 'error[= ](-?\d+)', errno)
    parse_err(s, l, 'errno[= ](-?\d+)', errno)

    # Storage errors
    err2cmd(s, l, '\((.*?)\): warning: mounting unchecked fs, running e2fsck is recommended', 'sudo e2fsck -n /dev/%s')
    err2cmd(s, l, 'I/O error, dev (.*?), sector', 'sudo smartctl -t long /dev/%s')
    err2cmd(s, l, 'Buffer I/O error on device (.*?),', 'sudo smartctl -t long /dev/%s')
    err2cmd(s, l, 'Emask .* \(media error\)', 'echo please check disk media with smartctl -t long')
    err2cmd(s, l, 'SError:.*(10B8B|Dispar)', 'echo please check SATA cables')

    err2cmd(s, l, 'authentication failure.*user=root', 'echo somebody tries to hack you')
    err2cmd(s, l, 'Failed password for root', 'echo somebody tries to hack you')

    log(s)
    #TODO:
    # --with-libiconv
    return s

def parse_fileinput():
    solutions = []
    for line in fileinput.input():
        if line != '\n':
            log('line=' + line)
            for s in parse_line_for_errors(line):
                add(solutions, s)
    for s in solutions:
        print(s)

if not os.path.isfile('system.tags'):
    includedir = os.environ.get('includedir', '/usr/include')
    log('Building system.tags for ' + includedir)
    os.system('ctags --sort=no -o system.tags --recurse --c-kinds=+ep ' + os.environ.get('includedir', '/usr/include'))

if not os.path.isfile('prototype.tags'):
    # TODO: optional current dir (-C ...)
    log('Building prototype.tags')
    os.system('ctags -o prototype.tags --recurse --c-kinds=p . ')

parse_fileinput()
