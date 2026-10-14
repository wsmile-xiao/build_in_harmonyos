# libspectre 旧版 config.guess 在 HarmonyOS PC 上的规避与构建三元组指定

> 草稿 ID：`DRAFT-LIBSPECTRE-0.2.12-HARMONYOS-CONFIG-GUESS`
> 来源任务：OHPCD DEP #13639（libspectre 0.2.12）
> 知识库议题：[Issue #3570](https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3570)
> 来源 PR：[PR #13738](https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/13738)

## 适用场景

旧版 GNU Autotools 项目随源代码携带过时的 `config.guess`，在 HarmonyOS PC 上运行 `configure` 时可能因设备 shell 对旧脚本分支的解析而失败。libspectre 的 CI 日志显示，GNU triplet case 分支返回 `syntax error near unexpected token ')'`，随后 configure 无法猜测 build type。

## 现象与原因

- 旧 `config.guess` 的 case 分支在 HarmonyOS PC shell 上发生解析错误，不能可靠提供构建三元组。
- 继续给旧脚本增加 case 分支可能在后续 triplet 表遇到同类解析问题。
- libspectre 的 Conan build 与 host profile 都是 HarmonyOS AArch64；明确传递 Autoconf `--build` 三元组即可避免自动执行旧 `config.guess`。

## 处理方法

1. 通过 `AutotoolsToolchain.configure_args` 显式传入 `--build=aarch64-unknown-linux-musl`，令 configure 跳过自动运行 `config.guess`。
2. 先运行发行包的 `config.sub aarch64-unknown-linux-musl`，确认 `config.sub` 接受该三元组。
3. 保持上游配置脚本不变，减少对旧 shell 语法和脚本内 case 表的依赖。
4. 若现有 Ghostscript 包只有 `gs` 命令，先构建带共享 API 的 Ghostscript 依赖包：同一 10.07.1 源码执行上游 `make so` 与 `make soinstall`，并安装 `psi/iapi.h` 到 `include/ghostscript/iapi.h`。
5. 在独立 Conan 缓存中验证 `libgs.so` 与 `iapi.h`，再以 HarmonyOS PC Conan 构建确认 libspectre configure、编译、上游检查及真实 Ghostscript 渲染完整通过。

## 验证与边界

- 2026-10-04 在隔离缓存 `CONAN_HOME=$HOME/work/psj/ch-gs14845` 用已构建的 `ghostscript/10.07.1.1`（依赖 PR #14671）重跑：`conan create` 退出码 0。configure 接受 `aarch64-unknown-linux-musl`，`gsapi_new_instance in -lgs` 与 `libgs >= 9.53.0` 均为 yes。上游 `make check -j1` 输出 `Nothing to be done for 'check'`，计数 0/0。消费者 4/4（`HARMONYOS_TESTS=4/4`）。日志 `$HOME/work/psj/ls13639/create.log`。
- 另外两处才会让这条链路走完：构建期把 ghostscript 的库目录放进 `LD_LIBRARY_PATH`（否则链接了 libgs 的配置探测程序找不到 soname）；`configure` 临时目录 `umask 077` 改为 `022`；离树编译增加 `-I$(top_srcdir)`。
- 消费者测试使用真实 PostScript 文档，经 libspectre 调用 Ghostscript 并校验页面渲染结果。
- 此三元组适用于 OHOS AArch64/musl 目标。若 Conan build profile 与 host profile 不同，需按实际构建机设置 build triplet，不能照抄目标三元组。

## 关系

- 适用组件：旧版 GNU Autotools 项目；`config.guess` 不兼容且 configure 支持显式 `--build` 时。
- 依赖：HarmonyOS PC AArch64 工具链；本包运行时依赖带 `libgs.so` 和 `include/ghostscript/iapi.h` 的 Ghostscript 包。
- 验证记录：以 OHPCD #13639 对应 PR 的最新机器人 CI 与 test_package 结果为准。
