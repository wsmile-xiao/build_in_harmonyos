# kcgi

Minimal CGI and FastCGI library for C.

## Version
0.13.4

## Description
kcgi is a minimal, secure CGI and FastCGI library written in C. It provides a simple framework for building web applications with proper security sandboxing.

## Build Requirements
- BSD make (bmake)
- clang compiler
- zlib

## Products
- libkcgi.a / libkcgi.so.1 - Main CGI library
- libkcgihtml.a / libkcgihtml.so.1 - HTML output helpers
- libkcgijson.a / libkcgijson.so.1 - JSON output helpers  
- libkcgixml.a / libkcgixml.so.1 - XML output helpers
- libkcgiregress.a / libkcgiregress.so.1 - Regression testing framework
- kfcgi - FastCGI process manager

## Usage
Include kcgi.h in your application and link against libkcgi.

## Documentation
Man pages available for all functions.

## Source
https://kristaps.bsd.lv/kcgi/
