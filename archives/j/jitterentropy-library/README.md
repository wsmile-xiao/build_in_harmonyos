# jitterentropy-library

jitterentropy-library 是一个基于 CPU 执行时间抖动的熵源库，用于生成高质量的随机数。

## 功能概述

- 提供 CPU jitter entropy 熵源
- 支持 FIPS 模式
- 无需硬件 RNG
- 跨平台支持
- 提供 shared library 和 static library

## OHOS 适配要点

### 编译要求
- **构建系统**：直接 Makefile 编译，无 configure 步骤
- **编译器**：必须设置 `CC=clang`（系统无 gcc/cc）
- **安装方式**：系统无 install 命令，需手动安装（mkdir + cp）

### 已知问题
1. **HMDFS 硬链接限制**：shutil.copytree 使用 os.link 会失败，需改用 `cp -r`
2. **符号链接循环**：源码包 tests/raw-entropy/recording_userspace 目录有循环，需排除
3. **下载服务器**：Savannah 可能超时，建议使用 GitHub 镜像

### 与 Linux 的差异
- Linux：可用 `make install` 自动安装
- OHOS：需手动执行安装步骤（创建目录 + 复制文件）
- 产物相同：共享库、静态库、头文件完全兼容

## 依赖关系

### 编译依赖
无特殊依赖，仅需标准 libc

### 运行依赖
- libc.so（标准 C 库）

## 编译版本

| 版本 | 状态 | 日期 | 产物 |
|------|------|------|------|
| 3.4.0 | built | 2026-05-29 | lib/libjitterentropy.so.3.4.0, lib/libjitterentropy.a, include/*.h |

## 使用示例
```c
#include <jitterentropy.h>

int main() {
    jent_entropy_init();
    struct rand_data *ec = jent_entropy_collector_alloc(0, JENT_FORCE_FIPS);
    char buf[32];
    jent_read_entropy(ec, buf, sizeof(buf));
    jent_entropy_collector_free(ec);
    return 0;
}
```

## 许可证
- BSD
- GPL v2

## 官方网站
https://github.com/smuellerDD/jitterentropy-library