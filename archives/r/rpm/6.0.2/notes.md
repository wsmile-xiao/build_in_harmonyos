# rpm 6.0.2 适配笔记

## 背景

RPM Package Manager 6.0.2，CMake 构建系统，适配 HarmonyOS PC (aarch64)。

## 修复记录

### 2026-09-09: 声明 zlib/bzip2 为 Conan 依赖

**问题**: conanfile.py 的 requirements() 缺少 zlib 和 bzip2 的 Conan 依赖声明，CMake find_package(ZLIB REQUIRED) 在 CI clean 环境找不到系统库。

**修复**:
- 新增 zlib/1.3.1.1（带 -fPIC，支持链入共享库）和 bzip2/1.0.8 为 Conan 依赖
- CMAKE_PREFIX_PATH 优先 Conan 包路径，确保 CI 环境可找到
- manifest.yaml 同步修正依赖列表和 configure_options

**验证**: conan create + CI 全流水线 (L0-L5) 100% pass

## 编译参数

- BUILD_SHARED_LIBS=ON
- ENABLE_PYTHON=OFF, ENABLE_NLS=OFF, ENABLE_OPENMP=OFF
- WITH_CAP=OFF, WITH_ACL=OFF, WITH_SELINUX=OFF, WITH_DBUS=OFF
- WITH_AUDIT=OFF, WITH_FAPOLICYD=OFF, WITH_SEQUOIA=OFF
- WITH_OPENSSL=ON, WITH_BZIP2=ON, WITH_ZSTD=ON, WITH_LIBLZMA=ON
- WITH_READLINE=OFF, WITH_ICONV=OFF, WITH_LIBDW=OFF, WITH_LIBELF=OFF
- WITH_LIBARCHIVE=ON (optional, patch makes it non-REQUIRED)

## 最终状态

status: closed
COMPLETED
