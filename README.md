# Errors resolver

The mission of Errors resolver is to provide resolutions for standard errors. Current implementation analyzes some build errors caused by missing components, searches the missing components in system environment and provides a resolution with missing components.

For example try this:

echo "warning: incompatible implicit declaration of built-in function ‘printf’" | ./errors_resolver.py

Solution:

CPPFLAGS+=' -include stdio.h';

## Demonstrations:

### Resolving compilation configuration errors:

./errors_resolver_demo

PS: remove files from previous test if need
rm errors_resolver_sample prototype.tags sub/libsub.so system.tags

## Run above demo with cross compiler:

CC=arm-linux-gnueabi-gcc ./errors_resolver_demo

This demo was tested on Ubuntu, where gcc-arm-linux-gnueabi and qemu-user are installed.

## Demo for resolving not found commands in subroutine with helper /usr/lib/command-not-found

./command-not-found-demo

## errors_resolver.py

### Input:

Compilation and system errors.
Output of compilation or execution log with errors can passed to output of resolver.

### Output:

Fixes to solve compilation errors in form of modification of environment variables.

## Features:

Analyzes warnings and errors:
* implicit declaration
* undeclared symbol
* undefined symbol
* library not found or missing
* command not fount
Demo supports cross compiler

Provides modification of standard environment variables:
* CPPFLAGS, LDFLAGS, LDLIBS, LD_LIBRARY_PATH

Uses tools for searing of missing components:
* ctags, nm, find
* /usr/lib/command-not-found

## To to list:
* Analyze more ./configure errors.


You are welcome to request additional features in form of erroneous sample source code (see errors_resolver_sample.c), sample errors and solutions.

For further information you are welcome to read sources.

Thanks
