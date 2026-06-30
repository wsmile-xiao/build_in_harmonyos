# 适配笔记： libilbc 3.0.4

# 遵循 ARCHIVE-SPEC v2.0

格式

# 最后更新: 2026-06-11

# 保留此头以便 finish 清理旧记录

# 不要修改本文件中编译结束块以上的内容

# ============================================================

# 编译开始
#
# **软件**: libilbc
# **版本**: 3.0.4
# **状态**: 编译成功 (built)
# **日期**: 2026-06-11
# ============================================================

# 源码信息
#
- URL: https://github.com/TimothyGu/libilbc/releases/download/v3.0.4/libilbc-3.0.4.tar.gz
- SHA256: 6820081a5fc58f86c119890f62cac53f957adb40d580761947a0871cea5e728f
- 构建系统: cmake
- 许可证: BSD-3-Clause

- 无依赖

# ============================================================ # 平台适配问题
#
## 问题1: LAST_SYSTEM_ERROR 未定义 (编译失败)
#
- **现象**: `rtc_base/checks.cc` 编译报错 `use of undeclared identifier 'LAST_SYSTEM_ERROR'`
- **根因**: CMake 将 HarmonyOS 识别为 `CMAKE_SYSTEM_NAME=HarmonyOS`（非UNIX），导致 `WEBRTC_POSIX` 和 `WEBRTC_LINUX` 编译宏未定义。 `LAST_SYSTEM_ERROR` 依赖 `WEBRTC_POSIX` 才有定义（`#define LAST_SYSTEM_ERROR (errno)`）
- **影响**: 所有使用 WebRTC 代码的 cmake 项目在 HarmonyOS 上都会遇到此问题
- **修复**: 修改 CMakeLists.txt,平台检测条件中加入 `CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS"`：
  ```cmake
  if(UNIX OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")
      add_compile_definitions(WEBRTC_POSIX)
  endif()
  if(APPLE)
      add_compile_definitions(WEBRTC_MAC)
  elseif(UNIX OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")
      add_compile_definitions(WEBRTC_LINUX)
  endif()
  ```
- **分类**: L1（平台真理） — 所有使用 WebRTC 代码的 cmake 项目在 HarmonyOS 上都受影响
- **补丁**: 0001-CMakeLists.txt.patch

# ============================================================ # 编译步骤
#
1. init-build: `python3 $SKILL_ROOT/scripts/ohc-run.py init-build libilbc 3.0.4 --url=...`
   - SSL 证书下载失败 → 手动 curl 下载 → 手动解压 → 用 --no-download 继续
2. 读取 build context: `.build-context-libilbc-3.0.4`
3. cmake 配置: `cd $BUILD_SRC_DIR && mkdir build && cd build && cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DBUILD_SHARED_LIBS=ON ..`
4. make 编译: `cd build && make -j2` ✅ (首次编译失败， LAST_SYSTEM_ERROR)
修复 CMakeLists.txt → 再次配置 → 编译成功)
5. make install DESTDIR: `cd build && make install DESTDIR=$TEST_PREFIX` ✅
8个文件)
6. 功能测试: ilbc_test 20/30 sample.pcm → ✅ (163/108 blocks)
 ilbc_test2 30 sample.pcm → ✅ (108 blocks)
 Done with simulation
7. 安全弹窗(R7): `make install` → $DEFAULT_PREFIX/bin/ilbc_test 运行正常 ✅
8. pkg-config: libilbc.pc 版本 3.0.4 ✅
# ============================================================ # 编译配置
#
| 参数 | 值 |
|------|------|
| CMAKE_INSTALL_PREFIX | $DEFAULT_PREFIX |
| BUILD_SHARED_LIBS | ON |
| CC | clang 15.0.4 |
| CXX | clang++ 15.0.4 |
| CFLAGS | -fPIC -O2 (内置) |
| 平台 | HarmonyOS aarch64 |

# ============================================================ # 产物清单
#
| 路径 | 类型 | 大小 |
|------|------|------|
| bin/ilbc_test | ELF可执行 | 178,688 bytes |
| lib/libilbc.so | ELF共享库 | 125,376 bytes |
| lib/pkgconfig/libilbc.pc | pkg-config | 239 bytes |
| include/ilbc.h | 头文件 | 15,203 bytes |
| include/ilbc_export.h | 头文件 | 1,029 bytes |
| share/doc/libilbc/CONTRIBUTING.md | 文档 | 2,216 bytes |
| share/doc/libilbc/NEWS.md | 文档 | 4,774 bytes |
| share/doc/libilbc/README.md | 文档 | 5,253 bytes |
# ============================================================ # 编译结束
#
**最终状态**: built ✅
 **编译器**: clang 15.0.4 / clang++ 15.0.4
 **配置参数**: cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DBUILD_SHARED_LIBS=ON
 **构建系统**: cmake
 **补丁**: 0001-CMakeLists.txt.patch (HarmonyOS平台检测)
 **测试**: ilbc_test(ilbc_test2) 功能测试通过
 **依赖**: libc++_shared.so (C++运行时)
---

**编译结束**: 2026-06-11 14:56
**最终状态**: built
