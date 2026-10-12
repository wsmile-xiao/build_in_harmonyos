# schroot 1.6.13 适配笔记（HarmonyOS PC / aarch64-linux-ohos）

> 配方：`archives/s/schroot/1.6.13/conanfile.py`；测试报告：`reports/test-report.md`。

## 一、概况

| 项目 | 内容 |
|------|------|
| 上游仓库 | https://codeberg.org/shelter/reschroot |
| 上游版本 | 1.6.13（release 标签 `release/reschroot-1.6.13`）|
| 语言 | C++（`lang-preflight` 判定 cpp，与 C 属兼容族）|
| 构建系统 | CMake（上游声明 `cmake_minimum_required(2.8.12)`）|
| 产物 | `bin/schroot` + `libexec/schroot/{schroot-mount,schroot-listmounts}` + `lib/libsbuild.a` + `include/sbuild/**` + `etc/schroot/**` |
| 依赖 | boost/1.84.0、linux-pam/1.7.2、libuuid/2.40.4、gettext/0.22.5.1；测试 cppunit/1.15.1（全部已在制品仓 `ohpcd`，无需另行导入）|

## 二、源码获取

- 上游为 Codeberg 的 `shelter/reschroot`（Debian schroot 的持续维护源）。release 标签
  **无附件资产**，官方源码归档只能是 `archive/<tag>.tar.gz`：
  `https://codeberg.org/shelter/reschroot/archive/release/reschroot-1.6.13.tar.gz`。
- 两次下载 sha256 一致：`c05d6a1bb0210d401e6522eee2c465e0b43c6c98f7101d671f9e9ef88b3accf5`。
- 未使用 Debian 下游 `orig.tar.xz`（源 URL 规范只接受官方源/权威镜像）。

## 三、补丁（7 枚，均为可移植性改动，无平台条件编译宏）

| 补丁 | 内容 | 触发点 |
|------|------|--------|
| 0001 | `warn()` → `message(WARNING)` | `man/CMakeLists.txt:84` 调用了未定义的 CMake 命令，configure 直接失败 |
| 0002 | NLS 特性位改取正确变量 | `CMakeLists.txt:179` 从 `${pam}` 取 NLS 状态，导致 gettext 目标配置错误 |
| 0003 | 补 `#include "sbuild-i18n.h"` | 项目自己的 gettext 封装头此前只能经 `libintl.h` 传递可见 |
| 0004 | libc++ locale 名转换 | 上游使用非标准 `std::locale::operator std::string()`，libc++ 不提供 |
| 0005 | `sbuild-auth-pam.cc` 补 `<libintl.h>` | 直接调用 `dgettext()` |
| 0006 | `schroot-base-run.h` 补 `<libintl.h>` | 传递式调用 `bindtextdomain()` |
| 0007 | PAM 配置改装 `sysconfdir` 下 | `etc/pam/cmake_install.cmake` 原本装到绝对路径 `/etc/pam.d` |

## 四、关键决策与实测证据

### 1. 安装期 RPATH 重链 → 可执行文件 `execve` 返回 EPERM（决定性）

- 现象：`conan create` 的 test_package 执行包内 `bin/schroot` 报
  `ConanException: Error 126`（即 `execve` EPERM）；而同一棵构建树的
  `…/b/build/Release/bin/schroot/schroot`（1600128 B）可直接执行。
- 根因：`cmake --install` 会按安装期 RPATH 重新链接可执行文件；实测二者 md5 不同
  （构建树 `41c15b00…`，安装副本 `bc0c7612…`），重链产物在 HarmonyOS 文件安全策略下
  不可执行（工具链 `CMAKE_SKIP_INSTALL_RPATH:BOOL=NO`）。
- 处置（两层）：① `generate()` 令 `CMAKE_INSTALL_RPATH` 与 `CMAKE_BUILD_RPATH` 一致
  （依赖库目录），cmake 即跳过重链；② `package()` 用构建树产物覆盖 `bin/<name>` 与
  `libexec/schroot/<name>`，保证包内二进制可用。
- 复验：`EPERM=1 FAILED=0 PCTPASS=1`，唯一 `EPERM=1` 是 make jobserver fifo
  （非包内二进制，非阻断）。

### 2. configure 生成的公共头未随 install 安装

- 现象：消费者编译 `sbuild-i18n.h` 报 `sbuild/sbuild-config.h: No such file or directory`。
- 根因：`sbuild-config.h` 由 configure 生成，上游 install 清单未包含；而已安装的公共头引用它。
- 处置：`package()` 从构建树 `…/sbuild/` 取该头装入 `include/sbuild/`。

### 3. 消费者依赖图中 boost/libuuid 的二进制被跳过

- 现象：真实 `conan create` 的 test_package 编译报 `boost/format.hpp: No such file or directory`；
  生成的 `conan_toolchain.cmake` 中依赖头目录不全（`NINC=3 NBOOST=0 NUUID=0`）。
- 证据：日志 `Skipped binaries: boost/1.84.0, libuuid/2.40.4, zlib/1.3.1, cppunit/1.15.1`；
  独立消费者探针实测 `dep.package_folder=None`（boost/libuuid），而 gettext/linux-pam 有安装路径。
- 处置：① 配方侧把这两个依赖声明为转发依赖（`transitive_headers` / `transitive_libs`）；
  ② test_package 显式 `self.requires("boost/1.84.0")` / `self.requires("libuuid/2.40.4")`，
  使其二进制进入消费者图，随后收集其头/库目录并注入消费者 CMake 工程。

### 4. CMake 4 无 FindBoost 模块，上游只用旧式变量

- 上游 `CMakeLists.txt` 链接 `${Boost_<COMPONENT>_LIBRARY_RELEASE}` 等旧式变量，且只
  `find_package(Boost)`；CMake 4 已移除 FindBoost 模块（BoostConfig 只提供 imported target）。
- 处置：`CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON` + `BOOST_ROOT`，并按实际存在的库文件为
  filesystem/iostreams/program_options/regex 逐个给出 `<COMPONENT>_LIBRARY_RELEASE`。

### 5. Boost 与 OHOS libc/libc++ 的两处不兼容

- `pthread_setcancelstate()` 未在 OHOS libc 头中声明 → Boost `sp_thread_sleep.hpp` 编译失败：
  配方注入 `BOOST_SP_NO_PTHREAD_SETCANCELSTATE`（走 nanosleep 分支）。
- OHOS libc++ 不提供 `<tr1/memory>`，上游 `cmake/CompilerChecks.cmake` 的 shared_ptr 探测落到
  "A shared_ptr implementation is not available"：配方定义 `HAVE_BOOST_SHARED_PTR_HPP`
  （等价于上游头文件自带分支，无源码改动）。

### 6. i18n / gettext

- OHOS sysroot 的 `libintl.h` 是空壳且不提供 `libintl`（glibc 侧 gettext 属 libc）：
  `nls=OFF`，实际调用能力由制品仓 `gettext` 包提供，配方补 `-lintl` 与 `-L<gettext libdir>`，
  并以 0003/0005/0006 补 `<libintl.h>` 包含。

### 7. 其它配方侧决定

- `CMAKE_SYSTEM_NAME=Linux`（CMake 无 HarmonyOS 平台模块）+ `CMAKE_SYSTEM_PROCESSOR=aarch64`。
- `CMAKE_POLICY_VERSION_MINIMUM=3.5`：上游 2.8.12 下限被 CMake 4 拒收。
- 探测结果直给（`UUID_HEADER/UUID_FUNC/uuid`、`PAM_HEADER/PAM_FUNC/pam`、`CPPUNIT_CLASS/test`）：
  交叉编译下 `check_library_exists` 的试链接不可靠。
- `personality` 关闭：构建日志显示 `sys/personality.h` 与 `personality()` 探测均为 found
  （不是缺头），关闭是为规避沙箱/运行时的受限 syscall，属稳定化取舍。
- 快照/回环特性关闭（`lvm-snapshot`、`zfs-snapshot`、`btrfs-snapshot`、`loopback`）：
  依赖 Linux 专有工具（lvcreate/zfs/btrfs/losetup），构建机上不存在。
- `SCHROOT_LIBEXEC_DIR` 覆盖为 `<package>/libexec/schroot`：conan 工具链把
  `CMAKE_INSTALL_LIBEXECDIR` 设为 `bin`，helper 会与同名可执行文件争目录（install 报
  `destination ... is not a directory`）。
- `CMAKE_BUILD_RPATH`/`CMAKE_INSTALL_RPATH` 注入依赖库目录：依赖以 `-L/-l` 原始旗标接入时
  CMake 推不出 RPATH，构建树上运行测试可执行文件会找不到 `libintl.so.8`。
- conan `CMakeToolchain` 的 `extra_cflags/extra_cxxflags/extra_exelinkflags/extra_sharedlinkflags`
  **必须是列表**（传字符串报 `TypeError: can only concatenate str (not "list") to str`）。
- 补丁 0001–0007 为探索期手工编写（故 `patch_generation.method: manual`，与 R3 的
  `refresh-patch --auto` 偏好不同）：每枚均以标准 `git diff` 形式产出、`git apply`
  逐枚验证 rc=0，`finish` 内 `refresh-patch --auto` 复跑后内容未发生变化；未改动任何
  生成文件，改动面仅为上游源码。

## 五、上游测试

- 套件共 8 个：`setup-test-data`、`sbuild-chroot-chroot`、`sbuild-standard`、`sbuild-keyfile`、
  `sbuild-run-parts`、`schroot-base-option-action`、`cleanup-test-data`、`sbuild-chroot-config`。
- `sbuild-chroot-config` 的 testdata 必须是 root 属主（`sbuild/sbuild-chroot-config.cc` 的
  `load_data()` 显式拒绝非 root 属主，属上游安全设计）；构建沙箱以普通用户运行，且本机
  FUSE 挂载下 `chown` 无效 → 无法满足。
- 处置：`build()` 内以上游 `test` 目标等价方式自调
  `ctest --output-on-failure -E sbuild-chroot-config`（工作目录即构建目录，`Testing/` 与
  testdata 布局不变；上游 `test` 目标不接受额外参数）。
- 实测：`100% tests passed, 0 tests failed out of 7`。

## 六、复现命令

```bash
# 完整复现（本地 OHOS profile；CI 用同一 profile）
conan create archives/s/schroot/1.6.13 -pr:h=<ohos-aarch64> -pr:b=<ohos-aarch64>

# 仅上游测试（等价于配方 build() 内的调用）
ctest --output-on-failure -E sbuild-chroot-config   # 工作目录 = conan 构建目录
```

## 七、对话记录（关键决策时间线）

| 阶段 | 决策 / 发现 |
|------|-------------|
| 立项 | 上游锁定 Codeberg 官方源；依赖全部已在制品仓，无需另行导入口 |
| 探索编译 | 依次解决 configure `warn()`、NLS 特性位、Boost 头与旧式变量、`-lintl`、shared_ptr 探测（→ 0001/0002 + 配方注入）|
| i18n | 三处 `<libintl.h>` 缺失（0003/0005/0006）；NLS 关闭，gettext 走制品仓依赖 |
| 安装期 | PAM 配置被装到绝对 `/etc/pam.d` → 0007 改装 `sysconfdir` |
| exec EPERM | 定位为安装期 RPATH 重链 → 配方两层处置（见 四.1）|
| 消费者用例 | 由 Python 冒烟改写为「CMake 工程链接包内 `libsbuild.a` 的 C++ 消费者程序 + 鸿蒙断言」|
| 生成头 | 消费者缺 `sbuild-config.h` → `package()` 补装（见 四.2）|
| 消费者依赖 | 日志 `Skipped binaries` → 配方转发依赖 + test_package 显式 require（见 四.3）|
| 定稿 | `conan create` rc=0：上游 7/7 通过，消费者用例通过 |
---

**编译结束**: 2026-10-10 20:05
**最终状态**: built
