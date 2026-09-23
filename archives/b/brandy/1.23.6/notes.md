# brandy 1.23.6 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-06
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤

```bash
# 语言预检（R47）
python3 $SKILL_ROOT/scripts/ohc-run.py lang-preflight brandy 1.23.6 --src <源码目录>
# → detected=c，与任务 cpp 兼容族，通过

# init-build（--project-dir 必须指向工作区仓库，避免误写 SKILL 目录）
python3 $SKILL_ROOT/scripts/ohc-run.py init-build brandy 1.23.6 \
  --no-download --project-dir <工作区仓库>

# 手动编译（探索阶段）
cd $BUILD_SRC_DIR && mkdir build && cd build
CC=clang cmake .. -DCMAKE_BUILD_TYPE=Release
make -j2

# 上游测试（R51 三步法）
# ctest Regressions 注册项: prove --exec <build>/sbrandy -r t/
# 注: ctest 直接运行失败是 prove 相对路径 t/ 在 build 目录解析问题；
#     从源码目录以绝对路径运行 prove 全部通过:
cd $BUILD_SRC_DIR
prove --exec <build>/sbrandy -r t/
# → t/01count.t .. ok, Files=1, Tests=3, PASS

# Staging 验证
make install DESTDIR=$TEST_PREFIX
# → usr/local/bin/sbrandy + usr/local/bin/tbrandy
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | src/keyboard.c 编译报 `keyset`/`FD_SET`/`select` 未声明 | `<sys/select.h>` 仅 `#ifdef TARGET_OPENBSD` 下包含（116 行），OHOS 映射为 TARGET_LINUX/TARGET_UNIX，不包含该头文件；而 waitkey() 使用 fd_set/select() | 将 `<sys/select.h>` 包含扩展至所有类 Unix 平台（TARGET_OPENBSD/LINUX/NETBSD/FREEBSD/GNU/MACOSX/SUNOS） |
| 2 | ctest Regressions 失败（退出码 214，无 TAP 输出） | ctest 在 build 目录运行 `prove --exec sbrandy -r t/`，相对路径 t/ 在 build 目录不存在 | 非测试失败：从源码目录以绝对路径运行 prove，t/01count.t 3 断言全部通过；已在 MANIFEST/PR 如实说明 |

## 源码修改

- `src/keyboard.c`: `<sys/select.h>` 包含条件从 `#ifdef TARGET_OPENBSD` 扩展至类 Unix 平台集合（探索阶段直接改源码，补丁由 finish refresh-patch --auto 生成）

## 依赖版本

- 无外部依赖（仅系统库 m/dl/pthread/rt）
- SDL 1.2 图形版为可选特性（find_package(SDL 1.2)），OHOS 制品仓无 SDL 1.2 → 方案 A 关闭，仅构建核心 sbrandy/tbrandy（文本/简单文本 UI），解释器功能完整

## 验证结果

```bash
sbrandy --version
# → Matrix Brandy BASIC VI version 1.23.6+dev (Linux/ARM-64bit) 19 Oct 2025

prove --exec <build>/sbrandy -r t/
# → All tests successful. Files=1, Tests=3
```
---

**编译结束**: 2026-09-07 15:46
**最终状态**: built
