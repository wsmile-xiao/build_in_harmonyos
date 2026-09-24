# shhmsg 1.4.2 适配笔记

## 编译环境

- 目标系统：HarmonyOS 6.0 PC aarch64
- 构建系统：Makefile
- 编译器：Clang 15.0.4
- Conan：OHOS 适配版 2.29.1
- 编译日期：2026-09-20
- 状态：built（真机验证通过，未上传）

## 上游与源码完整性

- 官方主页：https://shh.thathost.com/pub-unix/
- 官方源码包：https://shh.thathost.com/pub-unix/files/shhmsg-1.4.2.tar.gz
- 官方源码包 SHA256：`88c69e3f0b920b1ef93f6c10f354786f171d7cb3ab170a463bb9ab8bbf13a02b`
- 许可证：Artistic License 1.0（上游 README 的 License 节）

## 编译步骤

1. `source()` 下载并校验官方 1.4.2 源码包。
2. 将上游 Makefile、8 个 C 源文件及内部/公开头文件复制到独立构建目录。
3. 从 Conan `tools.build:compiler_executables` 获取 HarmonyOS Clang，显式覆盖上游默认 gcc 和编译参数。
4. 默认构建共享库；`shared=False` 时构建静态库。共享包用实体文件提供完整版本、SONAME 名和链接名。
5. Conan `test_package` 编译、链接并运行通用消费者测试和 HarmonyOS 专项测试。

## 适配问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 Makefile 默认调用 gcc | 旧构建脚本没有工具链配置接口 | 配方从 Conan 配置读取 C 编译器并显式覆盖 `CC`、`CCOPT` 和 `CCSHRD` |
| 2 | 上游共享库安装规则创建版本软链 | HMDFS 软链接行为不适合作为可复现包布局 | 保留版本库，并复制同内容的 `libshhmsg.so.1` 与 `libshhmsg.so` 实体别名 |

## 源码修改

无。库源码只使用标准 C/libc 接口，可直接在 HarmonyOS musl 环境编译运行；构建差异完全由 Conan 配方参数处理。

## 依赖版本

无第三方依赖；仅使用 HarmonyOS libc。Make、Clang 和 Conan 是构建工具，不作为运行时依赖传播。

## 上游测试账本

- 静态清点：发布包共 18 个文件；无 `tests/`、`test/` 目录，无测试源文件和测试框架配置。
- 构建入口清点：Makefile 只有构建、安装、清理和发布目标，没有 `check` 或 `test` 目标。
- 动态清点：真机执行 `make -n check` 和 `make -n test`，均报告没有对应目标。
- README 中“compiled and tested”仅为历史平台兼容性描述，不指向任何可执行测试套件。
- 上游实测测试数：0；不存在跳过、删除或修改的上游测试。

## 新增测试

- `test_shhmsg.c`：21 个断言，覆盖程序名默认值和路径提取、三个输出流的设置/恢复、错误前缀、普通消息、quiet 开关、强制名称前缀、verbose 级别、环境变量级别以及 `errno` 为零和非零的行为。
- `test_shhmsg_ohos.c`：4 个鸿蒙特有断言；编译期强制 `__OHOS__` 与 aarch64，运行期验证 LP64 ABI、OHOS 文件流重定向、UTF-8 消息字节保持以及系统 `strerror()` 与 `msgPerror()` 输出一致。
- 合计 25 个新增断言，严格不少于上游实测的 0 个测试，且包含独立鸿蒙特有测试。

## 交付物

- 默认共享构建：`lib/libshhmsg.so.1.4.2`、实体 `lib/libshhmsg.so.1` 与 `lib/libshhmsg.so`
- 静态构建选项：`lib/libshhmsg.a`
- 公开头文件：`include/shhmsg.h`
- 许可证材料：`licenses/README`

## 注意事项

- 本包是纯库，不安装命令行工具，因此不创建 `commands.json`。
- 上游没有正式自动化测试；测试数按静态与动态清点结果如实申报为 0，新增消费者测试不冒充上游测试。
- 本任务未提交、未推送、未创建或修改 PR。

---

**编译结束**: 2026-09-20 UTC
**最终状态**: built
