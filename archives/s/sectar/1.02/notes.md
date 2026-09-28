# sectar 1.02 适配笔记

## 编译环境
- 构建系统：上游 Autotools 1.4；实际构建直接由 Conan profile 的 OHOS clang 编译 6 个上游 C 源文件。
- 日期：2026-09-26；目标：OHOS/aarch64；宿主：Linux/x86_64；依赖：无第三方依赖。
- 上游源码：SourceForge star/sectar/1.02；SHA256 `81dca26f304e50d31d331349b18279179fc3da510ba3a7b5472346937b4dee76`。
- 许可证：COPYING 中 GPL-2.0-or-later；交付静态链接 CLI，不输出与系统同名的动态库。

## 上游测试清点（R51）
- 源码 6 个 `.c`，`tests/` 目录 0，`TESTS`/`check_PROGRAMS`/`add_test`/`pytest` 注册 0；`make -n check` 在旧 configure 失败后无 Makefile，不能执行；未把跳过写作通过。
- 上游用例：0；实跑 0；不存在可供修改的上游用例。`test_package` 新增真实消费者流程 1 例。

## 编译和错误
- 原始 `./configure --build=x86_64-pc-linux-gnu --host=aarch64-unknown-linux-ohos` 报 `Invalid configuration ... machine ... not recognized` 和 `ltconfig: you must specify a host type if you use --no-verify`。上游只有 CLI，不用 libtool 构建任何库：改用 Conan profile 的 `tools.build:compiler_executables.c` 直接编译 6 个源码文件，避免假报三元组、重生古董 configure 和依赖 autotools。
- `-std=gnu89 -Wno-implicit-function-declaration` 容纳 2001 年 C 写法；`VERSION` 由构建时定义为 1.02；静态链接让 x86 runner 的 `qemu-aarch64` 能直接运行交付产物。
- LP64 中 `long` 是 64-bit；原 `stword32` 声明违背名字且写入密文头。`0001-sectar-globaldefs.h.patch` 固定 `int32_t`，保留 32-bit 文件头。`0002-sectar-main.c.patch` 将 getopt 返回值从 `char` 改 `int`，保证 `EOF=-1` 不会在 unsigned-char 编译器中变成 255 使循环不结束；均无平台宏。
- 原加密格式只存块长不存明文长度；非整块明文解密尾部零填充，这是上游格式限制。消费者输入 C 源用空格补齐 32 字节整块，不声称支持无损解码任意长度文件。密码学不保证现代安全性，未新增安全特性。

## 测试（rule12）
- 手工交叉编译：`aarch64-unknown-linux-ohos-clang -static -std=gnu89 -Wno-implicit-function-declaration -DVERSION=\\\"1.02\\\" -I<sectar-src> <6个.c> -o /root/tmp/sectar-ohos`，返回 0；`qemu-aarch64 /root/tmp/sectar-ohos --version` 输出 `Sectar version 1.02`，退出 0。
- 32 字节明文 + 256-bit hex key 经 `qemu-aarch64 sectar -k key -e -o enc.star plain` 和 `-d -o dec enc.star`，`cmp plain dec` 退出 0；33 字节输入会增加零填充，已记录限制。
- `test_package/consumer.c`：由**安装的 sectar 包的 CLI** 加密消费者 C 源→解密生成 `roundtrip.c`→用 Conan OHOS profile 的 C 编译器静态编译→本机通过 qemu-aarch64 执行 `consumer`；验证完整密文往返、aarch64 32-bit 类型及可观测输出。实际 Conan W3 测试结果见 `reports/test-report.md`。鸿蒙特有消费者用例数：1。

## 知识草稿
- `E596-draft-88CF` 记录上游 CBC 格式缺失明文长度时非整块解密尾部零填充；`E483` 已涵盖本次无扩展名 SourceForge 下载 URL 的 Conan 误识别，不重复造条目。
- `finish` 内嵌 W3 本地 CI 完整通过（`w3-local-ci.log` 中消费者输出 `sectar OHOS aarch64 consumer OK`）。`finish` 总退出 1 来自非阻塞 G0 旧 configure 无法识别平台，以及 `gen_summary` 扫描本包之外的 `archives/q/qpdf/12.3.2{,.1}/manifest.yaml` 时的现存 `str`/list 解析异常；不改他人包或基础设施，不把总退出码写为 0。

## 交付
- 配方/源 hash/两处补丁/`test_package`/软件级 `commands.json`，无预编译二进制入仓。
---

**编译结束**: 2026-09-26 09:24
**最终状态**: built
