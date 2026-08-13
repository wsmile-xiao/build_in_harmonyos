# libzmf

libzmf is a library and a set of tools for reading and converting Zoner Draw
and Zebra file formats. It is part of the Document Liberation Project.

## Description
libzmf provides a C++ library (`libzmf-0.0`) that parses Zoner Callisto/Mantis
vector drawing files (`.zmf`) and feeds them through the librevenge content
interface. It is typically used by LibreOffice and other document converters
that rely on the Document Liberation Project stack.

## 已编译版本
- 0.0.2 (2026-07-30)

## 依赖
- librevenge/0.0.5 (core dependency, provides librevenge-0.0)
- boost/1.84.0 (header-only: cstdint, math/constants, optional, variant)
- zlib/1.3.1 (PNG chunk compression in Zoner format)
- libpng/1.6.43 (embedded PNG preview decoding)
- icu/73.2 (Unicode normalization for text records)

## 特性
- Parses Zoner Draw vector drawing records
- Extracts embedded PNG preview images
- Exposes content through librevenge's RVNGDrawingContent interface

## 使用方法
作为文档解析库使用，通常通过 librevenge 的抽象接口间接调用：

```cpp
#include <libzmf/libzmf.h>
libzmf::ZMFDocument document;
```
