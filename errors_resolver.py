#!/usr/bin/python3
# -*- coding: UTF-8 -*-

from __future__ import print_function
from pprint import pprint
import fileinput, re, subprocess, os, sys, inspect
from subprocess import check_output

exclude_includes = os.environ.get("exclude_includes",
        "lightweight_thread.hpp etip.h my_pthread.h pthreadtypes.h stdio2.h")

verbose = int(os.environ.get('verbose', '0'))

def log(*args, **kwargs):
    if verbose:
        print(inspect.stack()[1][3], str(*args).rstrip(), file=sys.stderr, **kwargs)
    pass

def popen(p):
    return subprocess.Popen(p, shell=True, stdout=subprocess.PIPE, encoding="utf-8").stdout

#
# Configuration:
#

src_path = os.environ.get('src_path', '.').replace(':', ' ')

# includedir is /usr/include or another for a cross-compiler
for line in popen('echo "#include <stdio.h>" | ' + os.environ.get('CC', 'gcc') + ' -E - '):
    m = re.match('.*?"(/.*)/stdio.h', line)
    if m:
        includedir = os.path.normpath(m.group(1))
        log('includedir=' + includedir);
        break
includedir_tags = re.sub(r'[:/ ]+', '_', includedir) + '.tags'

lib_path = '. ' # TODO user_obj, LIBRARY_PATH
for line in popen(os.environ.get('CC', 'gcc') + ' -Xlinker --verbose 2> /dev/null'):
    lib_path += ' '.join(re.findall('.*?SEARCH_DIR\("=?([^"]+)"\); *', line))
log('lib_path = ' + lib_path)
symbols_list = re.sub(r'[\.:/ ]+', '_', lib_path) + '.list'

#
#   Subroutines:
#

def substitute_paths(path):
    for subst in os.environ.get('substitute_paths',':').split(':'):
        if os.environ.get(subst):
            path = path.replace(os.environ.get(subst).rstrip('/') +'/', '${%s}/' % subst)
    return path

def popen_readline(cmd):
    log(cmd)
    #return check_output(cmd, shell=True)
    return subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, encoding="utf-8").stdout.readline().rstrip('\n');

def search_definitions_src(undefined):
    for src in os.environ.get('src_path', '.').split(':'):
        ret = []
        for src in popen('grep --word-regexp "^' + undefined + '" ' + src + '/tags | cut --fields=2'):
            src = substitute_paths(src.rstrip())
            log('proc src=' + src)
            add(ret, "LDLIBS+=' %s';" % src)
            #add(ret, "LDLIBS+=' %s';" % (os.path.splitext(src)[0]+'.o')) # an option to add object
            break
    if ret:
        return ret
    return "# unresolved " + undefined

def search_definitions_lib(undefined):
    # TODO
    log(lib_path)
    if not os.path.isfile(symbols_list):
        print('Building symbols list for ' + lib_path, file=sys.stderr)
        os.system('nm --demangle --defined-only --print-file-name --no-sort $(find ' + lib_path +
            ' -name "lib*.so" -o -name "lib*.so.*" -o -name *.o 2> /dev/null) 2> /dev/null | grep " T " > ' + symbols_list);
    line = popen_readline('grep --word-regexp ".* T ' + undefined + '\>" ' + symbols_list + '| cut --fields=1 --delimiter=":"')
    m = re.match(r'.*\/lib(.*)\.so', line)
    if m:
        return "LDLIBS+=' -l %s';" % m.group(1)

def search_definitions(undefined):
    ret = []
    add(ret, search_definitions_lib(undefined))
    if ret == []:
        add(ret, search_definitions_src(undefined))
    return ret

def search_lib_path(lib):
    log(lib_path)
    line = popen_readline('find ' + lib_path + ' -name "lib' + lib + '.so" -printf "%P\n" 2> /dev/null')
    log(line)
    m = re.match(r'(.*)\/lib.*\.so', line)
    if m:
        log(m.group(1))
        # arm-linux-gnueabi-gcc doesn't support LIBRARY_PATH
        #return ["LIBRARY_PATH+=':%s';" % m.group(1), "LD_LIBRARY_PATH+=':%s';" % m.group(1)]
        return ["LDFLAGS+=' -L %s';" % m.group(1), "LD_LIBRARY_PATH+=':%s';" % m.group(1)]
    res = []
    print('Searching for lib%s.so in repository' % lib, file=sys.stderr)
    if os.system('apt-file -h > /dev/null 2>&1') == 0:
        for package in popen('apt-file search --regexp .*/lib%s\.so$' % (re.escape(lib))):
            log('found ' + package)
            add(res, "install+=' %s'" % package.split(':')[0])
    elif os.system('yum whatprovides -h > /dev/null 2>&1') == 0:
        res = yum_whatprovides('*/lib' + lib + '.so')
    else:
        print("Can't search repository", file=sys.stderr)
    return res

def search_declarations(undeclared):
    log(undeclared)
    if not os.path.isfile(includedir_tags):
        my_env = os.environ.copy()
        os.environ["CTAGS"] = os.environ.get("CTAGS",'')
        os.environ["CTAGS"] += " -I __THROW,__THROWNL,__nonnull+"
        # Credit: http://stackoverflow.com/questions/1632633/ctags-does-not-parse-stdio-h-properly#1632633
        os.environ["CTAGS"] += " --exclude=internal"
        os.environ["CTAGS"] += " --sort=no --recurse "
        os.environ["CTAGS"] += " --c-kinds=+ep "
        # TODO: custom exclude
        print('Building tags for ' + includedir, file = sys.stderr)
        os.system('ctags -o ' + includedir_tags + ' ' + includedir)
    # TODO: man 3 $undeclared | grep '#include'
    if not os.path.isfile('prototype.tags'):
        # TODO: optional current dir (-C ...)
        print('Building prototype.tags', file=sys.stderr)
        os.system('ctags -o prototype.tags --recurse --sort=no --c-kinds=p ' + src_path)
    #return subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE).stdout.readline().rstrip('\n');
    ret = []
    for line in popen(
            'grep "^' + undeclared + '\t" ' + includedir_tags + ' prototype.tags '
            '| cut --fields=2'
            '| awk "{ print length, \$0 }"'
            '| sort --numeric-sort --stable'
            '| cut --delimiter=" " --fields=2-'):
        line = line.rstrip()
        # remove CPATH from include path
        for p in os.environ.get('CPATH', '').split(':') + [includedir]:
            if p != '': line = re.sub('^' + p + '/', '', line)
        log('proc line=' + line)
        for p in exclude_includes.split():
            log('exclude_includes=' + p)
            if p in line: line = None; break
        if line:
            add(ret, "CPPFLAGS+=' -include %s';" % line)
        # for demo the first result is enough
        break
    if ret:
        return ret
    return "# unresolved " + undeclared

def yum_whatprovides(f):
    res = []
    for l in popen('yum whatprovides -q %s 2>/dev/null' % f):
        m = re.match('([^ ]+-[^ ]+) : ', l)
        if m:
            log('{'+ m.group(1) + '}')
            for info in popen('yum info ' + m.group(1) + ' 2> /dev/null'):
                m = re.match('Name +: (.*)', info)
                if m: add(res, "install+=' %s'" % m.group(1))
    return res

def search_command(command):
    log(command)
    res = []
    print('Searching for %s in repository' % command, file=sys.stderr)
    if os.path.isfile('/usr/lib/command-not-found'):
        for line in popen('/usr/lib/command-not-found ' + command + ' 2>&1 '):
            log(line)
            m = re.match('.*apt(-get)? install ([\w-]+)', line)
            if m:
                log('{'+ m.group(2) + '}')
                add(res, "install+=' %s';" % m.group(2))
            m = re.match('^ \* ([\w-]+)\n', line)
            if m:
                log('{'+ m.group(1) + '}')
                add(res, "install+=' %s';" % m.group(1))
    elif os.system('apt-file -h > /dev/null 2>&1') == 0:
            for package in popen('apt-file search --regexp  "/bin/%s$"' % re.escape(command)):
                log('found ' + package)
                add(res, "install+=' %s'" % package.split(':')[0])
    elif os.system('yum whatprovides -h > /dev/null 2>&1') == 0:
        res = yum_whatprovides('*/bin/' + command)
    else:
            print("Can't search repository", file=sys.stderr)
    return res

def search_file(f):
    log(f)
    res = []
    #find_opt = ''
    #for e in os.environ.get('exclude_path', '').split(':'):
    #    find_opt += ' ! -path ' + e
    #log(find_opt)
    for p in os.environ.get('file_search_path', '.').split(':'):
        log(p)
        for line in popen('find ' + p + ' ' + os.environ.get('find_flags', '') + ' -name .pc -prune -o -path "*/' + f + '" -printf "%P\n"'):
            log(line)
            # get path to found file
            m = re.match('(.*)/' + f, line)
            if m:
                log('{'+ m.group(1) + '}')
                add(res, 'CPATH+=":%s";' % substitute_paths(m.group(1)))
    p = f
    if not p.startswith('/'):
        p = '%s/%s' % (includedir, f)
    print('Searching for %s in repository' % p, file=sys.stderr)
    #if res == []: # TODO
    if os.system('apt-file -h > /dev/null 2>&1') == 0:
        for package in popen('apt-file search --fixed-string %s' % p):
            log('found ' + package)
            add(res, "install+=' %s'" % package.split(':')[0])
    elif os.system('yum whatprovides -h > /dev/null 2>&1') == 0:
        res = yum_whatprovides(p)
    else:
        print("Can't search repository", file=sys.stderr)
    return res

def need_package(package):
    #return 'sudo apt-get install ' + package
    return "install+=' %s'" % package

def add(l1, l2):
    if isinstance(l2, list):
        for e in l2:
            if not e in l1:
                l1.append(e)
    else:
        if l2 and not l2 in l1:
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
    m = re.match('.*?' + error, line, re.IGNORECASE)
    if m:
        log('line=' + line)
        log('error=' + error)
        add(solutions, solution_func(m.group(1)))

def err2cmd(solutions, line, error, command):
    if '%s' in command:
        m = re.match('.*?' + error, line)
        if m:
            add(solutions, command % m.group(1))
    else:
        if re.match('.*?' + error, line):
            add(solutions, command)

def parse_errno(solutions, line, error):
    m = re.match('.*?' + error, line, re.IGNORECASE)
    if m:
        log('line=' + line)
        log('error=' + error)
        add(solutions, 'echo "\'%s\' in %s"' % (os.strerror(abs(int(m.group(1)))), line))

def parse_line_for_errors(l):
    s = []
    l = l.replace('‘', "'").replace('’', "'").replace('`', "'")
    log('line2=' + l)

    # Compilation and linkage errors:
    parse_err(s, l, "error: unknown type name '(.*)'.*", search_declarations)
    parse_err(s, l, "warning: implicit declaration of function '(.*)'.*", search_declarations)
    parse_err(s, l, "warning: incompatible implicit declaration of built-in function '(.*)'.*", search_declarations)
    parse_err(s, l, "error: '(.*)' undeclared.*", search_declarations)
    parse_err(s, l, "undefined reference to '(.*)'.*", search_definitions)
    parse_err(s, l, "configure:\d+: error: (\w+) is missing", search_lib_path)
    parse_err(s, l, "ld: cannot find -l(.*)", search_lib_path)
    parse_err(s, l, "warning: lib(.*?)\..*, needed by .*, not found .*", search_lib_path)
    parse_err(s, l, "error while loading shared libraries: lib(.*?)\..*: cannot open shared object file", search_lib_path)
    if (False
            or re.match(".*error: converting to 'std::__cxx11::list<int>'", l, re.IGNORECASE)
            or re.match(".*error: in C\+\+98 .* must be initialized by constructor, not by '{\.\.\.}'", l, re.IGNORECASE)
            or re.match(".*error: could not convert '{.*}' from '<brace-enclosed initializer list>' to 'std::vector<int>'", l, re.IGNORECASE)):
        s += [ 'CXXFLAGS="${CXXFLAGS/-std=c++*/} -std=c++11"' ]
    # ld: cannot find sub/sub.o: No such file or directory
    # cc: error: sub/sub.o: No such file or directory
    #TODO:
    # --with-libiconv

    # Not installed packages:
    parse_err(s, l, '/usr/lib/(command-not-found): No such file or directory', need_package)
    parse_err(s, l, '([^:^ ]+): command not found', search_command)
    parse_err(s, l, 'failed to run (.*?):', search_command)
    parse_err(s, l, ': ([^:^ ]+): No such file or directory', search_command)
    parse_err(s, l, ': ([^:^ ]+): not found', search_command)
    parse_err(s, l, 'ERROR: ([^:^ ]+) does not seem to be installed.', search_command) # ERROR: msgfmt does not seem to be installed.
    parse_err(s, l, "command '(.*)' not found", search_command) # command 'i686-pc-linux-gnu-g++' not found
    parse_err(s, l, "error: ([^:^ ]+) wasn't found", search_command)
    parse_err(s, l, "'(.*)' is needed", search_command)
    parse_err(s, l, "Could not find a ([^:^ ]+) in your PATH", search_command)
    err2cmd(s, l, 'ImportError: No module named (.*)', 'sudo pip install %s')

    parse_err(s, l, ": ([^:^ ]+): No such file or directory", search_file)
    parse_err(s, l, ': ([^:^ ]+): bad interpreter: No such file or directory', search_file)

    # Decoding errno
    if re.match('make.*: .* Error \d+', l) is None:
        parse_errno(s, l, 'error[= ](-?\d+)')
    parse_errno(s, l, 'return code = (-?\d+)')

    # Investigating system logs:

    # Storage errors in kernel log:
    # try to run e2fsck without unmounting in read only mode
    err2cmd(s, l, '\((.*?)\): warning: mounting unchecked fs, running e2fsck is recommended', 'sudo e2fsck -n /dev/%s')
    err2cmd(s, l, 'I/O error, dev (.*?), sector', 'sudo smartctl -t long /dev/%s')
    err2cmd(s, l, 'Buffer I/O error on device (.*?),', 'sudo smartctl -t long /dev/%s')
    err2cmd(s, l, 'Emask .* \(media error\)', 'echo please check disk media with smartctl -t long')
    err2cmd(s, l, 'SError:.*(10B8B|Dispar)', 'echo please check SATA cables')
    # /var/log/auth.log errors:
    err2cmd(s, l, '(Failed password for |authentication failure.*user=)root', 'echo somebody tries to hack you, please run IDS')
    # /var/log/syslog errors:
    err2cmd(s, l, 'mcelog: (Please check your system cooling.)', 'echo %s')

    log(s)
    return s

def parse_fileinput():
    solutions = []
    for line in fileinput.input():
        if line != '\n':
            log('line=' + line)
            for s in parse_line_for_errors(line.rstrip('\n')):
                add(solutions, s)
    for s in solutions:
        print(s)

if not os.path.isfile('tags'):
    if os.system('ctags --recurse --sort=no ' + src_path) != 0:
        print('echo please install ctags')
        exit(1)

parse_fileinput()
