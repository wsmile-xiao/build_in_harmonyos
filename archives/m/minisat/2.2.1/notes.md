# minisat 2.2.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-03
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 平台: aarch64-unknown-linux-ohos (OpenHarmony)
- 状态: published

## 编译步骤

1. 下载源码: `https://github.com/stp/minisat/archive/refs/tags/releases/2.2.1.tar.gz`
2. 手动下载 tarball（SSL证书问题导致 init-build 直接下载失败），放置到 `~/tmp/builds/minisat-2.2.1.tar.gz`
3. 解压并初始化: `ohc-run.py init-build minisat 2.2.1 --no-download`
4. 创建 build 目录: `mkdir build && cd build`
5. cmake 配置:
```bash
cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
      -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
      -DCMAKE_C_FLAGS="-fuse-ld=bfd -fPIC -O2" \
      -DCMAKE_CXX_FLAGS="-fuse-ld=bfd -fPIC -O2" \
      -DCMAKE_EXE_LINKER_FLAGS="-fuse-ld=bfd" \
      -DCMAKE_SHARED_LINKER_FLAGS="-fuse-ld=bfd" \
      ..
```
6. 构建: `make -j1`（全部 4 个目标编译成功）
7. staging 安装: `make install DESTDIR=$TEST_PREFIX`（staging 目录产物完整）
8. ELF 签名: `ohc-run.py sign-elf` 对 bin/minisat, bin/minisat_core, lib/libminisat.so 签名
9. 本地安装: `make install`（不带 DESTDIR，安装到 ~/usr/local）
10. 功能验证: 实际 SAT 问题求解测试
11. 预编译包制作: `ohc-run.py package minisat 2.2.1`
12. 收尾: `ohc-run.py finish minisat 2.2.1 published`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `fatal error: 'fpu_control.h' file not found` | aarch64/OHOS 平台不提供 x86 FPU 控制头文件，源码用 `#if defined(__linux__)` 条件包含 | 修改 System.h: `#if defined(__linux__) && !defined(__OHOS__)` 排除 OHOS，用 track-edit 追踪修改 |
| 2 | 链接器报错 `Error loading shared library libxml2.so.16` | OHOS SDK 的 lld 链接器运行时依赖 libxml2.so.16 无法加载（即使 LD_LIBRARY_PATH 包含该路径） | cmake 添加 `-fuse-ld=bfd` 参数使用 GNU ld.bfd 链接器替代 lld |
| 3 | `cmake_minimum_required(VERSION 2.6)` 不兼容 cmake 4.x | cmake 4.1.2 不支持低于 3.5 的兼容版本，直接报错 | 添加 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` 绕过版本兼容检查 |
| 4 | init-build 下载失败（SSL证书和超时） | OHOS 平台 SSL 证书验证失败，GitHub 连接超时 | 手动用 curl -k 下载 tarball，放置到预期路径，再用 `--no-download` 选项 |

## 源码修改

- **0001-minisat-utils-System.h.patch**: 修改 `minisat/utils/System.h` 第 23 行，将 `#if defined(__linux__)` 改为 `#if defined(__linux__) && !defined(__OHOS__)`，排除 OHOS 平台对 `fpu_control.h` 的包含。补丁类型: platform_compat，守卫宏: `__OHOS__`。

## 依赖版本

- zlib 1.3.1（静态库 libz.a，路径 ~/usr/local/lib/libz.a）

## 功能验证结果（真实执行）

### SAT 可满足问题测试
```
输入: p cnf 2 1 / 1 2 0
命令: minisat test_sat_sat.cnf result.txt
结果: SATISFIABLE → 输出 "SAT" + 满足解 "1 -2 0" (x1=true, x2=false)
```

### UNSAT 不可满足问题测试
```
输入: p cnf 1 2 / 1 0 / -1 0
命令: minisat test_sat_unsat.cnf result.txt
结果: UNSATISFIABLE → 输出 "UNSAT"
```

### minisat_core 测试
```
命令: minisat_core test_sat_sat.cnf result.txt
结果: SATISFIABLE → 输出 "SAT" + 满足解 "-1 2 0" (x1=false, x2=true)
```

### 二进制和库文件
```
~/usr/local/bin/minisat       → ELF 64-bit LSB arm64, dynamic, 186,816 bytes ✅
~/usr/local/bin/minisat_core  → ELF 64-bit LSB arm64, dynamic, 158,144 bytes ✅
~/usr/local/lib/libminisat.so → ELF 64-bit LSB arm64, shared, 113,024 bytes ✅
~/usr/local/lib/libminisat.a  → ar archive (静态库), 155,090 bytes ✅
~/usr/local/include/minisat/  → 18 个头文件（mtl/11 + utils/3 + core/3 + simp/1）✅
```

### make check
N/A — minisat cmake 项目没有 `make check` 目标或测试套件

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| minisat-2.2.1-ohos-aarch64.tar.gz | 828KB (848,020 bytes) | 预编译包：含 bin/minisat + bin/minisat_core + lib/libminisat.a + lib/libminisat.so + include/minisat/ 全部头文件 |
| minisat-2.2.1-ohos-aarch64-debug.tar.gz | 186KB (186,928 bytes) | 调试符号包 |
| 0001-minisat-utils-System.h.patch | 1,091 bytes | OHOS 平台 fpu_control.h 适配补丁 |

## 注意事项

- minisat 提供两个可执行文件: `minisat`（简化版求解器，含预处理）和 `minisat_core`（核心求解器，不含预处理）
- cmake 默认 STATIC_BINARIES=ON，可执行文件链接静态库 libminisat.a
- 源码同时包含 Makefile 和 CMakeLists.txt，本版本使用 cmake 构建
- OHOS 平台 lld 链接器存在 libxml2.so.16 加载问题，所有 cmake 项目都可能需要 `-fuse-ld=bfd`
- G0 干净构建验证（clean_verify.py）不支持 cmake 构建系统，已知脚本限制，手动验证构建可重现

---

**编译结束**: 2026-06-03 17:59
**最终状态**: published