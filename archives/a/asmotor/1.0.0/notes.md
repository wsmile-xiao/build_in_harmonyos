# asmotor 1.0.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-19
- 编译器: clang 15.0.4 / clang++
- 状态: published

## 编译步骤

1. init-build: 官方源 https://github.com/asmotor/asmotor archive release/1.0.0 tag
   - 源码 tarball SHA-256: 2e9cf0bb90f8966bd35edf0002fa098dd7b4c971da420be219483a77cfe64d29
   - util/ 为官方 submodule (asmotor-util)，release/1.0.0 引用提交 3dfef3089f6f05b2f03ebb0b147a4b01855720d5；tarball 不含 submodule，需单独拉取该提交放入 util/（git clone asmotor-util 后 checkout 3dfef30）
2. cmake 配置: `cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DCMAKE_INSTALL_PREFIX=<prefix> <src>`（debug/release 均验证）
   - 需要 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`：CMake 4.x 已移除对 <3.5 的兼容，ucm.cmake 内 `cmake_minimum_required` 版本过低导致配置失败
3. 编译: `cmake --build . -j2`（0 错误）
4. 安装: `cmake --install .`（DESTDIR staging 验证），产物为 8 个可执行文件 → 本库为 CLI 工具链，需 commands.json
   - bin/: motordcpu16 motor6502 motor68k motorz80 motormips motorschip xlib xlink
5. 上游测试: `test.sh` 逐个运行 test/<arch>/run.sh

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 配置失败 "Compatibility with CMake < 3.5 has been removed" | ucm.cmake 第 13 行 cmake_minimum_required 版本过旧，CMake 4.1.2 已移除 <3.5 兼容 | 配置时加 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` |
| 2 | 编译失败 "a function declaration without a prototype is deprecated [-Werror,-Wstrict-prototypes]" | 上游为 K&R 风格旧 C 代码（str_Empty()、expr_Pc() 等无原型声明），CMakeLists 开 -Wall -Wextra -pedantic -Werror | CMakeLists.txt 编译选项追加 `-Wno-strict-prototypes`（已通过 refresh-patch 固化） |
| 3 | 源码根 util/ 为空 | util 是 git submodule（asmotor-util），官方 tarball 不包含 submodule 内容 | 按 release/1.0.0 引用的精确提交 3dfef3089f6f05b2f03ebb0b147a4b01855720d5 拉取 asmotor-util 并放入 util/ |
| 4 | z80 测试 test_rot.asm / test_shift.asm 与自带 .answer 不符 | 上游 release/1.0.0 自身缺陷：(ix+d)/(iy+d) 间接寻址的旋转/移位指令（rl/rr/rlc/rrc/sla/sra/sll/srl）编码字节错误——实测 `rl (ix+1)` 输出 `DD CB 01 55`，而 Z80 规范与 tag 自带 answer 均为 `DD CB 01 16`；master 分支 answer 文件与 tag 完全一致但 z80 源码已重写（z80_section.c 新增等），判定为 tag 版本上游缺陷 | 非本适配引入；master 源码 z80_parse.c handleRotate 逻辑相同，输出差异源于 tag 自身。如实列入测试台账（z80 两用例不通过），不影响其余 7 个架构测试目录通过 |

## 源码修改

- CMakeLists.txt：非 MSVC 分支编译选项追加 `-Wno-strict-prototypes`（唯一源码修改，其余为配置参数）

## 依赖版本

- 无第三方运行时依赖（纯 C99 汇编器工具链，仅依赖 libc）
- 构建依赖：cmake 4.1.2 / make 4.4.1 / clang 15.0.4
- submodule: asmotor-util @ 3dfef3089f6f05b2f03ebb0b147a4b01855720d5

## 验证结果

```bash
# 编译（debug + release 均通过）
cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 <src> && cmake --build . -j2
# 上游测试：6502/680x0/common/dcpu-16/gameboy/mips/schip 全部通过（diff 无差异，退出码 0）
# z80: test_rot.asm、test_shift.asm 因上游 tag 编码缺陷与 answer 不符，其余 z80 用例通过
# staging: DESTDIR=<staging> cmake --install . → 8 个可执行文件（motordcpu16/motor6502/motor68k/motorz80/motormips/motorschip/xlib/xlink）
```
---

**编译结束**: 2026-09-19 21:54
**最终状态**: published
