# qastools 1.4.0 — HarmonyOS PC 适配 notes

## 适配日期
2026-09-19（配方与补丁）
2026-09-26（CI L0 门禁修复：test_package 实质化 + commands.json 补齐）

## 依赖闭包
| 依赖 | 版本 | 角色 |
| --- | --- | --- |
| qtbase-sql-dbus | 6.11.1 | Qt6 Core/Gui/Widgets/Network/DBus（E323/E441 先例：裸 qtbase/6.11.1 为 FEATURE_dbus=OFF） |
| qtsvg | 6.11.1 | Qt6 Svg 组件 |
| alsa-lib | 1.2.16.1 | ALSA 客户端库 |
| libudev-zero | 1.0.4 | libudev 静态 drop-in（R26：系统库名 → static-only） |

## 补丁清单（5 个，全部 portability）
| 文件 | 说明 |
| --- | --- |
| 0001-i18n-skip-linguist-tools-on-ohos.patch | Qt6LinguistTools 缺失时跳过 i18n 子目录（制品仓 qtbase 变体均不含 LinguistTools；翻译运行时加载，跳过安全） |
| 0002-global-include-dirs.patch | 顶层注入 UDEV_INCLUDE_DIRS / ALSA_INCLUDE_DIRS（子目录 CMakeLists 的 INCLUDE_DIRECTORIES 不继承顶层） |
| 0003-sstream-include.patch | states_db.cpp 显式 `#include <sstream>`（musl/libc++ 下 basic_ostringstream 未隐式包含） |
| 0004-qashctl-udev-libs.patch | 子目录 `SET(UDEV_LIBRARIES udev)` 改为优先读取 conanfile 传入的 UDEV_LIBRARIES_CACHE（绝对路径 libudev.a） |
| 0005-qasmixer-udev-libs.patch | 同 0004，qasmixer 侧 |

## conanfile generate() 关键项
- CMAKE_PREFIX_PATH = qtbase-sql-dbus 包目录 : qtsvg 包目录
- Qt6_DIR / Qt6Svg_DIR 显式缓存变量（E438 先例）
- CMAKE_MODULE_PATH = qtbase 的 lib/cmake/Qt6/platforms（Platform/HarmonyOS.cmake include Linux）
- UDEV_LIBRARIES_CACHE = libudev-zero 包内 lib/libudev.a 绝对路径
- CMakeDeps 生成 alsa-lib / libudev-zero 的导入 target

## 上游测试
- CTest 注册 0 个、无 test 目录、无 add_test → **无自动化测试入口**（清点证据见 test_package/MANIFEST.yml）
- test_package 独立承担 L1：**13 个用例**（TP-001..009 静态 + TP-010..013 运行期），真实 exec 被测包的三个可执行文件

## CI 门禁修复记录（2026-09-26）

PR #11414 首轮 CI 报 `L0 quality gate failed: no_test_sources stub_test_method commands_json_r38`。
三项均为配方仓库结构问题，与 qastools 源码/补丁无关，根因与修法：

| 门禁 | 根因 | 修法 |
| --- | --- | --- |
| L0c `no_test_sources` | `test_package/` 下只有 `conanfile.py` + `MANIFEST.yml`，无 `.c/.cpp/.cc/.cxx/.sh/.py` 测试源（`find -maxdepth 2 -not -name conanfile.py` 无命中） | 新增 `test_package/test_qastools.sh` |
| L0d `stub_test_method` | `test()` 只用 `assert` + `self.output.info` 读 ELF 字节，`grep -q "self\.run"` 无命中 —— 判为空壳 | `test()` 改为 `self.run(CONFIG_SHELL bash test_qastools.sh <pkg>/bin)`，断言落在真实进程输出上 |
| L0k `commands_json_r38` | `package_type = "application"` 触发 CLI 判定，但软件级目录缺 `commands.json`（R38） | 新增 `archives/q/qastools/commands.json`（type=tool，versions.1.4.0.ref=qastools/1.4.0） |

原 test() 的 ELF 魔数/NEEDED 静态校验能力已并入 `test_qastools.sh`（TP-003/006/009 保留 ELF 魔数断言），
并**新增**了原先完全缺失的运行期验证。

## 上游命令行契约（源码级核对，v1.4.0，测试断言的依据）
- 三个程序都在 `main()` 进入 Qt 事件循环**之前**处理 `--version` / `--help`
  （`shared/src/…` → 各程序 `src/desktop_items.cpp::parse_cmd_options`），故 headless 下可安全断言（R7）。
- `qasmixer`：`main.cpp:34-37` 为 `if (res < 0) return res;`，`parse_cmd_options` 对
  `--version/--help` 返回 `-1` → 进程以 **255** 退出且不进事件循环，退出码可硬断言。
- `qashctl`（`main.cpp:27-30`）与 `qasconfig`（`main.cpp:24-27`）：上游写成
  `if (res < ditems.init_settings (argc, argv))`，**二次调用** `init_settings` 后比较
  `-1 < -1` 为假，条件落空 → 打印版本号后继续进入 `app.exec()`，进程不自行退出。
  故这两个程序的断言只落在 stdout 版本串上，由 `QASTOOLS_TEST_TIMEOUT`（默认 15s）超时终止，
  rc=124 属预期。这是上游缺陷，本 PR 不改源码，如实记录。
- 版本串形态为 `"<PROGRAM_NAME> <VERSION>"`，`VERSION` 由顶层 `PACKAGE_VERSION` 派生 → `1.4.0`。

## 平台注意事项（测试期）
- OHOS 无 X11/Wayland → `QT_QPA_PLATFORM=offscreen`（conducteo/acetoneiso/diffpdf/marknote 先例）。
- `libc++_shared.so` 在 OHOS SDK 的**按架构分层** llvm lib 目录（`.../llvm/lib/aarch64-linux-ohos`），
  而 CI profile 的 buildenv 只前置了 `llvm/lib`（不含架构层）→ 测试脚本按
  `OHOS_SDK_LLVM_LIB` 覆盖并补齐（conducteo 同款处置）。
- OHOS 的 `/system/bin/sh`（mksh）不能执行 ELF 二进制 → `test()` 必须经 `CONFIG_SHELL`
  指向的 bash 包装（conducteo/acetoneiso 同款）。
- 直接从包目录 exec（未做 writable-copy + 自签）。依据：conducteo / acetoneiso /
  marknote / diffpdf / tina 五个已合包均如此并通过 CI；仅 fceux 因其自身构建产物
  未签名而走了 `archives/f/fceux/2.6.6/test_package/conanfile.py` 的拷贝+自签路径。
  若 CI 报 `Permission denied` 或信号被杀，下一步即照 fceux 先例补该路径。
- **2026-09-27 实测修正（E077）**：CI build #62097 首次真实 exec 即报
  `timeout: exec .../qasmixer: Operation not permitted`（EPERM rc=126），
  TP-010..013 全败、静态 TP-001..009 全过。根因：OHOS 内核只允许加载带有效
  `.codesign` 的 ELF；conan 缓存（用户存储路径）下的未签名 ELF 一律 exec 被拒，
  与"五个已合包"不等价——它们要么是库、要么其二进制已带签名。
  修复：conanfile.py `package()` 打包期对三个二进制自签（`binary-sign-tool
  sign -selfSign 1`，cronutils/1.1 先例），签名输出会丢执行位，故先 `chmod 0o755`
  后签名再 `os.replace` 并恢复 `0o755`。签名后从包目录 exec 生效（本机最小实验：
  自签 toybox 副本可 exec，未签名副本 EPERM rc=126）。

## 已知限制
- udev sound 卡热插拔监听在 OHOS 运行期无 udev 守护进程，`udev_monitor_new_from_netlink` 返回 NULL 时源码降级分支生效（不崩溃，功能不可用）。
- 翻译 .qm 未生成（i18n 子目录跳过），应用回退内置英文字符串。
- 上游 `qashctl` / `qasconfig` 的 `res < ditems.init_settings(...)` 条件落空缺陷未修（见上）。

## 本地验证
- 2026-09-19：`conan create archives/q/qastools/1.4.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing` → PASS（日志 `.ci_logs/target_qastools.log`）。该轮 test_package 为纯静态 TP-001..006。
- 2026-09-26 门禁修复：**L0c / L0d / L0k / L1d 四道门禁的判定逻辑已在隔离工作树内逐条复跑通过**
  （RED 复现 `no_test_sources stub_test_method commands_json_r38` → 修复后全绿）。
  新的运行期用例（TP-010..013）未能在 09-26 本机实测（无 OHOS 工具链），首次真实执行由 PR CI 承担。
- 2026-09-27 CI L1 签名修复（E077）：PR CI build #62097 真实 exec 失败（EPERM rc=126，见上），
  修复为 conanfile.py `package()` 打包期自签三个二进制；修复后已在本地对签名机制做最小实验验证
  （自签 ELF 可执行），并交由 PR CI 复跑做最终 GREEN 判定。
