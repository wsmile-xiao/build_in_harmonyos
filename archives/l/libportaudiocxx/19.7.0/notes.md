# libportaudiocxx 19.7.0 适配笔记

## 编译环境
- 构建系统: autotools（bindings/cpp 子目录，VPATH 构建）
- 编译日期: 2026-09-14
- 编译器: clang/clang++（OHOS aarch64 交叉目标；本机 macOS 仅做 configure/编译验证）
- 状态: built（OHOS 二进制由远端 shadow CI/门禁验证）

## 上游判定（关键决策）

libportaudiocxx 无独立上游源码树：
- waterlan 独立项目（waterlan.home.xs4all.nl/libportaudiocxx）已 404 失效；
- Alpine/Debian/Fedora 的 libportaudiocxx 发行包（Origin: PortAudio）全部来自
  **PortAudio 官方 tarball `pa_stable_v190700_20210406.tgz` 内的 `bindings/cpp/`**（
  PortAudioCpp 12，作者 Ludwig Schwardt / Mikael Magnusson）；
- 结论：上游 = PortAudio 官方 tarball，只构建 bindings/cpp 子目录，包名
  libportaudiocxx，版本 19.7.0，依赖已发布的 portaudio/19.7.0。

## 编译步骤

```bash
# 1. source: 完整 PortAudio tarball（strip_root）
# 2. 在 bindings/cpp 子目录 VPATH 配置（conan build_folder 内运行）：
#    <src>/bindings/cpp/configure --disable-shared --enable-static \
#      --build=aarch64-linux-ohos --host=aarch64-linux-ohos --prefix=/
# 3. make -j1
# 4. make install DESTDIR=$package_folder
```

OHOS 设备上 configure 通过 `/system/bin/sh <src>/bindings/cpp/configure`
显式调用（HMDFS shebang 限制），参数串保留 Conan 生成的完整 configure_args。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | bindings/cpp 顶层 configure 引用 `$srcdir/../..` 的 config.sub/install-sh/ltmain.sh | 设计为在 PortAudio 源码树内构建 | source 保留完整 tarball；构建定位到 bindings/cpp 子目录（VPATH），aux 文件自然从源码树根解析 |
| 2 | `libportaudiocpp_la_LIBADD` 指向 `$(top_builddir)/$(PORTAUDIO_ROOT)/lib/libportaudio.la` | 独立打包时源码树内无此库（C 库由 conan 依赖提供） | 0003 补丁：LIBADD 与 automake 自动生成的 DEPENDENCIES 改为 `-lportaudio`，由 conan 依赖提供 |
| 3 | make 尝试构建 bin 子目录 devs/sine（noinst 示例，依赖源码树内 portaudio） | 顶层 SUBDIRS 含 bin | 0001 补丁：SUBDIRS = lib include |
| 4 | config.status 临时目录 `mktemp -d "./confXXXXXX"` 在 HMDFS 上权限失败 | umask 077 创建 700 目录，HMDFS 拒绝 | 0002 补丁：umask 077→022（同 portaudio 0002） |
| 5 | config.sub 无法识别 aarch64-linux-ohos | 上游 config.sub 无 OHOS 支持 | 0004 补丁：maybe_os 分支 + `-linux-ohos*` 识别段（同 portaudio 0001） |
| 6 | 本机 autoreconf -fi 失败（AC_LIBTOOL_WIN32_DLL 未定义） | 本机无 libtoolize、autoconf 2.73 与包要求 2.69 不兼容 | 不重新生成 configure；补丁打在生成文件层（configure/Makefile.in/config.sub），PR 说明 |
| 7 | configure 直接执行被 HMDFS 拒绝 | HMDFS 禁止 shebang 脚本直接执行 | OHOS 分支用 `/system/bin/sh <configure>` 显式调用（同 portaudio） |
| 8 | macOS 上 refresh-patch 清理 .patch-staging 报 Resource deadlock avoided | macOS APFS 目录句柄死锁（已知现象） | 目录改名绕开（git 已忽略 .patch-staging / .patch-backup-*）；补丁文件不受影响 |

## 源码修改

补丁清单（均经 `ohc-run.py refresh-patch --auto` 生成）：

| 补丁 | 文件 | 修改 |
|------|------|------|
| 0001 | bindings/cpp/Makefile.in | SUBDIRS = lib include（去掉 bin 示例） |
| 0002 | bindings/cpp/configure | umask 077→022（HMDFS 临时目录） |
| 0003 | bindings/cpp/lib/Makefile.in | LIBADD/DEPENDENCIES → `-lportaudio`（链接 conan 依赖） |
| 0004 | config.sub（源码树根） | 识别 aarch64-linux-ohos / x86_64-linux-ohos |

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| portaudio | 19.7.0 | 已发布 ohpcd（recipe rev 0cfb1dcf84c1b5107923e574eb3cd741），含 OHOS armv8 binary；R36 先发布后构建 |

## 验证结果

```bash
# 本机（无 OHOS 工具链，验证到编译层）：
# 1. 4 个补丁在纯净 tarball 上 git apply 全部成功
# 2. VPATH configure --host=aarch64-linux-ohos 成功，生成全部 Makefile/portaudiocpp.pc
# 3. make 编译：16 个 .cxx 全部编译通过（0 error）
# 4. 生成的 lib/Makefile：LIBADD=-lportaudio、DEPENDENCIES=空、SUBDIRS=lib include ✓
# 5. portaudiocpp.pc：Requires: portaudio-2.0（与 portaudio 包 pkg_config_name 匹配）✓

# 远端（OHOS shadow CI/门禁）：conan test_package + 签名 + L0/L1/L4/L5 门禁
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | OHOS 适配配方（Autotools + /system/bin/sh + 签名） |
| conandata.yml | 官方源 + sha256 + 4 补丁声明 |
| patches/0001-0004 | 4 个补丁（git apply 验证通过） |
| test_package/ | C++ 消费者测试（生命周期/版本/枚举/迭代器/异常路径/sizeOfSample，6 断言；OHOS 另有 1 项平台特有断言）+ OHOS 签名 |
| reports/ | W0 / shadow-ci / upstream-test-inventory |
| manifest.yaml / notes.md | 本文件 |

## 注意事项

- `test_package` 使用 C++（.cxx），非模板的 test.c；CMake 项目语言设为 CXX。
- 包内库名为 `libportaudiocpp`（安装后 `lib/libportaudiocpp.a`），
  `cpp_info.libs = ["portaudiocpp"]`、`pkg_config_name = "portaudiocpp"`、
  cmake 名 `PortAudioCpp`。
- 头文件安装到 `include/portaudiocpp/*.hxx`（19 个），pc 文件
  `lib/pkgconfig/portaudiocpp.pc`。
- 静态库默认（shared=False），OHOS 下无需对 .a 签名；shared 分支保留
  `.so` 签名逻辑（同 portaudio）。
- 纯库包：无 `bin/` 产物，不需要 commands.json（R38）。
---

**编译结束**: 2026-09-15 00:07
**最终状态**: built
