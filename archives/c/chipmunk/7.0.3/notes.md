# chipmunk 7.0.3 适配笔记

## 编译环境

- 构建系统: CMake（>= 3.7，`project(chipmunk)`，纯 C99 `-std=gnu99`）
- 平台任务: contrib-6446（chipmunk 7.0.3），claimer Ember5843，认领时间 2026-09-15T04:20Z
- 目标平台: HarmonyOS PC arm64（`os=OHOS arch=armv8 compiler=clang 15 libc++`），本机原生构建
- 依赖: **无外部依赖**（仅 libc + libm；pthread 在 musl libc 内）
- 上游: https://github.com/slembcke/Chipmunk2D （tag Chipmunk-7.0.3，2406 stars / 362 forks）
- 源码 sha256: `1e6f093812d6130e45bdf4cb80280cb3c93d1e1833d8cf989d554d7963b7899a`
- 语言实测（R47 lang-preflight）: 源文件 60 个（c:60, bash:1），主体 C 占比 100%

## 源码面貌（摸底结论）

- 交付形态: `libchipmunk.a`（static）/ `libchipmunk.so.7`（shared, SOVERSION=7）+
  `include/chipmunk/*.h` 平铺全量头（含 constraints 系列头）
- 上游 CMake 选项: BUILD_DEMOS（默认 ON，需 OpenGL+GLFW）、BUILD_SHARED、BUILD_STATIC、
  INSTALL_STATIC、FORCE_CLANG_BLOCKS（Clang 默认 ON，`-fblocks`）
- block API（`cpSpaceEachBody_b` 等）只把 block 作为**形参**接收并调用，库内不创建
  逃逸字面量 → 不需要 blocks 运行库
- cpHastySpace.c 用 pthread（musl libc 内置）；上游给 shared target 显式链 `m`
- 上游**无测试套件**：无 tests/、无 CTest 注册、demo 是 OpenGL 交互程序
- `${chipmunk_constraint_header}` 在 src/CMakeLists.txt 被引用但从未定义 → 空表 install
  为无害 no-op，无需补丁
- GitHub tag tarball 顶层目录为 `Chipmunk2D-Chipmunk-7.0.3`，配方做扁平化解包

## 编译步骤（设备实机）

```sh
cd $HOME/build_in_harmonyos
python3 scripts/ohc-run.py conan-verify chipmunk 0.1.4 --project-dir "$PWD"   # 版本号按 7.0.3
```

## 选项映射

| Conan | 上游变量 |
|---|---|
| shared=False | BUILD_SHARED=OFF, BUILD_STATIC=ON, INSTALL_STATIC=ON |
| shared=True | BUILD_SHARED=ON, BUILD_STATIC=OFF, INSTALL_STATIC=OFF |
| — | BUILD_DEMOS=OFF, INSTALL_DEMOS=OFF（OpenGL/GLFW 不存在） |

注意上游 `if(BUILD_DEMOS OR INSTALL_STATIC) set(BUILD_STATIC ON FORCE)`：
shared 模式必须把 INSTALL_STATIC 也关掉，否则 BUILD_STATIC 被强制回写、两份库都装。

## 收编说明

- 分支 feat/chipmunk-7.0.3 上存在 09-07 认领者 lkyz 的遗留提交（其任务已退回 pending，本次由 Ember5843 重新认领）：其补丁 0001-sysctl-apple-guard.patch 经核实**确为必要**（OHOS musl 无 sys/sysctl.h），已通过 conandata patches 正式收编；其 test_package/test.c 由本配方的消费者测试替代后移除。合并保留其历史提交，未覆盖他人工作。

## 状态

- [x] 配方四件套
- [x] 设备实机 conan create + conan-verify（G0-G3）
- [x] test_package 消费者测试 9/9
- [x] push / PR / 平台绑定 / 提审
