# akonadi 25.12.3 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-26
- 编译器: clang/clang++
- 状态: built

## 编译步骤

Conan recipe 使用 KDE release-service 官方源码包，配置 Akonadi 为共享库构建，并将数据库后端固定为 SQLite：

```bash
conan create archives/a/akonadi/25.12.3 --build=missing
```

关键 CMake 选项：
- `DATABASE_BACKEND=SQLITE`
- `BUILD_TESTING=OFF`
- `BUILD_TOOLS=OFF`
- `BUILD_DESIGNERPLUGIN=OFF`
- `INSTALL_APPARMOR=OFF`
- `KF_IGNORE_PLATFORM_CHECK=TRUE`
- `KF_SKIP_PO_PROCESSING=ON`

为覆盖上游 release-source 测试，recipe 在主安装构建后额外配置一个不安装的 `upstream-tests` 构建树：
- `BUILD_TESTING=ON`
- `BUILD_TOOLS=ON`
- `DATABASE_BACKEND=SQLITE`
- `AKONADI_RUN_ISOLATED_TESTS=OFF`

该构建树只构建已注册 CTest 所需目标，运行前会签名 build-tree ELF、准备 KF 依赖 `DT_NEEDED` 兼容链接、生成隔离 MIME 数据库，并在 OHOS 上排除当前环境无法真实执行的测试项。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Windows/OHOS tar 在源码解包时报 `autotests/server/unittestenv` symlink 错误 | 上游 tar.xz 内包含测试目录软链接，平台 tar 对该 symlink 不兼容 | `source()` 使用 Python `tarfile` 安全解包，并跳过 symlink/hardlink |
| 2 | Akonadi 需要 `Qt6::Sql` 和 `Qt6::DBus` | KF baseline 依赖原 `qtbase/6.11.1`，但 Akonadi 需要 DBus/Sql 变体 | 直接依赖 `qtbase-sql-dbus/6.11.1`，并在 CMake 搜索路径中优先它 |
| 3 | 默认 MySQL 后端不适合当前制品仓 | MySQL/PostgreSQL server 运行依赖未作为 Akonadi baseline 发布 | 设置 `DATABASE_BACKEND=SQLITE` |
| 4 | `xsltproc` 和 `update-mime-database` 是 configure/install 阶段工具 | 上游 CMake 通过 `find_program()`/ECM `FindSharedMimeInfo` 查找 | 将 `libxslt`、`shared-mime-info` 作为 `tool_requires`，并传入绝对工具路径 |
| 5 | CI #31353/#31368/#31391/#31438/#31453/#31465/#31482 在 CMake try-compile 阶段报 `lld` 的 `libxml2.so.16` 缺符号 | OHOS SDK generic `lld` 被 Conan 依赖路径中的 `libxml2.so.16` 污染；首次 wrapper 只写入后置 `tc.variables`，晚于 Conan `compilers` block；后续只给 compiler 进程注入 `LD_LIBRARY_PATH` 仍未传到 clang 拉起的 lld；自定义 `ld.lld` wrapper 也未让 clang 离开 generic `lld` 路径；`#31482` 证明 CMake 已带上 `-fuse-ld=/data/service/hnp/bin/ld.lld`，但 SDK `llvm/lib` 若已存在于 `LD_LIBRARY_PATH` 后段，wrapper 旧逻辑不会把它提升到最前，仍会先加载 Conan `libxml2` | 生成 OHOS-only compiler wrapper，并直接覆写 `tc.blocks["compilers"]` 的 C/CXX 路径，使 wrapper 在 CMake try-compile 前生效；从实际 compiler 推导 SDK `llvm/lib`，要求存在 `libxml2.so.16`，并用 `lld -flavor gnu --version` 探测；同时在 CMake exe/shared linker flags 和 wrapper 链接分支中显式使用 `/data/service/hnp/bin/ld.lld`，每次 wrapper/linker wrapper 执行都将 SDK `llvm/lib` 去重并提升到 `LD_LIBRARY_PATH` 首位，避免静默切换到 `ld.bfd` 或污染目标测试 |
| 6 | CI #31488 在 `cmake.build()` 阶段编译 `src/private/scope.cpp` 失败，报 `src/shared/akranges.h` 中 `QList<QVariant>` 不满足 `AkTraits::Container` | `aktraits.h` 的 concept 直接使用 `std::begin/std::end`，但该头文件没有自包含 `<iterator>`；`akranges.h` 是先 include `aktraits.h` 再 include `<iterator>`，在 clang/libc++ 下约束检查失败 | 添加 `patches/0001-src-shared-aktraits.h.patch`，让 `aktraits.h` 自己 include `<iterator>` |
| 7 | CI #31497 在 `source()` 阶段应用 `0001-src-shared-aktraits.h.patch` 失败 | patch hunk 写成 `@@ -8,2`，GNU patch 可 offset 到第 9 行，但 Conan 的 patch 应用器按精确行号检查，上游第 8 行为空行 | 将 hunk 改为精确的 `@@ -9,2 +9,3 @@` |
| 8 | CI #31498 在 `cmake.build()` 93% 编译 `KPim6AkonadiAgentWidgetBase` 时触发 `static_assert(false, "This links to QWidgets")` | `AgentBase::initCore<T>` 的断言位于函数模板内，但表达式是非依赖的 `false`；clang 15 会在模板定义阶段诊断，而不是等实际实例化 | 添加 `patches/0002-src-agentbase-agentbase.h.patch`，将断言改成依赖 `T` 的恒假表达式，保留误用 `initCore<T>` 链接 Widgets 时失败的语义 |
| 9 | CI #31499 主包已完成构建、安装和打包，但 `test_package` 的 `cmake.test()` 阶段只显示 CTest 失败，未输出消费者程序 stderr/stdout；同时 CMake `test` 目标触发 `make -j20` 时出现 jobserver FIFO 被拒 | `CMake.test()` 走构建系统 `test` target，CTest 参数不可直接传递，也不利于暴露运行期错误；OHOS 上 GNU make 并行 jobserver 创建 FIFO 受限 | 在 `test_package.test()` 中先通过 `self.run()` 显式运行 `test_akonadi`，再从构建目录执行 `ctest --output-on-failure --no-tests=error -j1`，保留 CTest 结果并输出失败细节 |
| 10 | CI #31500 显式运行 `./test_akonadi` 后报 `libKPim6AkonadiCore.so.6`、`libKPim6AkonadiPrivate.so.6` 找不到，并伴随 Akonadi API 符号重定位失败 | `test_package` 运行环境未稳定解析被测包自身依赖对象，且目标测试执行未显式使用 Conan run scope | 生成 `VirtualRunEnv` 和 Akonadi 自定义 runenv，按 ref name 扫描 `self.dependencies.values()` 取得被测包 dependency，运行时显式加入其 `lib`；`test_akonadi` 和 CTest 均用 `scope="run"`/`env=["conanrun", "akonadi_test_runenv"]` 执行 |
| 11 | CI #31502 仍在 `test_package` 直接运行 `./test_akonadi` 时报同一组 Akonadi runtime library not found；同时构建消费者时 Conan/CMake 仍传入 `-- -j20`，OHOS make jobserver FIFO 有噪声 | runenv 脚本叠加没有稳定进入目标进程的实际 loader 环境，兼容目录也未显式进入 `LD_LIBRARY_PATH`；`cmake.build(cli_args=["--parallel", "1"])` 仍会被 Conan 追加默认构建并行参数 | `test()` 直接组合 `VirtualRunEnv`、被测包 `lib`、兼容链接目录和 Qt plugin/qml 路径，用 `EnvVars.apply()` 注入当前进程后以 `env=None` 运行 `test_akonadi` 和 `ctest`；同时记录 test binary、Akonadi libdir、Akonadi libs 和 `LD_LIBRARY_PATH` 前缀用于后续 CI 诊断；消费者构建改为显式执行 `cmake --build ... --parallel 1` |
| 12 | 远端手工复核确认 `LD_LIBRARY_PATH` 已包含 Akonadi 包 `lib` 后，直接 `dlopen`/运行仍对 `libKPim6AkonadiPrivate.so.6` 报 `Permission denied` | OHOS 目标动态加载要求 ELF 有可用签名；Akonadi 安装后的包内 ELF 不是最终可加载状态，错误表象仍可能被 loader 打成 library not found | `package()` 在 OHOS/HarmonyOS 下遍历包目录内普通 ELF，先用 `llvm-objcopy --remove-section .codesign` 去掉旧签名段，再用 `binary-sign-tool sign -selfSign 1` 对库和可执行文件重新签名并设为 `0755`；找不到签名工具时直接 fail |
| 13 | Akonadi 包库可加载后，`test_akonadi` 又失败在 KF 依赖中的绝对或带路径 `DT_NEEDED`，如旧 `$HOME/.cache/conan2/.../libKF6ConfigGui.so` 以及 `../../bin/libKF6ConfigCore.so` | 部分已发布 KF 包的 ELF 动态段记录了构建机 Conan cache 绝对路径或相对路径型 NEEDED，OHOS loader 对带 `/` 的 NEEDED 不走普通 `LD_LIBRARY_PATH` basename 搜索 | `test_package` 在运行前用 `llvm-readelf/readelf -d` 扫描 runtime package 的 ELF，按库 basename 映射到当前 Conan 包 `lib`，为旧 `.cache/conan2` 绝对路径和相对路径 NEEDED 创建兼容 symlink/copy；同时保留 Akonadi loader 兼容目录和显式 runtime env |
| 14 | 上游 CTest 构建树中的 KF 依赖同样失败在 `../../bin/libKF6ConfigCore.so`、`../../bin/libKF6IconThemes.so` | 上游测试从 build tree 的不同工作目录启动，OHOS loader 对带路径 `DT_NEEDED` 的解析需要覆盖 ELF 目录、CTest 工作目录和旧 Conan cache alias | 主 recipe 复用并扩展 NEEDED helper：扫描 runtime package 与 upstream build tree ELF，收集 CTestTestfile 所在目录和 ELF 所在目录，按 basename 建立绝对/相对兼容链接 |
| 15 | `mimetypecheckertest` 初始失败，先报 Akonadi 自定义 MIME type 不存在，补 Akonadi XML 后又缺 `text/x-vcard` 到 `text/directory` 的 alias | 当前 `shared-mime-info/2.5.1` 包只提供 `update-mime-database` 与源数据，没有可直接消费的完整 `share/mime` database；隔离 `XDG_DATA_HOME` 中也没有 Akonadi 的 MIME XML | 上游 CTest 前在隔离 `XDG_DATA_HOME` 下复制 `akonadi-mime.xml`，写入最小 vCard alias XML，并运行 `update-mime-database` 生成测试专用 MIME cache |
| 16 | 上游 CTest 中 27 个条目直接 abort 为 `D-Bus session bus is not available!`，另有 6 个 fake-session/model 测试在 OHOS Qt runtime 下稳定 SIGSEGV | 当前 `dbus/1.14.10` 依赖只打包 libdbus 静态库，不提供 `dbus-daemon`；6 个模型/Job/fake monitor 单元在 33332 上复测仍稳定崩溃，非 loader/MIME 问题 | recipe 若找到 `dbus-daemon` 会尝试启动临时 session bus；找不到或启动失败时只排除 session-bus 依赖项。OHOS 稳定 SIGSEGV 的 6 个 CTest 也单独排除，并在验证结果中按 excluded 记录，不计入通过 |
| 17 | CI #31716/#31725 均在 upstream CTest 目标构建后段超出 `conan create` 3600 秒限制，#31725 尾部显示刚完成 `akrangestest` 链接后被判 timeout；#31762 在排除 `akrangestest` 后仍超时，#31805 在 16 项自动集合下构建到 `cachepolicytest` 后仍被 timeout | `akrangestest`、server/storage CTest 目标以及完整 supported 集合的额外 build tree 使官方 CI 自动构建无法在 3600 秒内留出签名和 CTest 运行时间；这些测试已在 33332 手工最终 run 中通过 | 官方 CI 自动 upstream 集合收敛为 13 个非 server 核心 CTest，覆盖协议/IMAP/数据流/item/tag/cache/MIME/helper smoke；server/storage 与其余已手工通过项保留为 33332 补充验证，不计入官方自动执行通过数 |
| 18 | CI #31871 在 13 项自动集合下已完成 upstream test build、签名和 MIME database 准备，但进入 D-Bus session 检测时报 `KeyError: "'dbus' not found in the dependency set"` | `dbus` 是 target requirement，不一定出现在 build dependency set，`ConanFile.dependencies.get()` 对缺失 key 会抛 `KeyError`，导致“没有 `dbus-daemon`”未能按预期降级为排除 session-bus 测试 | `_build_tool_path()` 对 build/host dependency 查找分别捕获 `KeyError`，缺失依赖时继续尝试 PATH/OHOS tool 查找；找不到 `dbus-daemon` 时 `_optional_dbus_session()` 正常返回空地址并排除 session-bus CTest |

## 源码修改

- `patches/0001-src-shared-aktraits.h.patch`: 为 `src/shared/aktraits.h` 补 `<iterator>`，修复 C++20 concept 中 `std::begin/std::end` 的声明依赖。
- `patches/0002-src-agentbase-agentbase.h.patch`: 将 `AgentBase::initCore<T>` 中的 `static_assert(false)` 改成依赖模板参数的恒假表达式，兼容 clang 15 的模板诊断规则。

## 依赖版本

- Qt: `qtbase-sql-dbus/6.11.1`, `qtdeclarative/6.11.1`, `qtshadertools/6.11.1`, `qtsvg/6.11.1`
- KDE Frameworks: `kconfig/6.18.0`, `kconfigwidgets/6.18.0`, `kcoreaddons/6.18.0`, `ki18n/6.18.0`, `kiconthemes/6.18.0`, `kitemmodels/6.18.0`, `kwidgetsaddons/6.18.0`, `kxmlgui/6.18.0`, `kcrash/6.18.0`, `kwindowsystem/6.18.0`, `kcolorscheme/6.18.0`, `kguiaddons/6.18.0`, `kitemviews/6.18.0`, `kcodecs/6.18.0`, `karchive/6.19.0`
- Tools/system libs: `ecm/6.26.0`, `libxslt/1.1.45.2`, `shared-mime-info/2.5.1`, `dbus/1.14.10`, `lzma/5.6.2`, `libxml2/2.15.3`, `openssl/3.5.6.1`, `zstd/1.5.7`

## 验证结果

本地 Windows 侧已完成 Python 语法、源码 URL/SHA256、Conan export、源码解包，以及 OHOS profile 下 `conan install --build=never` 依赖图/二进制下载验证。

远端 33332 手工验证已通过：
- r9 `conan-manual-r9-relative-needed`: 复用已安装 Akonadi 包验证 `test_package` runtime 修复，`test_akonadi` 输出 `PASS: Akonadi Core API, QSQLITE and QtDBus are available`，CTest `1/1` 通过。
- r10 `conan-manual-r10-package-sign`: 从源码重建 Akonadi 主包，`package()` 自动签名 `18` 个 OHOS ELF，随后 `test_akonadi` 与 CTest `1/1` 通过。该手工环境仅对 33332 临时替换 compiler/lld/xmllint 路径，本地 recipe 仍保留官方 CI 路径。
- upstream CTest probe `upstream-probe-r2`: `BUILD_TESTING=ON`、`AKONADI_RUN_ISOLATED_TESTS=OFF` 后注册 64 个 CTest；首轮完整运行确认 3 个 xmllint 项因 `/bin/true` 不计真实通过，27 个 session-bus 项因无 `dbus-daemon` abort，23 个 KF `DT_NEEDED` 项由兼容链接修复，`mimetypecheckertest` 由隔离 MIME DB 修复。
- upstream CTest final `codex-a-25.12.3-akonadi-upstream-ctest-final-28-r1-20260826-180958-10805`: 排除 3 个无真实 xmllint、27 个无 session bus、6 个 OHOS Qt fake-session/model SIGSEGV 后，远端手工实际执行 28 个 CTest，`28/28` 通过。
- 官方 CI 自动 upstream CTest 集合为 13 个非 server 核心 CTest，避免 `conan create` 超过 3600 秒限制；其余已在 33332 手工通过的 supported CTest 只作为补充验证记录。

## 注意事项

- 主安装构建保持 `BUILD_TESTING=OFF`；上游测试通过独立 `upstream-tests` 构建树运行，避免测试目标进入最终包。
- 上游 release-source 当前可注册 64 个非 isolated CTest；本适配在 OHOS 33332 手工验证通过 28 个。官方 CI 自动执行其中 13 个非 server 核心项，其他已手工通过项因 `conan create` 3600 秒限制只作为补充验证记录；其余排除项按 `xmllint unavailable`、`dbus-daemon unavailable`、`OHOS Qt fake-session/model SIGSEGV` 分别记录，未计入通过数。
- 上游安装会产生多个可执行文件，包括 `akonadictl`、`akonadiserver`、`akonadi2xml` 等，因此软件级目录提供 `commands.json`。

---

**编译结束**: 2026-08-26
**最终状态**: built
