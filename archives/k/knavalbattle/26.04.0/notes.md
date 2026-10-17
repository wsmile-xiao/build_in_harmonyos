# knavalbattle 26.04.0 适配笔记

## 编译环境
- 构建系统: cmake（CMake + KF6/Qt6 Widgets + libkdegames KDEGames6，**.build-context 里 autotools 是 init_build 误判**）
- 编译日期: 2026-09-18
- 编译器: clang/clang++（OHOS arm64 工具链，ci/conan/profiles/ohos-aarch64）
- 状态: published

## 编译步骤

KDE Gear 26.04.0 release-service tarball 以 Conan 配方驱动（模式 B 探索 + conan-init 固化），实际执行：

```bash
# 1) 探索编译（源码 /storage/Users/currentUser/builds/knavalbattle-26.04.0.work）
#    CMake + KF6/Qt6，非 autotools

# 2) 生成并验证配方（conan-verify 8 门禁全过）
python3 scripts/ohc-run.py conan-verify knavalbattle 26.04.0

# 3) 收尾（W3 本地 CI + .ci-result.json）
python3 scripts/ohc-run.py finish knavalbattle 26.04.0 published

# 实际 conan create 命令（finish step [5/10] 与 W3 内部执行）
conan create archives/k/knavalbattle/26.04.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
```

关键 cmake 变量（conanfile.py generate() 写入 CMakeToolchain）：

| 变量 | 值 | 目的 |
|------|----|------|
| `CMAKE_BUILD_TYPE` | `Release` | profile 驱动 |
| `KF_IGNORE_PLATFORM_CHECK` | `TRUE` | OHOS 不在 KDE 平台列表，跳过平台检测 |
| `KF_SKIP_PO_PROCESSING` | `ON` | 跳过 .po→.qm 翻译目录生成（无需 LinguistTools/gettext） |
| `BUILD_TESTING` | `OFF` | 上游无测试（R51，见下） |
| `BUILD_SHARED_LIBS` | `ON` | 非系统同名库，动态链接由 Conan 管理 |
| `CMAKE_INSTALL_LIBDIR` | `lib` | 安装布局 |
| `CMAKE_BUILD_RPATH` | `$ORIGIN` | 运行时相对解析 |
| `CMAKE_EXE_LINKER_FLAGS` | `-Wl,--disable-new-dtags` | 避免绝对 RUNPATH 进产物 |
| `ECM_MODULE_PATH` | `<ecm>/share/ECM/{modules,find-modules,kde-modules}` | 手动注入 ECM 模块（见问题表） |

另：generate() 手写 `conan_cmakedeps_paths.cmake`（CMakeFIND_PACKAGE_PREFER_CONFIG ON + 逐依赖 prepend CMAKE_PREFIX_PATH/CMAKE_MODULE_PATH/CMAKE_LIBRARY_PATH/CMAKE_INCLUDE_PATH），因 KF6/qtbase 包 `cmake_find_mode=none`，CMakeDeps 不会把它们的 lib/cmake 加进 CMAKE_PREFIX_PATH。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | kdbusaddons/6.29.0 依赖冲突 | 6.29.0 需 Qt6DBus 组件（仅 qtbase/6.11.1.1 变体携带），与 libkdegames 闭包的 qtbase/6.11.1 冲突且不能共存 | 改用 kdbusaddons/6.14.0（构建于 qtbase-sql-dbus/6.11.1），并在配方直接 `requires("qtbase-sql-dbus/6.11.1")` 补齐 Qt6DBus 组件 |
| 2 | kdoctools/DocBook 工具链缺失且 kdoctools 破坏 KF6 单版本 | OHOS 基线无 meinproc6/DocBook XSL；kdoctools/6.19.0 构建于 karchive/6.19.0，与 libkdegames 的 karchive/6.18.0 override 冲突 | patches/0001 从 `find_package(KF6 COMPONENTS ...)` 移除 KF6DocTools 并注释 `kdoctools_install(po)`；patches/0002 跳过 doc/ 的 `kdoctools_create_handbook`。手册不影响游戏二进制 |
| 3 | KF6 双版本冲突 | libkdegames/26.04.0 将多个 KF6 组件钉在 6.18.0 线，ktextwidgets/6.14.0 又 requires 6.14.0 线组件 | 下游 conanfile 对 karchive/kcompletion/kconfig/ki18n/kwidgetsaddons 用 `override=True` 强制 6.18.0；kcrash/kdbusaddons/ktextwidgets/kdnssd 用各自已发布版本（KF6 ABI 同 major 兼容，二进制可干净链接） |
| 4 | CMake 不认识 OHOS（E092） | CMake 无 HarmonyOS platform module | `KF_IGNORE_PLATFORM_CHECK=TRUE` 绕过 KDE 平台检测（conan-verify G0 已知风险 E092 已处理） |
| 5 | ECM_MODULE_PATH 未传播 | CMakeDeps 生成的 ECMConfig 不设置项目 CMakeLists 依赖的变量 | generate() 从 `ecm.package_folder/share/ECM` 手动构造并注入 `ECM_MODULE_PATH`，另写 `conan_cmakedeps_paths.cmake` 逐依赖 prepend 查找路径 |
| 6 | test_package 中 openal-soft 缺失导致二进制无法启动 | openal-soft 是 libkdegames 的传递运行时依赖（libKDEGames6.so 带 `DT_NEEDED libopenal.so.1`），其配方默认 `shared=False`，Conan 将其当静态库从测试图剔除（package_folder=None） | test_package/conanfile.py 直接 `requires("openal-soft/1.25.2")`，把 libopenal 加回 LD_LIBRARY_PATH（R34 真实执行 `bin/knavalbattle --version` 验证） |
| 7 | OHOS ELF 必须签名 | 未签名的 ELF 在设备上不可执行 | package() 用 `llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign -selfSign 1` 对包内全部 ELF 签名 |
| 8 | 依赖库携带绝对/相对 DT_NEEDED | KF6/KDEGames6 产物带构建机绝对 conan 缓存路径与 `../../bin/` 相对条目 | test_package 从全新 scratch CWD 运行，`../../bin` 指向依赖 so link farm，并物化缺失的绝对 DT_NEEDED（alligator 26.04.0 / E537 先例） |

## 源码修改

| 补丁 | 修改内容 |
|------|---------|
| `patches/0001-CMakeLists.txt.patch` | `find_package(KF6 COMPONENTS ...)` 移除 `DocTools`；注释 `kdoctools_install(po)`（无 meinproc/DocBook 工具链） |
| `patches/0002-doc-CMakeLists.txt.patch` | 跳过 `kdoctools_create_handbook` 手册生成（游戏二进制不需要手册） |

## 依赖版本

最终 requirements 版本清单（全部制品仓在仓版本）：

```
qtbase/6.11.1
qtbase-sql-dbus/6.11.1
karchive/6.18.0
kcompletion/6.18.0
kconfig/6.18.0
kcoreaddons/6.18.0
kcrash/6.18.0
kdbusaddons/6.14.0
kdnssd/6.29.0
ki18n/6.18.0
ktextwidgets/6.14.0
kwidgetsaddons/6.18.0
kxmlgui/6.18.0
libkdegames/26.04.0
ecm/6.26.0        # tool_requires（build 期）
```

## 验证结果

```bash
conan create archives/k/knavalbattle/26.04.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
# → exit 0（34/34 依赖已安装，test_package 真实执行）
#   knavalbattle 2.1.26040   ← bin/knavalbattle --version 输出，退出码 0

conan-verify: 8 门禁全 PASS（G0/G1/G2/G3/G4 + L2/L4/L5）
finish: W3 本地 CI（setup.sh + build_and_test.sh）PASS → .ci-result.json exit_code=0
```

### R51 上游测试清点证据

源码树 `/storage/Users/currentUser/builds/knavalbattle-26.04.0.work` 全树 grep 验证，上游**无任何测试**：

```
$ find . -type d \( -name tests -o -name test \) | wc -l
0
$ grep -rIn -e "enable_testing" -e "add_test" -e "ECMAddTests" -e "BUILD_TESTING" \
    --include="CMakeLists.txt" --include="*.cmake" . | wc -l
0
$ grep -rIl -e "ctest" -e "qtest" . | wc -l
0   # 唯一命中 snapcraft.yaml 第 50 行 "BUILD_TESTING=OFF" 是 snap 打包配置，非测试注册
```

- 无 `tests/`/`test/` 目录、无 `add_test`/`enable_testing`/`ctest`/`qtest`/`ECMAddTests` 注册。
- 因此不设置 upstream_check_command（test_package/MANIFEST.yml 已写明），无需 ctest 可运行。
- 适配验证靠 test_package（R34）：真实执行打包二进制 `bin/knavalbattle --version` → `knavalbattle 2.1.26040` 退出码 0。

## 注意事项

- **JC 假阳性说明（W3 第一次失败根因）**：本地 W3 的 junk_check 在 full 模式（整仓 74306 文件）下命中了他人目录 `archives/c/cloog/0.21.1/` 中已被提交的 `.build-closed`/`.staging-verified`（commit 906cc59ae7，他人 PR）——非本包文件，严禁删除/修改。修复：切到 `feat/knavalbattle-26.04.0` 分支并只提交 `archives/k/knavalbattle/`，使 junk_check 进入 incremental 模式（`git diff origin/main...HEAD` 只含本分支改动），JC PASS、W3 通过并写入 `.ci-result.json`。
- **status 保持 published 需要 reports/test-report.md**：finish 前置关卡检查发现 test-report.md 缺失会降级 built；已补本测试报告。
- `.build-context-knavalbattle-26.04.0` 的 `BUILD_SYSTEM="autotools"` 是 init_build 误判，实际为 **cmake**（manifest.yaml/notes 均已修正）。
- 产物为纯可执行包（无 lib/），软件级 `commands.json` 已声明（R38，type=tool）。
---

**编译结束**: 2026-09-18 15:51
**最终状态**: published
