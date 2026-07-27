# Test Report — makefile2graph v1.5.0

**Date**: 2026-07-15
**Build System**: makefile
**Compiler**: clang 15.0.4

## Compilation

```bash
$ make CC=clang -j1
clang -fPIC -O2 -Wall -I/storage/Users/currentUser/usr/local/include -L/storage/Users/currentUser/usr/local/lib  make2graph.c   -o make2graph
```

Result: ✅ PASS (no errors, no warnings)

## Binary Verification

```bash
$ ./make2graph --version
1.5.0
```

Result: ✅ PASS

## Functional Tests

### Test 1: DOT format output
```bash
$ make -Bnd 2>/dev/null | ./make2graph --format l
<ROOT>
all
make2graph
make2graph.c
```
Result: ✅ PASS

### Test 2: GEXF XML format output
```bash
$ make -Bnd 2>/dev/null | ./make2graph --format x
<?xml version="1.0" encoding="UTF-8"?>
<gexf xmlns="http://www.gexf.net/1.2draft" version="1.2">
  <meta>
    <creator>https://github.com/lindenb/makefile2graph version:1.5.0</creator>
    <description>Creates a graph from a Makefile</description>
```
Result: ✅ PASS

### Test 3: Deep format output
```bash
$ make -Bnd 2>/dev/null | ./make2graph --format e
make2graph
```
Result: ✅ PASS

### Test 4: Wrapper script
```bash
$ PATH=.:$PATH ./makefile2graph
digraph G {
n2[label="all", color="red"];
n3[label="make2graph", color="red"];
n4[label="make2graph.c", color="green"];
n3 -> n2 ;
```
Result: ✅ PASS

## Conan Test Package

```bash
$ conan create . --build=missing --user=ohpcd --channel=stable
...
make2graph --version → 1.5.0
make -Bnd | make2graph --format l → OK
make -Bnd | make2graph --format x → OK
```
Result: ✅ PASS

## Summary

| Test | Result |
|------|--------|
| Compilation | ✅ PASS |
| Binary --version | ✅ PASS |
| DOT format | ✅ PASS |
| GEXF format | ✅ PASS |
| Deep format | ✅ PASS |
| Wrapper script | ✅ PASS |
| Conan test_package | ✅ PASS |
| W3 CI simulation | ✅ PASS |
