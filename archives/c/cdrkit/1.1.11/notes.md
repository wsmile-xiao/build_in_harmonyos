# cdrkit 1.1.11 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-06
- 编译器: clang/clang++
- 状态: published (conan-verify passed)
- 源码: https://ftp.debian.org/debian/pool/main/c/cdrkit/cdrkit_1.1.11.orig.tar.gz

## 依赖
- bzip2/1.0.8 (conan ohpcd)
- zlib/1.3.1 (conan ohpcd)

## 适配修改 (8 个补丁)

### 1. CMakeLists.txt
- 添加 `cmake_minimum_required(VERSION 3.5)` (CMake 4.x 兼容)

### 2. genisoimage/checksum.c
- 替换 `pthread_cancel` 为优雅线程关闭 (OHOS 不实现 pthread_cancel)
- 使用条件变量信号通知线程退出

### 3. genisoimage/genisoimage.h
- 添加 `extern` 到 `outfile` 声明 (修复 lld 重复符号)

### 4-5. genisoimage/sha256.h, sha512.h
- 添加 `__THROW` 回退定义 (OHOS bionic libc 不定义 __THROW)

### 6. include/xconfig.h.in
- 禁用 `HAVE_RCMD` (OHOS 无 rcmd())
- 禁用 `HAVE_SETREUID` (OHOS 无 setreuid, 导致 SIGSYS)
- 禁用 `HAVE_SETREGID` (OHOS 无 setregid, 导致 SIGSYS)

### 7. wodim/CMakeLists.txt
- 条件链接 libcap (OHOS 有 sys/capability.h 但无 libcap 库)

### 8. wodim/wodim.c
- 使用内核 `capget/capset` API 替代 libcap 用户空间 API
- `get_cap()` 函数使用 `__user_cap_header_struct` 和 `__user_cap_data_struct`

## 交付物
- conanfile.py + conandata.yml + test_package/
- 8 个补丁文件 (patches/)
- commands.json (命令行工具声明)

## 结束
COMPLETED
