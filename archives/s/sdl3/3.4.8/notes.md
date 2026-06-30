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
4. HarmonyOS 无 Gtk 支持：禁用 SDL_TRAY

---

**编译结束**: 2026-05-20 15:30:00
**最终状态**: built