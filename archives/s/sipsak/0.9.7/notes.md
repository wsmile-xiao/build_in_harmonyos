# sipsak 0.9.7 HarmonyOS PC 适配说明

## 源码

- 版本：0.9.7
- 来源：官方 GitHub Release（nils-ohlmeier/sipsak 0.9.7）
- 校验：`conandata.yml` 中固定 SHA-256

## 构建方式

配方不运行旧版 Autotools，而是使用 Conan 构建环境中的 C 编译器直接编译命令行程序所需的源文件。这样不依赖 OHOS CI 中缺失的 Autotools 工具，也不会触发 `config.guess`、`config.sub` 或 `configure` 在 HMDFS 上的问题。
主要兼容选项：
- `-D_GNU_SOURCE`：声明 musl 提供的 GNU 扩展接口。
- `-fcommon`：保持 sipsak 0.9.7 旧源码中 tentative definitions 的链接语义。
- 显式 `HAVE_*` 和包版本宏：替代 `configure` 生成的配置头。
- Conan build-type 标志：分别支持 Debug、Release、MinSizeRel 和 RelWithDebInfo。

当前配方不修改上游源码，因此没有应用补丁。

## 测试

上游 0.9.7 发布包包含两个基于 Check 框架的单元测试源文件：
- `tests/check_helper.c`（5 个用例）
- `tests/check_md5.c`（2 个用例）

OHOS 环境未提供 Check 框架。为避免跳过上游测试，配方内置了一个最小化的 Check 兼容层（`files/check.h` + `files/check_shim.c`），只实现上游测试用到的 Check API 子集（Suite/TCase/SRunner/fail_unless 等），上游测试源码不做任何修改。构建阶段会用该兼容层编译并执行 `check_helper` 与 `check_md5` 两个测试程序，共 7 个用例全部真实运行；任一用例失败会使构建失败。

`test_package/test_sipsak.sh` 使用 Bash 严格模式验证安装后的可执行文件存在，并确认 `sipsak --version` 输出版本 0.9.7。