# lomiri-polkit-agent 0.3.3 适配笔记

## 编译环境

- 构建系统: cmake（C++17）
- 编译日期: 2026-09-29（首轮）/ 2026-10-02（P1 修复轮强制重建复验）
- 编译器: clang 15.0.4 / clang++（OHOS SDK 26.0.0.18）
- 目标: aarch64-linux-ohos，profile = `ci/conan/profiles/ohos-aarch64`（CI 同款）
- 状态: built（W3 = conan create + G0-G4 门禁通过；未经 CI 上传）

## 编译步骤

1. 取上游官方归档（GitLab 标签 `0.3.3`，**无 v 前缀**；`/-/archive/v0.3.3/...` 会 404），
   sha256 `96167c491cbb17d800e7037c0b038931104423e5d916069f34661231ccdba028`。
2. `generate()`：
   - `PkgConfigDeps` 生成 `polkit-agent-1` / `gio-2.0` / `libnotify` / `properties-cpp` 的 `.pc`；
   - 补回生成版 `glib-2.0.pc` 的 `-lintl`（`PkgConfigDeps` 按 `cpp_info` 重建时丢失）；
   - `CMakeToolchain` 设 `BUILD_TESTING=ON`（上游 3 例随包构建并在 `build()` 内实跑，见问题 4/7），
     并把各依赖包 `libdir` 以 `-L` 注入
     `CMAKE_EXE_LINKER_FLAGS` / `CMAKE_SHARED_LINKER_FLAGS`（glib 目录排首位）。
3. `build()`：`PKG_CONFIG_PATH = generators_folder + 各依赖包 {lib,share}/pkgconfig`
   （全部落在构建目录/依赖包目录内，不注入共享系统前缀，R49）→ `cmake configure` + `build`。
4. `package()`：`cmake install` → `bin/lomiri-polkit-agent/policykit-agent` +
   `lib/systemd/user/lomiri-polkit-agent.service`。
5. 验证：`conan-verify lomiri-polkit-agent 0.3.3` → G0/G1/G2/G3 ✅、G4 ⚠️（无 cache 路径，
   取不到 package id）、L2/L4/L5 ⏭️ 跳过（无 cache 路径）→ **配方验证通过**
   （报告 `reports/conan-verify-report.md`）。

复现命令：

```bash
conan create archives/l/lomiri-polkit-agent/0.3.3 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 `Unknown CMake command "add_formatcode_target"` / `"ENABLE_COVERAGE_REPORT"` | 上游顶层 CMakeLists 无条件调用 Ubuntu `cmake-extras` 提供的两个可选目标，源码树未随附对应 `.cmake` 模块 | `patches/0001`：用 `if(COMMAND ...)` 守卫（不改变语义，仅跳过本机不存在的可选目标） |
| 2 | 链接报 `ld.lld: unable to find library -lgio-2.0` / `-lpolkit-agent-1` | 上游只用 `pkg_check_modules(...)_LIBRARIES`（纯 `-l` 库名，不含 `-L`），依赖 Ubuntu 系统库目录 | `generate()` 把每个依赖包 `libdir` 以 `-L` 注入 `CMAKE_(EXE|SHARED)_LINKER_FLAGS`（路径全在 Conan 包目录内，R49） |
| 3 | 链接报 `undefined symbol: g_libintl_gettext` | glib 的 OHOS 包把 gettext 实现放在自带 `lib/libintl.so`（glib 自身对 `g_libintl_*` 是未定义引用），其自带 `glib-2.0.pc` 写有 `-lintl`；`PkgConfigDeps` 按 `cpp_info` 重建的 `.pc` 丢掉了它 | `generate()` 在生成的 `glib-2.0.pc` 的 `Libs:` 行补回 `-lintl`，并把 glib 的 `libdir` 排在 `-L` 首位，避免同名 `libintl` 抢先解析 |
| 4 | 上游 `tests/` 无法构建（pkg-config 模块 `dbustest-1` 缺失；GMock 依赖硬编码 `/usr/src/gtest`） | `tests/CMakeLists.txt` 走 `find_package(GMock)` + `GTEST_SOURCE_DIR=/usr/src/gtest/src`，并提供 Ubuntu `libdbustest` 专有的 `dbustest-1` | `patches/0003` 把两个探测块换成配方注入变量（`gmock/1.17.0`、`dbustest/19.04.0`、`dbus/1.14.10`），`BUILD_TESTING=ON` → 3 例在 OHOS 真实构建；`build()` 内实跑 ctest（R51，见问题 7 与「上游测试申报表」） |
| 5 | **运行期 smoke test：二进制启动即 `Error loading shared library libnotify.so.4`，随后 `notify_notification_show`/`notify_notification_close: symbol not found`，self.run 退出码 1（dlopen 侧 `Permission denied`）** | **制品仓 `libnotify/0.8.3`（recipe rev `3d16c3c8`）的 `libnotify.so.4.0.0` 带一段无法通过 OHOS 动态链接器校验的 `.codesign`：`dlopen` 直接报 EACCES，库缺席导致依赖它的二进制在重定位 `notify_*` 符号时失败** | `test_package/generate()` 与配方 `build()`（`_sign_test_closure()`，上游 ctest 前）都把依赖图共享库复制到测试私有目录（`$TMPDIR` 下）统一重签名，并把该目录置于 `LD_LIBRARY_PATH` 首位；**只写私有副本，不改动 conan 缓存**（同 R49 的私有 prefix 口径）。依赖包本身的制品缺陷应由其配方修复后重发 |
| 6 | `libnotify/0.8.3.1` 依赖冲突 | 0.8.3.1 以 `force=True` 钉死 `glib/2.88.0.1`，与 `polkit/124.1` 的 `glib/2.84.0.1` 直接冲突（`ERROR: Version conflict`） | 精确引用 `libnotify/0.8.3`（与 `polkit/124.1`、`gdk-pixbuf/2.44.6` 同处 glib/2.84 生态） |
| 7 | 上游 3 例闭包重签后可真实执行，但 0 例通过；首个失败点＝libdbustest 无法 spawn 总线守护进程（`Unable to start dbus daemon: Failed to execute child process “dbus-daemon” (No such file or directory)`，3 例累计 15 次） | 本包虽 `tool_requires("dbus/1.14.10")`，但该图解析出的制品（pkgid `8f3067d852b56f8fcaf7f0424e846c63b0a0c5ec` → 缓存目录 `.conan2/p/dbusb5cad6cb27f93/p`）**不含 `bin/`**（实测 `bin_exists=NO`，`lib` 仅 1 个条目）→ 配方按依赖 `bindirs` 组装 PATH 时自然跳过（实测 PATH 追加 5 项：libnotify/gdk-pixbuf/glib/libpng/dbustest）；对照实验（把含 `bin/dbus-daemon` 的另两个 dbus 制品目录手工加入 PATH）证明 daemon 可被拉起，但随即撞上 dbustest 的编译期配置路径 `--config-file //share/dbus-test-runner/{system,session}.conf`（前缀为空、非本机路径） | 不在本包内 hack：三层阻塞（① 已发布 dbus 制品缺 `bin/`；② dbustest 前缀烘死；③ mock 服务需 `python3 -m dbusmock`，而 OHOS dbus-python 轮子缺 GLib 主循环绑定）全部位于依赖包侧。配方按 R51 如实上报：ctest 真跑、逐例结果落 `reports/upstream-ctest.log`、以 WARN 呈现且**不阻断编译/打包**（强制重建 `EXIT=0` 即证） |

### E489 签名问题的三态对照实验（问题 5 的证据，本机实测）

| 变体 | 操作 | `dlopen` 结果 |
|---|---|---|
| A 原件 | 直接加载制品仓缓存中的 `libnotify.so.4.0.0` | ❌ `Permission denied`（加载器拒绝，EACCES） |
| B 去签名段 | `llvm-objcopy --remove-section .codesign` | ❌ 仍 `Permission denied`（**未签名同样被拒**） |
| C 去段 + 重签 | B + `binary-sign-tool sign -inFile <elf> -outFile <elf> -selfSign 1`（本包实现改用 `-signAlg SHA256withECDSA`，同为自签名） | ✅ 可正常加载 |

结论：唯一变量是「签名是否有效」；修法为 **先移除旧 `.codesign` 段，再自签名**
（顺序不可颠倒，直接对失效签名重签无法通过）。同一 smoke test 在修复后从
`--version` 退出码非 0 变为全部断言通过。

## 源码修改

| 补丁 | 内容 |
|---|---|
| `patches/0001-CMakeLists.txt.patch` | 顶层 `CMakeLists.txt`：`add_formatcode_target()` / `ENABLE_COVERAGE_REPORT()` 调用包进 `if(COMMAND ...)`，使非 Ubuntu 主机可 configure |
| `patches/0002-service-main.cpp.patch` | `service/main.cpp`：增加 `--version` / `--help` 分支，使 D-Bus 激活型服务二进制可在无 session bus/polkitd 的环境被冒烟测试（R34/L1 运行层） |
| `patches/0003-tests-CMakeLists.txt.patch` | `tests/CMakeLists.txt`：去掉 `find_package(GMock)` / `GTEST_SOURCE_DIR=/usr/src/gtest/src` 与 `pkg_check_modules(dbustest-1)` 两个 Ubuntu 专有探测块，改用配方注入变量（`gmock/1.17.0`、`dbustest/19.04.0`）→ 上游 3 例在 OHOS 可构建 |

三个补丁均为可移植性改动，不含平台宏（`__OHOS__`）——平台差异全部在 conanfile.py 内以
依赖注入方式处理（R8/R49）。

## 依赖版本

| 依赖 | 版本 | 用途 |
|---|---|---|
| polkit | 124.1 | `polkit-agent-1`（libpolkit-agent-1 + polkit-agent-1.pc），R37 适配修复版 |
| glib | 2.84.0.1 | `gio-2.0`（GDBus 会话总线） |
| libnotify | 0.8.3 | 桌面通知（运行期需重签名，见问题 5） |
| properties-cpp | 0.0.4 | D-Bus 属性封装 |
| gmock | 1.17.0 | 上游单元测试框架（`patches/0003` 注入，仅构建测试用） |
| dbustest | 19.04.0 | 上游测试的 D-Bus 会话夹具（`patches/0003` 注入；自带 `.pc` 未展开 prefix，故直接注入路径） |
| dbus | 1.14.10 | 测试夹具所需 `dbus-daemon`（`tool_requires`；实测该已发布制品不含 `bin/`，见问题 7） |

## 上游测试申报表（R51 三步法）

**① 清点**：上游源码自带 `tests/`，`tests/CMakeLists.txt` 注册 **3 个 ctest 用例**
（`agent-test`、`auth-manager-test`、`authentication-test`，均为单元测试）。

**② 可运行性**：**3/3 可构建、可运行**（适配后）。上游原状不可运行的硬原因是
`find_package(GMock)` + `GTEST_SOURCE_DIR` 硬编码 `/usr/src/gtest/src` 与 pkg-config
模块 `dbustest-1`（Ubuntu libdbustest）在 OHOS 侧均不存在；`patches/0003` 把这两个探测块
换成依赖图注入（`gmock/1.17.0`、`dbustest/19.04.0`、`dbus/1.14.10`），并在 `build()` 内
真实执行 `ctest --output-on-failure --timeout 180`（用例失败**不阻断构建**，结果如实记录）。

**③ 回填（实测：2026-10-02 首跑；2026-10-11 修复尝试后强制重建复跑，结论一致——3 例均构建并真实执行、0 通过）**：

> **2026-10-11 修复尝试记录**：探测到制品仓 `dbus/1.14.10.2` 制品含 `bin/dbus-daemon`（1.14.10 缺 bin 是第一阻塞的根源），依次尝试 ① tool_requires 升级 1.14.10.2 ② expat force 统一 2.8.2.1 / 2.8.2 ③ host 侧引入 1.14.10.2——四轮均 Version conflict 失败。根因（graph info JSON 实证）：dbustest/19.04.0 工具链**精确钉死** dbus/1.14.10（→ expat 精确 2.8.2），1.14.10.2 精确钉 expat/2.8.2.1，同 build 上下文双 dbus 节点版本互斥；tool_requires 不支持 force，profile replace_requires 属框架文件不可改，host 侧引入则撞 glib/2.84 vs 2.88。依赖改动已 revert 回绿基线（graph_rc=0 复验通过，create6 重建 3 例结论与首跑一致）。**已落地 `_make_dbus_daemon_wrapper`**（POSIX sh，BusyBox ash 兼容已干跑验证）：改写 dbustest 烘死的空前缀配置路径 + 补 machine-id + exec 真 daemon——未来 dbus 制品带 bin/ 时自动打通，届时 3 例预期可过。剩余两层阻塞（dbusmock 的 GLib 绑定、制品侧缺陷）不变。

运行前配方先在 `build()` 内执行 E489 依赖闭包重签名（实测 `新签 39 / 复用 0 / 失败 0`
→ `<build>/test-closure-signed`，只写构建目录内私有副本、不改动 conan 缓存），3 例因此得以
越过加载期、真实执行到上游断言点：

| 用例 | 是否构建 | 是否运行 | 结果（2026-10-02） | 运行期阻塞（首个失败点） |
|---|---|---|---|---|
| `agent-test` | ✅ | ✅（gmock 注册 4 例） | ❌ failed 0.27s | libdbustest 无法 spawn 总线守护进程：`Failed to execute child process “dbus-daemon” (No such file or directory)` → 断言落在 `tests/agent-test.cpp:91` |
| `auth-manager-test` | ✅ | ✅（gmock 注册 4 例） | ❌ failed 0.08s | 同上（daemon 无法 spawn） → 断言落在 `tests/auth-manager-test.cpp:73` |
| `authentication-test` | ✅ | ✅（gmock 注册 3 例） | ❌ failed 0.09s | 同上（daemon 无法 spawn） → 断言落在 `tests/authentication-test.cpp:78` |

合计 **3 例执行 / 0 例通过**；拒载类错误 0 次（E489 重签生效）、daemon spawn 失败 15 次。
原始输出见 `reports/upstream-ctest.log`（含逐例 `Test #1..#3` 行）。阻塞链条共三层，
全部位于依赖包侧（证据见问题 7）：
① 本包已 `tool_requires("dbus/1.14.10")`，但该图解析出的已发布制品不含 `bin/`
   （实测 `bin_exists=NO`），配方按依赖 `bindirs` 组装 PATH 时自然跳过（追加 5 项）→ 夹具 spawn 失败；
② 对照实验把含 `bin/dbus-daemon` 的另两个 dbus 制品目录加入 PATH 后 daemon 可被拉起，
   但随即报 `Failed to start message bus: Failed to open "//share/dbus-test-runner/system.conf"` ——
   dbustest 的编译期配置路径前缀为空（空前缀 `//share`）；
③ mock 服务需 `python3 -m dbusmock`，而 OHOS `dbus-python` 轮子无可用 GLib 主循环绑定。
`ctest` 结果**不阻断构建**（平台阻塞下仍产出可用制品）；制品自身验证由 `test_package/`
（实质消费者用例，R34，7 项断言全通过）承担，台账见 `test_package/MANIFEST.yml`。

## 验证结果

```bash
# W3（本地 CI 等价：干净制品 + CI 同款 profile）
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify lomiri-polkit-agent 0.3.3
# → G0 ✅ G1 ✅ G2 ✅（conan create EXIT=0）G3 ✅ G4 ⚠️（无 cache 路径）
# → L2/L4/L5 ⏭️ 跳过（无 cache 路径）→ ✅ 配方验证通过
```

`test_package`（`conan create` 时执行，日志 `reports/conan-create.log` 的 `[test]` 段；
本轮复验同批日志见 `reports/upstream-ctest.log`）：
结构层断言包内 `bin/lomiri-polkit-agent/policykit-agent` 为 aarch64 ELF、systemd user unit
已安装且非空；运行层经 `test.sh` 实跑 `--version`（断言含程序名与 `0.3.3`）与 `--help`
（断言含 `Usage:`），**全部通过**——修复前同一测试因问题 5 退出码非 0。实测输出：

```text
被测二进制: .../p/bin/lomiri-polkit-agent/policykit-agent
✅ ELF 校验通过 (e_machine=0xb7)
✅ 服务单元已安装: .../lib/systemd/user/lomiri-polkit-agent.service
[test] --version  →  lomiri-polkit-agent 0.3.3
[test] ✅ --version 含程序名与版本号 0.3.3
[test] ✅ --help OK
[test] 全部通过
```

## 交付物

| 文件 | 大小 | 说明 |
|---|---|---|
| `bin/lomiri-polkit-agent/policykit-agent` | 4,356,672 B | 服务二进制（aarch64 ELF，D-Bus 激活） |
| `lib/systemd/user/lomiri-polkit-agent.service` | 379 B | systemd user unit |
| 包总体积 | 4,378,518 B | 无头文件/库导出（`cpp_info` 全空） |

## 注意事项

1. **上游 unit 的 `ExecStart` 写死构建期绝对路径**（`configure_file` 用
   `CMAKE_INSTALL_FULL_PKGLIBEXECDIR`）：制品内的 unit 会带上 conan 缓存路径，
   部署到目标机时需由系统集成方重写（或按发行版打包规则重新生成）。属上游行为，未打补丁改动。
2. **运行期依赖链**：agent 由会话总线 `loadmodule`/`.service` 激活，需 session bus +
   polkitd + 认证后端；本包只交付二进制与 unit，端到端认证需目标环境具备这些系统组件
   （参见 `README.md` §5）。
3. **libnotify/0.8.3 制品签名缺陷**：本包测试通过私有副本重签名绕过；该依赖包应在
   制品仓修复后重发（证据：问题 5 与三态对照表）。
4. 产物未 strip，调试字符串内含构建目录绝对路径。
---

**编译结束**: 2026-10-02 21:20（P1 修复轮：强制重建复验 + 证据刷新）
**最终状态**: built
