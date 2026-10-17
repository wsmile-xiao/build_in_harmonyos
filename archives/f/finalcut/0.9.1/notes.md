# finalcut 0.9.1 适配笔记

## 知识积累与复用

- ✅ **E007**：复用 Autotools `config.guess`/`config.sub` 对 HarmonyOS triplet 的识别经验；配方在生成文件上幂等补齐识别逻辑。
- ✅ **E011**：复用 HMDFS 下生成的 configure 脚本 umask 导致临时 awk 脚本不可执行的经验；配方只改写构建目录中的生成文件。
- ✅ **E028**：复用静态构建以避免共享库覆盖系统库的经验；`finalcut` 使用静态库，ncurses 则作为独立 Conan 传递依赖提供 termcap 符号。
- ✅ 新增草稿 [E429-draft-32AB](../../../../knowledge/drafts/E429-draft-32AB.md)：真机上对 pty slave 执行 `TIOCSTI` 返回 EACCES，导致上游 `fkeyboard_test` 中 9 个输入注入用例不能注册；只影响依赖注入能力的测试，不推断所有 OHOS 版本，也不修改生产代码。

## 编译环境

- 构建系统：Autotools
- 编译日期：2026-10-02
- 目标设备：HarmonyOS 6.0，aarch64
- 工具链：Clang/Clang++ 15.0.4，libc++；Conan 2.29.1；CMake 4.1.2；GNU Make 4.4.1
- 状态：built；上游目标 28/30（28 PASS、2 个 BSD 后端 N/A），HarmonyOS aarch64 Release 消费者 CTest 为 2/2；详见 `reports/upstream-tests-ledger.md`
- 分支：`feat/finalcut-0.9.1`，起点为 `upstream/main`

## 编译步骤

上游正式源码为 GitHub `0.9.1` 发布归档，SHA256 为 `6593b3c43ba1de98e4e0e3a563dbf9316fade71ef85c82e6b6f086184ec69a56`。配方使用 `autoreconf` 生成 `configure`，再以 Conan 的 Autotools 工具链构建静态库。依赖已在制品仓核验：`ncurses/6.6`、`automake/1.18` 和 `libtool/2.5.4`。

关键配置：

- `--disable-shared --enable-static`
- finalcut 上游要求 C++14；配方将 `-std=c++14` 放在 profile 的 C++ 标准参数之后，避免较新的 `std::iterator` 弃用诊断触发 `-Werror`。
- ncurses 的头文件、库目录和 `-lncursesw` 由 Conan 依赖提供，并从 `package_info()` 透传给消费者。
- 对 autoreconf 生成的 `config.guess`、`config.sub`，配方用幂等 Python 文本变换加入 `aarch64-unknown-linux-ohos` triplet 识别；HarmonyOS 改动不写入 `.patch`。
- HarmonyOS HNP bash 在 Conan 深层 HMDFS 目录中需要 `PWD` 与实际构建目录一致。配方只在自身 build environment 中设置 `PWD=self.build_folder`，随后 configure、make 和 install 均成功。

Windows 工作区运行依赖预检时无法连接 `ohpcd`（Conan 报 `WinError 10013`），因此本机脚本把远端依赖报告为未发布；不能将该网络错误当作缺包。改从执行构建的 HarmonyOS 设备查询 `ohpcd`，`ncurses/6.6`、`automake/1.18`、`libtool/2.5.4` 三个 recipe 均存在，Conan 构建实际安装/使用了这些依赖。版本占用检查通过：`finalcut/0.9.1` 未占用。

本机使用的依赖预检命令：

```text
bash ci/scripts/preflight_check.sh finalcut/0.9.1 --deps 'ncurses/6.6 automake/1.18 libtool/2.5.4'
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案与结果 |
|---|---|---|---|
| 1 | 首次 Conan 配置报 `settings.os.version` 未定义 | 设备默认 profile 未声明 HarmonyOS 版本 | 使用仓库 `ci/conan/profiles/ohos-aarch64`（`os=OHOS`、`os.version=6.0`、aarch64、Clang 15/libc++）；后续 Conan 构建通过 |
| 2 | Autotools configure 报无法判断工作目录，日志反复出现 `getcwd` | HNP bash 从 HMDFS 构建目录启动时继承了指向父目录的 `PWD` | 配方 buildenv 设置 `PWD` 为 Conan build folder；最小复现由失败转为成功，正式构建配置通过 |
| 3 | Conan 的 CppUnit `.pc` 文件前缀未重定位，且上游测试 Makefile 漏传 `CPPUNIT_CFLAGS` | 设备 Conan CppUnit 包的 `.pc` 写有 `prefix=/`；上游 `test/Makefile.am` 只把 `CPPUNIT_LIBS` 接入链接行 | 测试专用临时 `.pc` 使用包的绝对路径，并通过测试专用 `CPPFLAGS` 显式加入 CppUnit include 目录；未把 CppUnit 加入生产配方依赖 |
| 4 | 上游部分测试不能在目标系统构建或断言不匹配 | 个别测试依赖 FreeBSD/OpenBSD 后端、引用当前发布头文件不存在的接口、出现重复定义，或断言固定了浮点/terminfo 表现 | 针对测试可移植性加入 `0006`；只在 HarmonyOS 门控内核不支持的 TIOCSTI 输入注入用例，其余逐项目标结果与具体原因记录于 `reports/upstream-tests-ledger.md`。Conan consumer 与 HarmonyOS 专属测试仍全部通过 |
| 5 | 正式 W3 clean build 经 GitHub archive URL 下载超时，codeload URL 被 Conan 误判为 ZIP | 测试设备无法及时完成 `github.com` archive 跳转链路；codeload 直连可用，但 URL 没有归档后缀 | 使用 GitHub 官方 codeload tag archive，并在 `conandata.yml` 显式给 `get()` 传 `filename: finalcut-0.9.1.tar.gz`；设备实测归档 SHA256 与原值一致（`6593b3c43ba1de98e4e0e3a563dbf9316fade71ef85c82e6b6f086184ec69a56`） |

## 源码修改

应用 6 个可复现补丁：

1. `0001-ftermlinux-isa-guard.patch`：仅在 ISA sysctl 支持代码启用时声明相关私有字段，修正 Clang `-Werror` 未使用字段问题。
2. `0002-configure-ac-quote.patch`：为 configure 中的 `$CXXFLAGS` 添加正确引用，支持 Conan 注入的多参数 flags。
3. `0003-am-cppflags.patch`：为 Automake include flags 补顶层源码路径，保证 out-of-source 构建能找到 `final/*.h`。
4. `0004-fscrollview-void-parent.patch`：在 `NDEBUG` 构建中显式使用仅供断言读取的变量。
5. `0005-test-clang-warnings.patch`：将三个 Clang 15 上游测试诊断降为非致命 warning，保留其余 `-Werror`。
6. `0006-upstream-test-portability.patch`：为上游测试启用 `UNIT_TEST`/`DEBUG`，只在原生 OS 注册 BSD 后端，在 HarmonyOS 避开被内核禁止的 `TIOCSTI` 输入注入用例；修复 aarch64 浮点与 terminfo 假设、测试 helper 重复符号和 FVTerm 测试桩签名，并修复 Sun key capability 指针的生命周期问题。

配方还会在 HarmonyOS 构建时仅为 `FKeyboardTest::init()` 添加 Clang `optnone`。真机 Release 构建实测表明该 fixture 初始化中的 `std::function` 回调复制在优化下触发 SIGSEGV；`optnone` 只覆盖测试夹具初始化函数，不改变库优化等级，也不禁用已注册测试。

配方同时携带 configure 使用的两个 autoconf-archive m4 宏。消费者测试包括普通 `FString` API 检查，以及仅在 CMake 报告 `HarmonyOS` 或 `OHOS` 时启用的 aarch64 PTY 交互流程：启动 FINAL CUT 对话框、渲染“鸿蒙”、通过终端键入中文、Tab 切换焦点、回车激活按钮，并检查应用正常退出且输入文本未损坏。

## 上游测试清点与结果

发布归档原有 30 个跨平台 CppUnit 目标。应用 `0006` 后，HarmonyOS aarch64 实测为 28/30：28 个适用目标全部通过，FreeBSD/OpenBSD 两个专用后端目标按 host 条件不注册、标记 N/A。`fkeyboard_test` 在 HarmonyOS 运行 4 个无交互依赖用例，9 个依赖内核拒绝的 `TIOCSTI` 用例不注册。Conan `build()` 现在会在打包前自动执行该上游检查。逐项结果见 `reports/upstream-tests-ledger.md`，其中单独保留了未适配时的实测基线。

## 验证结果

- HarmonyOS aarch64 `conan create`：finalcut 静态库构建和打包成功。
- HarmonyOS 6.0 aarch64 Conan consumer：`test_finalcut`、`test_ohos_unicode` 均通过，2/2。鸿蒙专项用例运行在新建 PTY 中，真实启动 FINAL CUT 应用、绘制含“鸿蒙”的对话框和输入框、键入“鸿蒙”、切换到 Accept 并回车；退出后检查 `FLineEdit` 返回的 UTF-8 文本/宽字符长度、终端输出及子进程成功状态。正式 W3 重跑的 consumer CTest 为 2/2，专项 UI 流程 1.50 秒、总耗时 1.53 秒。
- 最新 HarmonyOS aarch64 `ci/conan/build_and_test.sh` 运行中，Conan 日志记录 `make -j1 check` 为 28/28、consumer CTest 为 2/2；生成的 `ci-metadata.json` 记录 L0、L1、L4、L5 通过，L2 因无 `bin/` 跳过。真机日志保存在本地忽略文件 `reports/w3-local-ci.log`，本次结果不依赖手工改写 `.ci-result.json`。
- 仓库 `python tests/run_all.py`：其余 11 个测试文件通过；`test_v1220.py` 的 runner 硬编码 Linux HNP Git 路径，在 Windows 本机不可用。将该模块的 `GITBIN` 临时指向本机 Git 后，v12.20 的 33 项均通过；没有修改仓库测试文件。
- 运行命令、源文件计数与上游测试逐项结果记录于 `reports/upstream-tests-ledger.md`。

## 依赖版本

- 构建依赖：`ncurses/6.6`、`automake/1.18`（tool requirement）、`libtool/2.5.4`（tool requirement）
- 仅上游测试使用：`cppunit/1.15.1`

## 交付物

这是 Conan 源码配方，不包含真机二进制；Conan 在目标 HarmonyOS aarch64 上构建了静态包，并通过 consumer 集成测试。
