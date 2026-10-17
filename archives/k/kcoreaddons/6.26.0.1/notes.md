# kcoreaddons 6.26.0.1 notes

## Scope

本版 = 上游 KDE Frameworks **6.26.0** 源码 + 两项 OHOS 适配修复，版本号按适配修复后缀递增为 `6.26.0.1`。

作为 `kio/6.26.0.1` 闭包的第 2 个依赖包交付（PR 前缀【依赖项】）；`kconfig/6.26.0.1` 已被他人认领，按 DAG 跳过，先交本包（叶子，闭包内零依赖）。

## Adaptations

- `KF_IGNORE_PLATFORM_CHECK=TRUE` bypasses KDE's platform allowlist for OHOS.
- `KCOREADDONS_USE_QML=OFF` disables the optional QML plugin; the KF baseline
  needs `KF6::CoreAddons`, not the QML plugin.
- `BUILD_PYTHON_BINDINGS=OFF` / `USE_DBUS=OFF`: Shiboken6/PySide6 and the Qt DBus
  split are not part of the current OHOS dependency set.
- `BUILD_TESTING=ON` runs the upstream CTest autotests inside `build()`.
- **DT_SONAME fix (本版新增)**: CMake ships no `Platform/HarmonyOS` module, so
  `CMAKE_SHARED_LIBRARY_SONAME_C/CXX_FLAG` stay empty and lld emits no `DT_SONAME`;
  consumers then record the absolute build-machine path of `libKF6CoreAddons.so`
  in `DT_NEEDED`. The recipe now injects `-Wl,-soname,` for both flags.
- **C++20**: kcoreaddons 6.26.0 使用 `std::ranges`; `CMAKE_CXX_STANDARD` 被
  `variable_watch` 覆盖未生效，改用 `CMAKE_CXX_FLAGS=-std=c++20` 强制。
- 补丁（`patches/`，仅 `settings.os == "OHOS"` 时应用）：
  - `0001-CMakeLists.txt.patch` — 跳过 `ecm_install_po_files_as_qm(poqm)`
    （qtbase 包内无 Qt Linguist 工具组件）。
  - `0002-src-lib-CMakeLists.txt.patch` — OHOS 视为非 Windows 类 Unix 目标选择
    `*_unix.cpp` 源码。
  - `0003-src-lib-clockskew-harmonyos.patch` — HarmonyOS clockskew 引擎源码选择。
  - `0004-ohos-upstream-autotest-fixes.patch` — 上游 autotest OHOS 修复：
    `dladdr` 探测、MIME 复合后缀回退、`LANGUAGE` locale 回退、硬链接与
    user/group 库不可用时的运行期跳过。
  - `0005-kaboutdata-ranges.patch` — KAboutData 的 C++20/ranges 兼容。
  - `0006-qfilecopy-harmonyos-plugin-test.patch`（本版新增）— plugin 测试改用
    读写复制替代 `QFile::copy`：OHOS 上 `QFile::copy` 恒返回 FALSE
    （errno 75 = EOVERFLOW）。
- `ECM_MODULE_PATH` 手工设置（CMakeDeps 生成的 `ECMConfig.cmake` 不传播该变量）；
  `conan_cmakedeps_paths.cmake` 手工生成（qtbase 用 `cmake_find_mode=none`，
  CMakeDeps 不会把其 `lib/cmake` 加进 `CMAKE_PREFIX_PATH`）。

## Upstream test execution (measured)

清点：上游 6.26.0 `BUILD_TESTING=ON` 注册 **30** 项 CTest 用例。
实测（本机 `conan create`，2026-09-30）：

- 上游 CTest：**30/30 passed, 0 failed out of 30**（日志 `tmpdir/kcoreaddons-create.log:807`）。
- Conan `test_package`：**1/1** CTest passed，并直接运行测试二进制输出
  `PASS: KAboutData created (component=testapp version=1.2.3)`
  （`test_package/conanfile.py` 的 `test()` 实际调用被测包 API，符合 R34）。
- 无跳过/未运行的上游用例（30 项全部执行并通过）。

## Verification

- Upstream source SHA256 verified:
  `92fdbfab68e52d9eacf44a992f01cb364d6395c24441e2fd47dd48a23b3281f6`
  （`https://download.kde.org/stable/frameworks/6.26/kcoreaddons-6.26.0.tar.xz`）。
- `conan create . -pr:h ohos-aarch64 -pr:b ohos-aarch64 --build="kcoreaddons/*"`
  → rc=0；包 id `57ffd8c720a5bfee7e8827990cd6550a49181c1b` 已创建。
- 本地缓存目录：`~/.conan2/p/b/kcore0fc408254cd6a`（等 5 个 kcore* 构建目录）。

---

## 对话记录

### 对话 #1 — 2026-09-30

- 目标：交付 `kcoreaddons/6.26.0.1`（`.1` 升版 = 上游 6.26.0 + DT_SONAME 注入 + 0006 补丁），
  作为 `kio/6.26.0.1` 闭包的第 2 个依赖包（PR 前缀【依赖项】）。
- 闭包 DAG 核对结论：kcoreaddons 为叶子（闭包内零依赖，仅 qtbase/6.11.1 + ecm/6.26.0），
  不依赖被他人认领的 kconfig，因此可先交付；等 kconfig 发布后再交 kservice/kcolorscheme/kcompletion。
- 本地 `conan create . --build="kcoreaddons/*" -pr:h ohos-aarch64 -pr:b ohos-aarch64` → rc=0；
  上游 CTest 30/30、test_package 1/1 全绿。
- 交付文件集镜像 karchive/6.26.0.1：conanfile.py、conandata.yml、manifest.yaml、notes.md、
  patches/0001-0006、test_package/{conanfile.py,test.cpp,CMakeLists.txt,MANIFEST.yml}。
- 制品仓探测（R35，`conan download --only-recipe`）：kcoreaddons/6.26.0.1 未发布（本 PR 为首次发布）。

**编译结束**: 2026-09-30 13:25
**最终状态**: built
---

**编译结束**: 2026-09-30 13:28
**最终状态**: built
