# Errors resolver

The mission of Errors resolver is to provide resolutions or recommendations for standard errors. For example it analyzes some build errors caused by missing components, searches the missing components in system environment and provides a location to missing components.

For example:

echo "warning: implicit declaration of function ‘pthread_create’" | ./errors_resolver.py

Output with solution:

CPPFLAGS+=' -include pthread.h';

In this example errors_resolver.py searches tags and provides missing header file.

## Demonstrations:

### Resolving compilation configuration errors:

./errors_resolver_demo

PS: remove files from previous test if need
* rm errors_resolver_sample prototype.tags sub/libsub.so

## Run above demo with cross compiler:

CC=arm-linux-gnueabi-gcc ./errors_resolver_demo

This demo was tested on Ubuntu, where gcc-arm-linux-gnueabi and qemu-user are installed.

## Demo of resolving error 'command not found'

Helper /usr/lib/command-not-found resolves the error in interactive shell.
To resolve errors in subroutine run:

./command-not-found-demo

## Analyzing system logs

sudo ./errors_resolver.py /var/log/*log

## Resolving various errors from a log file:

./errors_resolver.py < [errors.log](https://github.com/makelinux/errors_resolver/blob/master/errors.log)

## Description of core application errors_resolver.py

### Input:

Compilation and system errors.
Output of compilation or execution log with errors can passed to output of resolver.

### Output:

Fixes or recommendations to solve errors in form of modification of environment variables or shell commands.

## Features:

Analyzes warnings and errors:
* implicit declaration
* undeclared symbol
* undefined symbol
* library not found or missing
* command not found
* decodes numeric system errno
* catches some disk errors

Demo supports cross compiler

Provides modification of standard environment variables:
* CPATH, CPPFLAGS, LIBRARY_PATH, LDFLAGS, LDLIBS, LD_LIBRARY_PATH

Uses tools for searing of missing components:
* ctags, nm, find
* /usr/lib/command-not-found

## Regression test:

* (./errors_resolver_demo && CC=arm-linux-gnueabi-gcc ./errors_resolver_demo && ./command-not-found-demo && ./errors_resolver.py errors.log && echo PASSED) > regression_test.log 2>&1 && echo PASSED || (tail regression_test.log; false)

## To to list:
* Analyze more ./configure errors.

You are welcome to request additional features in form of erroneous sample source code (see errors_resolver_sample.c), sample errors and solutions.

For further information you are welcome to read sources.

Thanks
