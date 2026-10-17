# oflib 0git20070620 HarmonyOS PC 适配笔记

## 源码与构建

- 上游快照日期：2007-06-20。
- 上游仓库现已不可访问，使用 Ubuntu 官方归档中与 Debian 签名 `.dsc` 校验值完全一致的原始 tarball。
- SHA256：`944bb57801eba6bc12e74bde077ec2e601aa216e315a5031c8f4f2b8db353d49`。
- 构建系统：原始 Makefile；配方使用 Conan profile 指定的 Clang，复现上游三源文件共享库构建。
- 第三方依赖：无；W0 依赖预检通过。

## 适配修改

1. `of_api.h` 补充 `<limits.h>`，使 HarmonyOS musl 环境中的 `PATH_MAX` 可见。
2. 将头文件中的全局变量改为 `extern`，并在 `of_externals.c` 中提供唯一实体定义，修复现代 Clang 默认 `-fno-common` 下的重复符号错误。
3. 不执行上游硬编码 `gcc`、`/usr/local` 和 `ln -s` 的安装规则；Conan 在私有包目录安装头文件和共享库，并用实体文件提供 `libofapi.so.0`、`libofapi.so` 名称。

## 上游测试四维账本（R51）

| 项目 | 数量 | 证据 |
|------|-----:|------|
| 上游正式测试静态声明 | 0 | 源码无 `tests/`/`test/` 目录，无 `TESTS`、`check` 目标、测试框架或 CI 配置 |
| 上游正式测试实际执行 | 0 | 上游未提供可执行测试入口 |
| 上游示例程序 | 3 | `example/example.c`、`ramtest.c`、`soundbus.c`；均为硬件设备树演示，不属于自动化测试 |
| 适配后注册场景 | 4 | uint32、uint64、合成设备树、HarmonyOS PC 平台测试 |
| 适配后实断言 | 37 | 32 个公共 API/文件系统断言 + 5 个 HarmonyOS PC/AArch64 断言 |

上游测试源码未被修改。适配新增测试使用真实 `libofapi` API，不将示例程序或新增消费者测试冒充上游测试。

## 测试范围

- 大端 32/64 位设备树属性转换、索引和越界行为。
- 在可写工作目录构造合成设备树，验证根目录设置、按路径找节点、名称/类型加载、属性存在性和属性读取。
- HarmonyOS 特有测试在运行时确认 `uname=HarmonyOS`、`machine=aarch64`、64 位 ABI，并调用打包后的公开 API。

## 常见合入问题自查

- 仅修改 `archives/o/oflib/0git20070620` 及软件级元数据；无预编译二进制、源码压缩包或临时文件入仓。
- 源 URL 为 HTTPS 权威归档，SHA256 完整；补丁与 `conandata.yml` 一一对应。
- 补丁只修改源文件，不含 `__OHOS__` 平台宏，不改生成文件。
- `test_package` 真实链接并运行被测库，不使用空壳、跳过或伪造上游通过率。
