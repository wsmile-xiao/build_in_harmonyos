---
title: SDL3 3.4.8 HarmonyOS 编译记录
---

## 编译过程

### 初始化
- 下载 SDL3 3.4.8 源码（从 GitHub release）
- 解压到 `/storage/Users/currentUser/builds/sdl3-3.4.8.work`

### 平台适配修改

**1. CMakeLists.txt（补丁 0001）**
- 添加 HarmonyOS 平台检测：`set(OHOS true)`
- 定义 `__OHOS__` 宏
- 将 HarmonyOS 视为 Unix-like 系统（启用 pthread）
- 禁用 SDL_TRAY（HarmonyOS 无 Gtk 支持）

**2. SDL_platform_defines.h（补丁 0002）**
- 定义 `SDL_PLATFORM_OHOS`
- 取消定义 `SDL_PLATFORM_LINUX`（避免错误识别为 Linux）

**3. SDL.c（补丁 0003）**
- 排除 `SDL_Gtk_Quit()` 调用（HarmonyOS 无 Gtk）

**4. SDL_systhread.c（补丁 0004）**
- 禁用 `pthread_setcanceltype`（HarmonyOS pthread 实现不完整）

### 编译

```bash
cd build
cmake .. -DCMAKE_BUILD_TYPE=Release -DSDL_PTHREADS=ON -DSDL_TRAY=OFF
make -j2
```

### 安装

```bash
make install DESTDIR=$TEST_PREFIX
make install
```

### 验证

- G0 干净构建验证：PASS
- G1 二进制完整性：PASS
- G2 功能可用性：PASS
- G3 可移植性：PASS
- G4 档案完整性：PASS

### 知识沉淀

编译中学到的知识：
1. HarmonyOS 需要 cmake 检测 OHOS 平台
2. SDL3 需要定义 SDL_PLATFORM_OHOS 并取消 SDL_PLATFORM_LINUX
3. HarmonyOS pthread 实现不完整：禁用线程取消功能
4. HarmonyOS 无 Gtk 支持：禁用 SDL_TRAY---

**编译结束**: 2026-08-27 21:51
**最终状态**: built

---

## 第 2 次修复（2026-09-17，配合 sdl2-compat 2.32.68 适配）

### 问题 1：包类型静态 → sdl2-compat 运行期无法加载 SDL3

- **现象**：sdl2-compat 2.32.68 test_package 运行时
  `Failed loading SDL3 library.` 后 abort (signal 6)。
- **根因**：sdl2-compat 是 SDL2 兼容层，构建期只用 SDL3 头文件，
  运行期 `dlopen("libSDL3.so.0")`（sdl2_compat.c 的 LoadSDL3Library）。
  旧配方默认 `shared=False` 只产 libSDL3.a，包内没有 libSDL3.so.0。
- **修复**：配方改为 `package_type = "shared-library"`（移除 shared 选项），
  SDL_SHARED=ON / SDL_STATIC=OFF。

### 问题 2：共享库无 SONAME / 无 libSDL3.so.0 版本化文件

- **根因**：CMake 不识别 HarmonyOS 平台（UNIX=FALSE），
  ① `CMAKE_SHARED_LIBRARY_SONAME_C_FLAG` 为空 → SOVERSION 属性被忽略；
  ② SDL3 CMake 的 SONAME 分支 `elseif(UNIX AND NOT ANDROID)` 不命中。
- **修复**：
  1. 新增补丁 `0005-CMakeLists-soname.patch`：SONAME 分支改为
     `elseif((UNIX AND NOT ANDROID) OR OHOS)`（OHOS 变量由补丁 0001 设置）；
  2. 配方 generate() 注入
     `tc.cache_variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"`。
- **产物**：libSDL3.so.0.4.8（SONAME=libSDL3.so.0）+ libSDL3.so.0 + libSDL3.so。

### 验证（2026-09-17 本机实测）

```
conan create . --build=missing
  → test_package: SDL3 3.4.8 test: OK
  → 产物 libSDL3.so.0.4.8 (SONAME=libSDL3.so.0, NEEDED 仅 libc.so)
```

### 问题 3：CI worker 环境残留 fribidi.pc 导致 CMake 生成失败（2026-09-17 CI #49298）

- **现象**：CI-020 worker 上 `PkgConfig::PC_FRIBIDI includes non-existent
  path "/storage/Users/currentUser/usr/local/include/fribidi"` → generate 失败；
  同配方在 CI-033 与本机通过（无 fribidi.pc）。
- **根因**：补丁 0001 为启用 POSIX 路径（pthread/unix fs）设了 `UNIX_SYS=ON`，
  其副作用是 `dep_option(SDL_X11 ... ${UNIX_SYS} ...)` 默认 ON，而
  `dep_option(SDL_FRIBIDI ... ON SDL_X11 OFF)` 在 CheckX11() 探测之前求值
  （此时 SDL_X11 缓存仍为 ON）→ SDL_FRIBIDI 被缓存为 ON。worker 上存在
  残留的 fribidi.pc 时 CheckFribidi 创建带不存在 include 路径的
  IMPORTED_TARGET → 生成期报错。
- **修复**：配方显式关闭全部桌面 Linux 后端（X11/Wayland/KMSDRM/RPI/
  ROCKCHIP/FRIBIDI/LIBTHAI/ALSA/JACK/PIPEWIRE/PULSEAUDIO/SNDIO），
  鸿蒙上它们本就不可用，同时消除对 worker 本地 pkg-config 环境的敏感性。
- **验证**：本地重建后选项摘要确认全部 OFF，Video drivers: dummy offscreen、
  Audio drivers: disk dummy oss 不变，test_package 通过。

**编译结束**: 2026-09-17
**最终状态**: built

---

## 第 3 次更新（2026-09-20，上游测试集成 R51 + 依赖死锁解除）

### 背景

sdl2-compat 2.32.68 的适配依赖本包发布（拓扑序：sdl3 → sdl2-compat）。
本包 PR #6209 自 8-23 起处于 open 状态未合入，上游测试声明
（test_package/MANIFEST.yml）此前为占位形态（upstream_test_in_build: false、
仅 1 条申报），不满足 R51 上游测试三步法要求。本次补齐。

### 上游测试集成

- `SDL_TESTS=ON` 构建上游 test/ 目录（96 个测试程序全部编译，
  不安装进包：SDL_INSTALL_TESTS 默认 OFF）
- build() 内 `ctest --output-on-failure --timeout 180 -E '^testrwlock$'`
  运行 CTest 注册的非交互集（上游 TESTS_ENVIRONMENT 已注入 dummy 驱动）
- **结果：24/25 通过**（testautomation/testatomic/testthread/testsem/
  testtimer/torturethread/testfilesystem/testplatform 等全绿）
- **排除 1 个：testrwlock**——OHOS musl `pthread_rwlock` 无写者排队
  公平性（等待中的 writer 不阻塞新 reader），testrwlock 饱和读锁模式
  （6 readers 1000ms 持锁/10ms 间隙）下 writer 永久饥饿死锁。实测验证：
  裸 pthread_rwlock 探针单次写锁获取正常；`--nbthreads 1`（非饱和）通过。
  属 libc 公平性差异（glibc/macOS/Windows 均有写者救济），非 SDL 逻辑缺陷。
  SDL 自带 generic rwlock 的 rdlock 同样不等待排队 writer（仅 assert），
  换实现不能解决。完整论证见 test-report.md。

### test_package 加强

- `find_package(SDL3)` + `SDL3::SDL3`（官方配置名，package_info 设置
  cmake_file_name=SDL3/cmake_target_name=SDL3::SDL3，与上游 SDL3Config.cmake
  一致，下游 sdl2-compat 的上游 CMake 即用此形态）
- `can_run` 守卫 + SDL_VIDEODRIVER/SDL_AUDIODRIVER=dummy（无头 CI 安全）
- 验证：运行时 SDL_GetVersion() == 编译期 SDL_VERSION 头文件一致性 +
  SDL_InitSubSystem(EVENTS) 真实子系统初始化周期

### 验证（2026-09-20 本机实测）

- conan-verify 8 道门禁全部通过（G0-G4 + L2/L4/L5）
- W3 本地 CI 模拟（build_and_test.sh）通过
- W4 独立审计 pass（P0/P1 清零，P3 建议已修复：manifest 0003 guard 字段
  精确化、测试清单计数口径、未用 import 清理）

**编译结束**: 2026-09-20
**最终状态**: built
