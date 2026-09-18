# wdq2wav 1.0.0 适配笔记

## 本轮状态
- 分支: `feat/wdq2wav-1.0.0`
- issue: #1715 https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/1715
- 当前阶段: 本机前置适配完成，待 OHOS 真机或 shadow CI 单包验证
- 适配日期: 2026-08-01

## W0 依赖检查
- 运行时/编译依赖: 无外部三方库，仅 C++ 标准库和 POSIX 文件接口
- 依赖适配拆分: 不需要新增依赖 PR

## 源码与构建系统分析
- 源码: Debian `wdq2wav_1.0.0+dfsg.orig.tar.xz`
- sha256: `6c99ee94e8e697f2cf41188c952f7ab90cba2d7deb04fd7dad24918fa9f0139d`
- 构建系统: 手写 Makefile
- 主要源码: `wdq2wav.cpp`, `wdq2wav.h`
- 产物: `wdq2wav` 命令行工具，附带 `wdq2wav.1` man page
- 上游测试: 未发现测试套件，未集成 `make check`

## 适配修改
- `conanfile.py`: 使用 `GnuToolchain`，限制 `os in ("Linux", "OHOS")`，按 application 打包 `bin/` 与 man page
- `conandata.yml`: 记录 Debian 源码 URL、sha256 与补丁
- `patches/0001-Makefile-use-toolchain-and-portable-install.patch`: 将硬编码 `g++` 改为 Conan toolchain 变量，追加本地 `-I.` include，并将 `install -o root -g root` 替换为 `mkdir/cp/chmod`
- `test_package`: 使用 CMake 编译 `test.cpp`，测试程序通过 `popen` 执行 `wdq2wav -h`，检查帮助文本包含 `usage:`, `wdq-file`, `wav-file`
- `test_package/MANIFEST.yml`: 记录消费者测试断言数 4

## 本机验证结果
- 已下载源码并校验 sha256
- 已确认源码包只包含 Makefile、`wdq2wav.cpp`、`wdq2wav.h`、man/html 文档
- Windows 本机无 `make` 与 `conan` 命令，无法执行完整 `conan create`
- MinGW `g++` 会进入源码 `WIN32` 分支并触发 Windows 专用兼容代码错误，不作为 OHOS/Linux 结论
- WSL 未安装可用发行版，无法用 Linux 用户态完成替代构建

## 待真机/shadow CI 命令

```sh
CI_PACKAGES="archives/w/wdq2wav/1.0.0" zsh ci/conan/build_and_test.sh
```

如使用 shadow CI 运行器：

```sh
/path/to/run-ohos-shadow-ci.sh archives/w/wdq2wav/1.0.0
```

建议真机验证关注：
- L0/L1 是否通过，`Build Summary` 是否显示 `Total: 1`
- 编译日志是否使用 OHOS profile 注入的 `clang++`
- `bin/wdq2wav` 和 `share/man/man1/wdq2wav.1` 是否进入包产物
- `test_package` 是否成功编译并运行 `test_wdq2wav`，间接执行 `wdq2wav -h`

## 真机验证结果

统一入口规范验证：

```sh
sh "$HOME/ohos-users/windrel/wdq2wav-1.0.0-pr1715/run-conan-heavy.sh"
```

最终 runner 目录：

```text
$HOME/ohos-test-runs/windrel-1.0.0-wdq2wav-1.0.0-pr1715-conan-20260801-152916-30536
```

验证摘要：
- `L0_RESULT=pass: all checks passed`
- `L1_RESULT=pass: test_package executed`
- `L2_RESULT=skip: wdq2wav version/help failed`（CI 内置探针使用 `--help/--version`，上游工具支持 `-h`；非阻塞）
- `L4_RESULT=pass: patches clean`
- `L5_RESULT=pass: bin/ has content`
- `Build Summary`: `Total: 1`, `Success: 1`, `Failed: 0`
- `test_package`: 成功编译并运行 `test_wdq2wav`，输出 `wdq2wav CLI help test: OK`

保留的非阻塞提示：
- 已新增软件级 `archives/w/wdq2wav/commands.json`，声明 `wdq2wav/1.0.0` 为可执行工具，满足 R38/L0k 门禁。
- 上游源码存在 2 个 `delete`/`new[]` 警告；未影响构建和消费者测试，本轮不扩大修复范围。
