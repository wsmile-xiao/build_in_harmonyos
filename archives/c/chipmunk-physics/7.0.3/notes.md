# chipmunk-physics 7.0.3 适配笔记

## 编译环境

- 构建系统: cmake (cmake version 4.1.2)
- 编译日期: 2026-06-18
- 编译器: clang 15.0.4 / clang++
- CFLAGS: -fPIC -O2
- 操作系统: HarmonyOS (鸿蒙)
- 架构: aarch64
- 状态: published

## 编译步骤

### 1. 源码获取

原始下载 URL `https://chipmunk-physics.net/release/Chipmunk-7.x/Chipmunk-7.0.3.tgz` 存在两个问题：
1. SSL 证书自签名导致验证失败
2. 路径返回 404

替代方案：通过 GitHub 仓库 `slembcke/Chipmunk2D` 使用 `git clone --depth 1 --branch Chipmunk-7.0.3` 获取源码，然后打包为 tar.gz 放置到 `$TMPDIR/builds/` 供 init-build 使用。

### 2. 初始化编译环境

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py init-build chipmunk-physics 7.0.3 \
  --url=https://chipmunk-physics.net/release/Chipmunk-7.x/Chipmunk-7.0.3.tgz
```

init-build 成功检测到已存在的 tarball 并跳过下载，完成解压、档案创建、依赖检查和环境验证。

### 3. CMake 配置

首次尝试仅使用 `-DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX`（遵循 R1 参数最少化），但 CMake 报错找不到 OpenGL——这是 demo 应用程序的依赖。

**修复**：添加 `-DBUILD_DEMOS=OFF` 禁用 demo 构建目标。核心物理库不需要 OpenGL。

```bash
cd $BUILD_SRC_DIR
mkdir build && cd build
cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DBUILD_DEMOS=OFF ..
```

CMake 输出：
```
Configuring Chipmunk2D version 7.0.3
-- Configuring done (2.3s)
-- Generating done (0.1s)
-- Build files have been written to: .../build
```

### 4. 编译

```bash
make -j2
```

首次编译失败，错误：`fatal error: 'sys/sysctl.h' file not found`

修复后重新编译成功：
```
[ 62%] Linking C static library libchipmunk.a
[ 63%] Linking C shared library libchipmunk.so
[ 81%] Built target chipmunk_static
[100%] Built target chipmunk
```

### 5. Staging 安装（R20 DESTDIR 模式）

```bash
make install DESTDIR=$TEST_PREFIX
```

安装文件：
- `lib/libchipmunk.so` (178,560 bytes)
- `lib/libchipmunk.a` (240,018 bytes)
- `include/chipmunk/*.h` (30 个头文件)

### 6. 测试

- `ctest`：无测试目标（CMake 项目未定义 test target，demo 需 OpenGL 已禁用）
- 功能测试：编写测试程序验证 7 项核心 API（空间创建、重力设置、刚体创建、碰撞体创建、物理步进等），动态链接和静态链接均通过

### 7. 预编译包制作

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py package chipmunk-physics 7.0.3
```

输出：
```
chipmunk-physics-7.0.3-ohos-aarch64.tar.gz: 662KB
```

### 8. 本地安装（模拟用户部署）

```bash
make install  # 不带 DESTDIR，安装到 $DEFAULT_PREFIX
```

### 9. 收尾

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py finish chipmunk-physics 7.0.3 published
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 | 铁律 |
|---|------|------|----------|------|
| 1 | 源码下载 SSL 证书验证失败 + URL 404 | chipmunk-physics.net 证书自签名且路径变更 | 通过 GitHub git clone 获取源码，打包后放置到预期路径 | R10 |
| 2 | CMake 找不到 OpenGL (`Could NOT find OpenGL`) | demo 应用需要 OpenGL，鸿蒙系统无 OpenGL 库 | 添加 `-DBUILD_DEMOS=OFF` 禁用 demo（核心物理库不需要） | R1 |
| 3 | `fatal error: 'sys/sysctl.h' file not found` | 现代系统（鸿蒙/Linux 内核 5.x+）已移除 sys/sysctl.h | 用 `#ifdef __APPLE__` 守卫 `#include <sys/sysctl.h>`（sysctlbyname 仅在 Apple 分支使用） | R8 |
| 4 | manifest 缺少 build_system 字段 | init-build 模板默认 autotools | 手动更新为 cmake，添加 configure_options | R15 |
| 5 | verify-build G4 报 "manifest 缺少 build_system" | 同 #4 | 更新 manifest.yaml | — |
| 6 | 补丁计数不一致 (manifest=0 vs disk=1) | finish 生成补丁后未更新 manifest patches_applied | 手动更新 patches_applied 列表 | — |

## 源码修改

### 补丁：0001-src-cpHastySpace.c.patch

**文件**: `src/cpHastySpace.c`
**类型**: 平台兼容性修复
**守卫**: `#ifdef __APPLE__`

**问题**：`#include <sys/sysctl.h>` 在非 Apple 平台（鸿蒙/Linux）不可用。该头文件在 Linux 内核 5.5+ 中被移除。

**分析**：通过 grep 确认，`sysctl.h` 的唯一使用者是 `sysctlbyname("hw.ncpu", ...)`，该调用位于 `#ifdef __APPLE__` 分支内。非 Apple 平台走 `else` 分支（`threads = 1`），不需要 sysctl。

**修复**：

```c
// Before:
#ifndef _WIN32
#include <sys/sysctl.h>
#include <pthread.h>

// After:
#ifndef _WIN32
#ifdef __APPLE__
#include <sys/sysctl.h>
#endif
#include <pthread.h>
```

**影响范围**：仅影响 `cpHastySpace` 多线程物理空间的线程数检测。在非 Apple 平台，`threads` 默认为 1（单线程模式），不影响物理模拟正确性。

## 依赖版本

| 依赖 | 版本 | 类型 | 说明 |
|------|------|------|------|
| cmake | 4.1.2 | 构建工具 | CMake 构建系统 |
| clang | 15.0.4 | 编译器 | C/C++ 编译器 |
| make | 4.4.1 | 构建工具 | GNU Make |

无运行时依赖。Chipmunk 是纯 C 库，仅使用标准 C 库和 pthread（cpHastySpace 多线程支持）。

## 验证结果

### 库文件
```
libchipmunk.a:  240,018 bytes (静态库, 32个目标文件)
libchipmunk.so: 178,560 bytes (共享库, ELF 64-bit LSB arm64)
```

### 头文件（30个）
```
chipmunk.h, chipmunk_ffi.h, chipmunk_private.h, chipmunk_structs.h,
chipmunk_types.h, chipmunk_unsafe.h, cpArbiter.h, cpBB.h, cpBody.h,
cpConstraint.h, cpDampedRotarySpring.h, cpDampedSpring.h, cpGearJoint.h,
cpGrooveJoint.h, cpHastySpace.h, cpMarch.h, cpPinJoint.h, cpPivotJoint.h,
cpPolyShape.h, cpPolyline.h, cpRatchetJoint.h, cpRobust.h,
cpRotaryLimitJoint.h, cpShape.h, cpSimpleMotor.h, cpSlideJoint.h,
cpSpace.h, cpSpatialIndex.h, cpTransform.h, cpVect.h
```

### 功能测试（动态链接）
```
[PASS] cpSpaceNew: 空间创建成功
[PASS] cpSpaceSetGravity: 重力设置成功 (y=100.00)
[PASS] cpSpaceGetIterations: 迭代次数=10
[PASS] cpBodyNew: 刚体创建成功 (mass=10.0, moment=500.00)
[PASS] cpBodySetPosition: 位置=(50.0, 100.0)
[PASS] cpCircleShapeNew: 圆形碰撞体创建成功 (radius=10.0)
[PASS] cpSpaceStep: 步进模拟完成 dt=0.0167
所有功能测试全部通过 ✓
```

### 功能测试（静态链接）
```
[PASS] cpSpaceNew: 空间创建成功
[PASS] cpSpaceSetGravity: 重力设置成功 (y=100.00)
[PASS] cpSpaceGetIterations: 迭代次数=10
[PASS] cpBodyNew: 刚体创建成功 (mass=10.0, moment=500.00)
[PASS] cpBodySetPosition: 位置=(50.0, 100.0)
静态链接运行退出码: 0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| chipmunk-physics-7.0.3-ohos-aarch64.tar.gz | 662KB | 预编译包（库+头文件） |
| chipmunk-physics-7.0.3-ohos-aarch64-debug.tar.gz | 80KB | 调试符号包 |
| 0001-src-cpHastySpace.c.patch | 14.4KB | sys/sysctl.h 平台兼容性补丁 |

## 注意事项

1. **BUILD_DEMOS=OFF 是必需的**：demo 应用依赖 OpenGL，鸿蒙系统无 OpenGL 库。核心物理库功能不受影响。
2. **sys/sysctl.h 修复仅影响 cpHastySpace.c**：多线程物理空间的线程数检测在非 Apple 平台回退为单线程（`threads = 1`），不影响物理模拟正确性。
3. **无 pkg-config 文件**：Chipmunk 的 CMake 构建系统不生成 .pc 文件。使用者需通过 `-I.../include/chipmunk -L.../lib -lchipmunk` 或 CMake `find_package` 链接。
4. **下载 URL 不可靠**：chipmunk-physics.net 存在 SSL 证书和路径问题，建议使用 GitHub 仓库作为源码获取渠道。
**预编译包**: chipmunk-physics-7.0.3-ohos-aarch64.tar.gz (662KB)

## 对话记录

### 对话 #1: 初始化与编译 (2026-06-18)

**用户请求**: 编译 chipmunk-physics 7.0.3

**执行步骤**:
1. 加载编译 SKILL (openharmony-compile-agent)
2. 初始化 SKILL_ROOT 环境变量
3. 运行 init-build（源码下载失败 → GitHub git clone 替代）
4. CMake 配置（首次失败：OpenGL 缺失 → 添加 -DBUILD_DEMOS=OFF）
5. make 编译（首次失败：sys/sysctl.h 缺失 → #ifdef __APPLE__ 守卫修复）
6. make install DESTDIR=/storage/Users/currentUser/tmp/test-install-chipmunk-physics-7.0.3（staging 安装成功）
7. ctest（无测试目标，跳过）
8. 功能测试（编写 7 项 API 测试程序，动态+静态链接均通过）
9. ohc-run.py package（预编译包制作成功，662KB）
10. make install（安装到 /storage/Users/currentUser/usr/local）
11. ohc-run.py finish published（收尾成功，补丁生成+归档关闭+质量门禁通过）
12. ohc-run.py verify-build（G0-G4 质量门禁复查通过）

**遇到的问题**: 源码下载失败、OpenGL 缺失、sys/sysctl.h 头文件不存在、manifest 字段缺失
**解决方案**: 见上方遇到的问题与解决方案表格
**最终结果**: published，预编译包 662KB，1 个补丁，质量门禁 PASS

### 对话 #2: 补充归档文件 (2026-06-18)

**用户反馈**: 缺少真实执行的测试报告，且归档文件内容缺少

**补充内容**:
1. 重写 test-report.md，包含 ctest 实际输出、库文件验证、功能测试完整日志、预编译包内容验证
2. 创建软件级 README.md（archives/c/chipmunk-physics/README.md）
3. 创建软件级 manifest.yaml（archives/c/chipmunk-physics/manifest.yaml，含版本索引）
4. 更新版本级 manifest.yaml：补充 knowledge_gained（4 条知识）和补丁分类信息
5. 重写 notes.md：补充对话记录、详细的编译步骤、完整的验证结果
6. 重新运行 finalize-archive：缺失项从 1 降为 0

---

**编译结束**: 2026-06-18
**最终状态**: published
**质量门禁**: PASS (G1-G4 全通过)
**预编译包**: chipmunk-physics-7.0.3-ohos-aarch64.tar.gz (662KB)
