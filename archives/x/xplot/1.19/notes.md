# xplot 1.19 HarmonyOS PC 移植记录

## 编译环境

- 目标设备：HarmonyOS 6.0，aarch64（Conan `OHOS` / `armv8`）
- 构建系统：Makefile
- 编译器：设备工具链 clang/clang++ 15
- Conan：2.29.1
- 编译日期：2026-10-02
- 状态：built
- 源码：Ubuntu 官方归档中的上游 `xplot_1.19.orig.tar.gz`
- 源码 SHA-256：`aded1c33dc8393c02d95d5fe4b5c7c7c8289a8c3aa74706af1a962b95518277d`

## 编译步骤

在 HarmonyOS 设备上使用仓库的 `ci/conan/profiles/ohos-aarch64` 配置执行 Conan 原生构建。Conan 下载并校验上游源码，使用已发布的 `libforms/1.2.4` 依赖，并在设备上编译、打包及签名：

```sh
SSL_CERT_FILE=/system/etc/ssl/certs/cacert.pem \
conan create archives/x/xplot/1.19 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=xplot/1.19
```

证书环境变量指向设备系统 CA，用于验证 HTTPS 源码下载。没有关闭 TLS 校验。传给 `conan create` 的 profile 在本次执行中复制到设备临时工作目录。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | bundled `libfli` 子构建忽略 Conan 编译器并重置编译选项 | 上游 `cbuild` 和 `cbuild.def` 写死 `g++`、`gcc` 与系统头文件路径 | 补丁保留调用方 `CC`，并从 Conan 传递依赖头文件和编译器设置 |
| 2 | `cbuild` 在 HarmonyOS 上无法加载定义文件，临时文件也写入系统 `/tmp` | shell 不会从当前目录搜索 `cbuild.def`；HarmonyOS 构建应使用构建目录临时区 | 使用显式 `./cbuild.def`，并将临时文件放在 Conan 构建目录的 `TMPDIR` |
| 3 | `libforms/1.2.4` 没有上游使用的 `<X11/forms.h>` 路径 | Conan 依赖安装的是 `<forms.h>` | 在 Conan 私有构建目录生成兼容头文件，不修改上游源码或系统路径 |
| 4 | 打包后的帮助文件不在上游硬编码目录 | Conan 包安装到独立 package folder | 程序从 `XPLOT_HELPFILE` 读取帮助文件路径，Conan 运行环境提供该变量 |
| 5 | 上游 GUI 测试需要交互式 XForms 窗口 | SSH 会话没有 `DISPLAY` 或 X server | 跳过 4 个窗口测试；Conan 消费者测试执行真实二进制的参数解析错误路径，该路径在初始化 XForms 前返回 |

## 源码补丁

- `patches/0001-libfli-lib-cbuild.patch`：使 bundled `libfli` 尊重 Conan 工具链、头文件和临时目录，并修正 shell 文件路径处理。
- `patches/0002-src-dohelp.c.patch`：允许从 `XPLOT_HELPFILE` 查找安装后的帮助文件。

## 发现与知识

- ✅ bundled `libfli` 的 `cbuild` 脚本必须保留 Conan 传入的编译器和依赖头文件，并从构建目录读取 `TMPDIR`；处理方式见 `patches/0001-libfli-lib-cbuild.patch`。
- ✅ `libforms/1.2.4` 将 `forms.h` 安装在 `include/`，而 xplot 1.19 使用 `<X11/forms.h>`；私有兼容头在 `conanfile.py` 的 build folder 中生成。
- ✅ 缺少 `-format` 参数会在 XForms 初始化前返回，可用真实已安装程序在无 `DISPLAY` 会话测试；实现见 `test_package/test_xplot.py`。

## 依赖版本

- `libforms/1.2.4`，其 Conan 闭包由设备 Conan cache 中已发布的包提供。

## 验证结果

- 原生 HarmonyOS AArch64 `conan create`：通过，退出码 0。
- Conan 消费者测试：通过。测试运行已安装的 `xplot` 可执行文件，确认 `DISPLAY` 未设置时 `xplot -format` 以退出码 1 返回预期诊断 `missing format string after -format flag`。
- 鸿蒙特有检查：通过。测试确认内核名为 `HarmonyOS`、ELF machine 为 AArch64，并且签名后的可执行文件包含一个 `.codesign` 段。
- 最近一次仓库 CI 构建包标识：recipe revision `7af67fef2e3c593d5821cb9dc61e5384`，package ID `47e0b84c22b930844f5db4ffeb6e9c8723264f52`，package revision `56f1fbe053a683708c902668c97dcbb9`。
- 仓库 W3 本地 CI：通过，退出码 0；目标包 1 个，成功 1 个，失败 0 个。L0、L1、L4、L5 通过；L2 因 `--version`/`--help` 在无图形会话失败而跳过。`.ci-result.json` 由 `finish` 流程生成，`reports/w3-local-ci.log` 的 SHA-256 与其记录一致。
- `finish` 最终返回 1：全仓库 W5 还报告既有知识条目 E219、E253、E305 的 4 个必填字段为空；542 个文档与 KV 配对完整，知识图谱校验通过（有 170 条非阻塞告警）。xplot 自身的知识检查通过并生成 `.knowledge-done`，没有修改这些无关条目。
- 归档就绪检查尚未完成：本次没有单独的 staging 目录或 release/debug tarball，因此 `.staging-verified` 和 `packaging/` 未生成。Conan W3 结果仍为通过，不能将其解释为这两类归档产物已交付。
- 上游 `make tests` 清点：注册 4 个交互场景，本次执行 0、通过 0、失败 0、因无图形会话跳过 4。未将参数解析测试描述为绘图或窗口渲染验证。
- 编译有上游旧代码告警，包括 `void main` 等声明；构建和消费者测试成功。

## 交付物

Conan 在设备本地缓存中生成并签名了 `bin/xplot`，同时打包帮助文件、man page 和 GPL 许可证。版本归档目录交付可复现的 Conan 配方、补丁、消费者测试及验证记录。

## 注意事项

xplot 依赖 XForms/X11 显示服务器完成绘图。当前设备没有 X11 display，因此本次验证不覆盖窗口创建、交互或实际绘图显示。

## 对话记录

### 对话 #1 [2026-10-02]

- 目标：在 `upstream/main` 基线上创建 `feat/xplot-1.19`，并将 xplot 1.19 移植到 HarmonyOS PC。
- 操作：使用 Conan 原生 AArch64 profile 构建 xplot，执行消费者测试和仓库 W3 CI。
- 结果：Conan 消费者测试及 W3 CI 通过；图形测试因设备没有 X11 display 跳过，归档 staging/打包产物未生成。
---

**编译结束**: 2026-10-02 22:52
**最终状态**: built
