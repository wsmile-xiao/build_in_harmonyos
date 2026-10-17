# ctpv 1.1 HarmonyOS PC 适配笔记

## 软件与源码

- 上游仓库：https://github.com/NikitaIvanovV/ctpv
- 上游标签：`v1.1`
- 标签提交：`f70bee281917dfb6aedacecf06d4f791492e72da`
- 源码归档：`ctpv-1.1.tar.gz`
- SHA256：`29e458fbc822e960f052b47a1550cb149c28768615cc2dddf21facc5c86f7463`
- 许可证：MIT

## 构建配置

- 目标：HarmonyOS / OHOS 6.0，AArch64
- 编译器：OHOS Clang 15
- 构建系统：上游 Makefile
- 目标链接：静态 PIE，启用 NX、PIE、RELRO 与立即绑定
- 构建并发：`make -j1`
- 依赖：`libmagic/5.48`、`openssl/3.5.6.1`

ctpv 在构建时先编译并执行 `embed/embed`，把帮助文本和 shell 预览器转成 C 头文件。交叉编译时若该生成器也使用目标编译器，构建主机会尝试执行目标 ELF。补丁新增 `HOSTCC`，只让内嵌资源生成器使用宿主编译器；`ctpv` 和 `ctpvquit` 仍使用目标编译器。

运行时补丁让 FIFO 和 Kitty 状态文件使用 `${TMPDIR:-/tmp}`，并让默认 shell 使用 `SHELL` 或通过 `PATH` 查找 `sh`。这些修改不引入平台宏，Linux 与 OHOS 共用同一实现。

OHOS AArch64 默认 `char` 为无符号类型。上游词法器虽以 `int` 返回 `EOF`，随后却把返回值缩窄为 `char`，导致空配置文件末尾的 `-1` 变成 `255` 并被报告为非法字符。第二个补丁让字符读取链路一直使用 `int`，同时终止文件末尾无换行的注释扫描。这是 ISO C `fgetc` 风格的可移植修复，不改变有效字节的解析。第三个补丁让不含斜杠的 shell 名称由现有 `execvp` 通过 `PATH` 解析，同时仍用 `X_OK` 校验带路径的配置值。

`libmagic` 的静态库仍需要 `magic.mgc` 数据库。配方把依赖包中的数据库复制到 `share/misc/magic.mgc`，并在 Conan 运行环境中设置 `MAGIC`，保证 MIME 识别使用与链接库版本一致的数据。

## 上游测试清点（R51）

| 清点项 | 数量 | 证据 |
|--------|-----:|------|
| `tests/` 或 `test/` 目录 | 0 | 对官方 v1.1 归档执行 `find`，未发现测试目录 |
| 测试命名源码或脚本 | 0 | 全树文件清单仅含生产源码、构建辅助脚本和文档 |
| CTest/pytest/其他注册测试 | 0 | 上游不使用 CMake/pytest，也未包含测试框架 |
| `check`/`test` Make 目标 | 0 | Makefile 仅有 all/options/install/uninstall/clean/docs；`make -n check` 返回无目标 |
| **上游测试合计** | **0** | `ci/tools/extract_upstream_tests.sh` 同样报告无测试入口 |

上游基线为 0 个可运行测试入口，因此没有上游测试被修改、删除或跳过。适配后新增 12 个真实消费者断言，直接运行包内三个命令；其中 1 个为 HarmonyOS 专项 `TMPDIR` IPC 路径测试。

## 测试范围

消费者测试覆盖：三个安装命令存在性、版本、帮助、预览器列表、libmagic MIME 识别、文本预览、符号链接信息、错误路径、XDG 配置路径，以及 HarmonyOS 可写 `TMPDIR` 下的 IPC 状态文件。测试脚本输出 TAP 并严格校验 12 个断言。

## 补丁说明

六个补丁仅包含可移植性、确定性错误修复和命令行兼容性补充：

1. 将构建期生成器编译器与目标编译器分离；
2. 临时路径遵循 `TMPDIR`；
3. 默认 shell 不再硬编码 `/bin/sh`。
4. 词法器以 `int` 保存 EOF，避免无符号 `char` 目标将 EOF 误判为输入字节。
5. 允许默认的 `sh` 由 `PATH` 解析，并严格校验显式 shell 路径可执行。
6. 为现有短选项补充等价长选项，使命令发现和通用 smoke test 可直接使用 `--help`/`--version`。
7. 将依赖 `#!/bin/sh` 的 `ctpvclear` 包装脚本替换为 AArch64 原生启动器，保持 `id` 环境变量和首个参数的原有接口。
8. 为两个辅助命令增加 `--help` 和 `--version`，使赛事命令发现冒烟覆盖包内全部可执行文件。

补丁没有修改任何上游测试（上游没有测试文件），没有注入 `__OHOS__` 宏，也没有改变预览选择或正常输出语义。

---

**编译结束**: 2026-09-11
**最终状态**: built
