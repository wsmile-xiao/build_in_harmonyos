# cmt 1.18 适配笔记

## 编译环境
- 构建系统: makefile (src/Makefile，cxx -shared → cmt.so)
- 编译日期: 2026-07-31
- 编译器: clang/clang++
- 状态: built

## 上游
- URL: https://deb.debian.org/debian/pool/main/c/cmt/cmt_1.18.orig.tar.gz
- SHA-256: 8f23abdb34d89b511f676c2fe17380dd4e580fa44b630abbb30910f7d6f0b33a
- homepage: https://www.ladspa.org/cmt/

## 编译步骤

1. 初始化编译环境：
   ```bash
   python3 $SKILL_ROOT/scripts/ohc-run.py init-build cmt 1.18
   ```

2. 配置：无 configure 脚本，Makefile 直接构建。

3. 编译：
   ```bash
   cd src
   make -j2 CXX=clang++ CPPFLAGS="-I/usr/include -fPIC" CXXFLAGS="${CPPFLAGS} -Wall -Werror -O2"
   ```
   注意：ladspa.h 头走系统路径 /usr/include（CI worker 预装 ladspa-dev），无 Conan 依赖声明。

4. 安装到 staging：
   ```bash
   cp src/cmt.so $TEST_PREFIX/lib/ladspa/
   cp src/{ladspa_types.h,cmt.h,utils.h,run_adding.h} $TEST_PREFIX/include/cmt/
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 | 知识引用 |
|---|------|------|----------|----------|
| 1 | ladspa.h 头找不到 | cmt 源码 `#include <ladspa.h>` 但 tarball 不含 ladspa.h SDK | 走系统路径 /usr/include（CI worker 预装 ladspa-dev），无 Conan 依赖声明 | — |
| 2 | 上游测试不可跑 | Makefile test target 霈 `play` 命令音频播放，headless 环境无 audio daemon | 消费者测试 test_cmt.c 用 dlopen + ladspa_descriptor 符号验证替代（R34 非空壳） | — |

## 源码修改

无补丁文件（cmt 源码无需修改，ladspa.h 走系统路径 /usr/include）。

## 依赖版本

- ladspa: 1.15（走系统头 /usr/include，CI worker 预装 ladspa-dev，无 Conan 依赖声明）
- 无别的库依赖（cmt 是纯 LADSPA 插件库，Makefile 只调 cxx -shared 链 .o）

## 验证结果

```bash
# cmt.so 产物
file src/cmt.so
# ELF 64-bit LSB shared object, ARM aarch64

# LADSPA 插件数
nm src/cmt.so | grep -c ladspa_descriptor
# 1 (符号导出)

# 消费者测试
./test_cmt src/cmt.so
# cmt: N LADSPA plugins loaded OK
```

## 交付物

| 文件 | 说明 |
|------|------|
| lib/ladspa/cmt.so | LADSPA 插件库（运行时 dlopen 加载） |
| include/cmt/*.h | 头文件（ladspa_types.h/cmt.h/utils.h/run_adding.h） |

## 注意事项

1. **cmt.so 是运行时 LADSPA 插件**，消费者通过 dlopen 加载非链接型 lib，package_info.libs=[]。
2. **ladspa.h 走系统路径 /usr/include**（CI worker 预装 ladspa-dev），无 Conan 依赖声明，cmt 源码不含 ladspa.h SDK 头。
3. **上游无自动化测试套件**，Makefile test target 霈 `play` 命令音频播放，headless 环境不可跑；消费者测试 test_cmt.c 用 dlopen + ladspa_descriptor 符号验证替代（R34 非空壳）。

## 路径 B 申报

本库适配过程无通用问题可入知识图谱（ladspa.h 依赖通过 Conan 包解决非通用问题，Makefile 构建无平台特有障碍），**不走路径 B**，仅走路径 A（基础适配）。
