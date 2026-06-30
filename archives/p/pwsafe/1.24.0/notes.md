# pwsafe 1.24.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-10
- 编译器: clang/clang++
- 状态: published

## 编译步骤

使用 cmake + make 编译：
```bash
cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_SYSTEM_NAME=OHOS .
make -j2
make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 不识别 OHOS 平台 | 缺少平台条件 | 添加 __OHOS__ 守卫条件 |
| 2 | secure_getenv 不可用 | OHOS musl 缺少此函数 | 用 getenv 替代，#ifdef __OHOS__ |
| 3 | keystub.cpp syscall 缺失 | seteuid 等在 OHOS 上未实现 | 添加 __OHOS__ 条件跳过 |
| 4 | run.cpp 编译错误 | /proc 文件系统差异 | 添加 __OHOS__ 守卫适配 |
| 5 | StringX.cpp mbstate_t 问题 | 头文件包含差异 | 显式包含 wchar.h |
| 6 | version.in 模板路径问题 | 本地路径硬编码 | 替换为可移植路径 |

## 交付物

| 文件 | 说明 |
|------|------|
| pwsafe-1.24.0-ohos-aarch64.tar.gz | 预编译包（含 pwsafe CLI） |
| pwsafe-1.24.0-ohos-aarch64-debug.tar.gz | debug 预编译包 |
