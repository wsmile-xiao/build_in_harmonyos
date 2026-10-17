# DRAFT — CMake 多压缩/多后端库在 OHOS 交叉环境的依赖接线统一模式

## 一句话
OHOS conan 工具链把 `CMAKE_FIND_ROOT_PATH_MODE_*` 设为 ONLY 后，CMake 多后端库（libarchive/libtiff 家族）的依赖探测必然失败；**预设 Find 模块缓存变量**（`<PKG>_INCLUDE_DIR` + `<PKG>_LIBRARY` 指向 conan 依赖实际路径）是唯一可靠接线法，双库实证。

## 错误面（何时命中）
```
CMake Error at ...: Could NOT find ZLIB (missing: ZLIB_LIBRARY ZLIB_INCLUDE_DIR)
CMake Error at ...: Could NOT find ZSTD (missing: ZSTD_LIBRARY ZSTD_INCLUDE_DIR)
```
任何 OHOS 交叉构建中多后端/多压缩库的 `find_package` 报 Could NOT find。

## 根因
`ohos.toolchain.cmake` 设 `CMAKE_FIND_ROOT_PATH_MODE_{PROGRAM/LIBRARY/INCLUDE/PACKAGE}=ONLY`，find_path/find_library 只搜 NDK sysroot，conan 依赖安装路径全被过滤。标准 Find 模块与上游自带模块（无 CONFIG 模式）双双中招。

## 修复（可复制模式）
```python
# conanfile.py generate()/build() 内
import glob
_wire = [
    ("zlib",       "ZLIB_INCLUDE_DIR",    ["ZLIB_LIBRARY"],           ["libz.so", "libz.a"]),
    ("bzip2",      "BZIP2_INCLUDE_DIR",   ["BZIP2_LIBRARIES"],        ["libbz2.so", "libbz2.a"]),
    ("xz_utils",   "LIBLZMA_INCLUDE_DIR", ["LIBLZMA_LIBRARY"],        ["liblzma.so", "liblzma.a"]),
    ("zstd",       "ZSTD_INCLUDE_DIR",    ["ZSTD_LIBRARY"],           ["libzstd.so", "libzstd.a"]),
]
for dep, inc_var, lib_vars, cands in _wire:
    info = self.dependencies[dep].cpp_info.aggregated_components()
    inc = next(iter(info.includedirs), "")
    lib = ""
    for d in info.libdirs:
        for c in cands:
            hit = glob.glob(os.path.join(d, c))
            if hit: lib = hit[0]; break
        if lib: break
    defs[f"-D{inc_var}={inc}"]
    defs[f"-D{lib_vars[0]}={lib}"]
```
关键语义：**已设的 cache 变量 find_* 不再搜索**。

## 为什么不用备选
- `MODE=BOTH` + 追加 ROOT_PATH：破坏 ONLY 隔离，曾致宿主 sysroot 污染（链接错架构）
- CONFIG 模式（CMakeDeps）：老库（libarchive 3.7.7/libtiff 4.7.2）的 find_package 不带 CONFIG
- pkg-config：上游模块不带 .pc 时不可用

## 证据
- **libarchive 3.7.7**（PR #8329，2026-09-05）：四后端（zlib/bzip2/xz/zstd）全预设接线，CI #40012 绿，上游 783/800（17 失败均为 hmfs 平台限制）
- **libtiff 4.7.2**（main 已合入）：同法接线 zlib/libdeflate/libjpeg-turbo/zstd，配方注释含同款结论

## 适用家族
libarchive、libtiff、gdal、openexr、vips、graphicsmagick 等一切"多可选后端 + CMake + 老式 Find 模块"的库。
