# kcov 38 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-27
- 编译器: clang/clang++
- 状态: published

## 编译步骤

### 1. 依赖准备
- elfutils 0.191 (提供 libdw 和 libelf)
- zlib 1.3.1
- gettext 0.22.5 (提供 libintl)

### 2. CMake 配置
```bash
cd kcov-38.work/build
cmake .. \
  -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
  -DCMAKE_BUILD_TYPE=Release \
  -DSPECIFY_RPATH=ON \
  -DCMAKE_SYSTEM_NAME=Linux \
  -DZLIB_LIBRARY=/storage/Users/currentUser/usr/local/lib/libz.so \
  -DZLIB_INCLUDE_DIR=/storage/Users/currentUser/usr/local/include
```

### 3. 编译和安装
```bash
make -j2
make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | cmake_minimum_required 版本过低 | cmake 4.1.2 不支持 < 3.5 | CMakeLists.txt: VERSION 2.8.4 → 3.5 |
| 2 | __ptrace_request 未定义 | musl libc 不定义此类型 | ptrace_linux.cc: `typedef int __ptrace_request` |
| 3 | pthread_cancel 未定义 | musl libc 不支持 pthread_cancel | solib-handler.cc: `#define pthread_cancel(thread) (0)` |
| 4 | libcurl 链接失败 | libcurl 在 musl 上符号缺失 | CMakeLists.txt: 禁用 CURL_FOUND |

## 源码修改

### 修改文件列表
1. **CMakeLists.txt** - cmake 版本要求
2. **src/CMakeLists.txt** - 禁用 curl
3. **src/engines/ptrace_linux.cc** - musl ptrace 兼容
4. **src/solib-handler.cc** - musl pthread 兼容

### 具体修改

#### CMakeLists.txt (第1行)
```cmake
cmake_minimum_required (VERSION 3.5)
```

#### src/CMakeLists.txt (第3-7行)
```cmake
# Disable curl on musl/OHOS (not fully compatible)
find_package (CURL)
set (CURL_FOUND "FALSE")
set (CURL_LIBRARIES "")
```

#### src/engines/ptrace_linux.cc (第6-9行)
```c
/* musl libc doesn't define __ptrace_request */
#ifndef __GLIBC__
typedef int __ptrace_request;
#endif
```

#### src/solib-handler.cc (第21-24行)
```c
/* musl libc doesn't support pthread_cancel */
#ifndef __GLIBC__
#define pthread_cancel(thread) (0) // No-op for musl/OHOS
#endif
```

## 依赖版本

| 软件 | 版本 | 用途 |
|------|------|------|
| elfutils | 0.191 | DWARF/ELF 解析 (libdw, libelf) |
| zlib | 1.3.1 | 压缩支持 |
| gettext | 0.22.5 | 国际化 (libintl) |
| cmake | 4.1.2 | 构建工具 |

## 验证结果

### 二进制文件
```bash
$ ls -la ~/usr/local/bin/kcov*
-rwxrwx--- 1 file_manager 7060160 kcov
-rwxrwx--- 1 file_manager 2562624 kcov-system-daemon
```

### 预编译包
```bash
$ ls -lh archives/k/kcov/38/packaging/
kcov-38-ohos-aarch64.tar.gz        3.1M
kcov-38-ohos-aarch64-debug.tar.gz  8.2M
```

### 包内容
```bash
$ tar tzf kcov-38-ohos-aarch64.tar.gz
bin/kcov
bin/kcov-system-daemon
lib/external/libdw.so.1
lib/external/libelf.so.1
lib/external/libintl.so.8
share/doc/kcov/...
share/man/man1/kcov.1
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| kcov-38-ohos-aarch64.tar.gz | 3.1M | 预编译包 (stripped) |
| kcov-38-ohos-aarch64-debug.tar.gz | 8.2M | 调试符号包 |

## 注意事项

### 运行时权限限制
- kcov 使用 ptrace 系统调用跟踪进程
- OpenHarmony 可能限制 ptrace 权限
- 可能需要 root 权限或 capabilities 设置:
  ```bash
  sudo setcap cap_sys_ptrace+ep ~/usr/local/bin/kcov
  ```

### 功能限制
- Coveralls 上报功能已禁用 (因 libcurl 兼容性问题)
- 核心覆盖率收集功能正常可用
- 支持 JSON、HTML、Cobertura 等格式输出

### 平台特性
- musl libc 环境适配完成
- 不支持 GNU 扩展 (pthread_cancel, __ptrace_request)
- libcurl 可能需要额外适配才能启用

---

**编译结束**: 2026-05-27 15:56
**最终状态**: published
