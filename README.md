# Errors resolver

The mission of Errors resolver is to provide resolutions for standard errors. Current implementation analyzes some build errors caused by missing components, searches the missing components in system environment and provides a resolution with missing components.

For example try this:

echo "warning: incompatible implicit declaration of built-in function ‘printf’" | ./errors_resolver.py

Solution:

CPPFLAGS+=' -include stdio.h';

## Run demo:

./errors_resolver_demo

## Run demo with cross compiler:

CC=arm-linux-gnueabi-gcc ./errors_resolver_demo

## errors_resolver.py

### Input:

Compilation errors as output of compilation

### Output:

Fixes to solve compilation errors in form of modification of environment variables.


## Features:

Analyzes warnings and errors:
* implicit declaration
* undeclared symbol
* undefined symbol
* library not found or missing
Demo support cross compiler

Provides modification of standard environment variables:
* CPPFLAGS, LDFLAGS, LDLIBS, LD_LIBRARY_PATH

Uses tools for searing of missing components:
* ctags, nm, find

## To to list:
* Analize more ./configure errors.


You are welcome to request additional features in form of erroneous sample source code (see errors_resolver_sample.c), sample errors and solutions.

For further information you are welcome to read sources.

Thanks
