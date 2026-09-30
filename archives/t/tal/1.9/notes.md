# tal 1.9 适配笔记

## 编译环境
- 构建系统: makefile（上游手写 Makefile，无 configure）
- 编译日期: 2026-09-24
- 编译器: OHOS NDK clang 15.0.4（aarch64-unknown-linux-ohos），x86_64 构建机交叉编译
- 状态: built（conan-verify 与 finish W3 本地 conan create 通过；未上传制品仓）

## 上游概况
- 官方主页: https://thomasjensen.com/software/tal/（作者 Thomas Jensen，1.9 为最终版本，1999-03-11）
- 源码包 `tal-1.9.tar.gz` 仅 8 个文件：FILES、INSTALL、LICENSE、Makefile、tal.1、tal.c（1335 行 ANSI C）、tal-1.9.man.ps、tal19.txt
- 依赖: 无第三方依赖，只用 libc（stdio / stdlib / string / unistd / getopt）
- 许可证: 作者自拟的简短许可（允许自由使用与修改，要求在源文件开头注明原作者与改动），非 SPDX 标准许可 → `LicenseRef-tal`

## 编译步骤

配方 `build()` 在源码目录执行（命令行变量覆盖 Makefile）：

```bash
make -j1 tal CC=/data/service/hnp/bin/clang \
     CFLAGS='-O2 -Werror=implicit-function-declaration -static-pie'
# 展开为: clang -O2 -Werror=implicit-function-declaration -static-pie -o ./tal ./tal.c
```

`package()` 安装 `bin/tal`、`share/man/man1/tal.1`、`licenses/LICENSE`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 按上游 INSTALL 执行 `make linux`（`CC=gcc CFLAGS="-ansi -O"`），换成 OHOS clang 后只有 6 条 `-Wint-to-pointer-cast` 告警、看似编译成功，但二进制处理第一行输入即 SIGSEGV（qemu 退出码 139） | `-ansi` 定义 `__STRICT_ANSI__`，musl `features.h` 不再默认开启 `_BSD_SOURCE`/`_XOPEN_SOURCE`，`string.h`/`strings.h` 随之隐藏 `strdup()`/`strcasecmp()` 声明；C89 把它们隐式声明为返回 `int`，`(char *) strdup(...)` 的显式强转把 64 位堆指针截断为 32 位 | 不走平台目标，改用通用目标 `make tal` 并保持 clang 默认 C 方言（声明可见）；加 `-Werror=implicit-function-declaration`，同类回归直接编译失败。未改源码、无补丁 |
| 2 | 直接 `make`（不带目标）退出码 0，却不产出二进制 | `all: $(MAKE) $(OS)_tal`，构建机未设环境变量 `OS` 时落到 `_tal` 目标，只打印平台提示 | 配方显式指定 `tal` 目标 |
| 3 | 上游平台目标硬编码 `CC=gcc`，构建机无 gcc | 手写 Makefile 不感知交叉工具链 | R33：编译器取自 Conan `tools.build:compiler_executables`，经 make 命令行变量传入 |
| 4 | x86_64 构建机无法启动动态链接的 OHOS 产物（缺 `/lib/ld-musl-aarch64.so.1`） | 本机没有 aarch64 musl 动态加载器 | 交付产物用 `-static-pie` 链接（仍是 PIE，带 GNU_RELRO + BIND_NOW，栈不可执行）；同一产物在 AArch64 上原生运行、在 x86 上经 `qemu-aarch64` 运行，test_package 实跑的就是交付二进制本身。先例：ctpv/1.1、cutmp3/4（static-pie），whichman/2.4（-static） |

## 源码修改

无：`patches/` 为空，未改动上游任何文件。

## 依赖版本

无第三方依赖（`requirements()` 为空），W0 依赖发布检查无待查项。

## 上游测试清点（R51）

- 源码包只有上述 8 个文件：无 `test/`、`tests/` 目录，无测试源文件；Makefile 目标只有 `all`、9 个平台目标及其 `*_tal`、`$(BIN)/tal`、`_tal`、`clean`、`love`，**没有 `check`/`test` 目标** → 上游自动化测试 **0 个**（N = 0，N′ = 0）。
- 上游官方示例页 https://thomasjensen.com/software/tal/examples.html 给出 6 个示例、9 组「输入 / 命令 / 输出」，全部作为金样逐字节比对纳入 `test_package/test_tal.sh`。

## 适配后测试统计

| 类型 | 用例 | 断言 | 说明 |
|---|---|---|---|
| 上游测试 | 0 | 0 | 上游无测试（见上） |
| 消费者测试 `test_tal.sh` | 1 | 15 | 上游示例页 9 组金样 + 6 项 CLI 行为 |
| **鸿蒙特有测试** 消费者用例 `tal_consumer` | **1** | — | 完整构建流水线，见下 |

鸿蒙特有测试（N = 1）是一个完整的消费者用例：在 HarmonyOS PC 的构建流程里用 tal 格式化生成代码，再编译、运行依赖这段代码的程序。

1. `test_package/conanfile.py` 的 `build()` 生成一个参差不齐的 X-macro 头文件 `error_table.h.in`：1202 行，其中 `E_BLOB` 那一行长 3000 列。
2. 包内的 `bin/tal` 以 infile/outfile 方式把续行符对齐，输出 `error_table.h`。
3. CMake + OHOS 工具链以 tal 的输出为头文件，编译消费者程序 `tal_consumer.c`（static-pie）。
4. `test()` 运行 `tal_consumer`：程序检查它所依赖的头文件是否每个续行符都在同一列，然后使用编译进来的错误码表——1200 个码、取值之和，以及由 3000 列长行中字符串长度得出的 `E_BLOB`。期望值由生成器独立计算，经编译宏传入。

平台相关性：OHOS musl 的 `LINE_MAX` 为 4096，tal 按 `LINE_MAX` 分块读行。换成 `LINE_MAX=2048`（glibc 取值）的 tal 构建，会把长行拆成两行，宏续行随之断开，消费者程序直接编译失败。

负向对照（本地按同一流水线手工重放）：

| tal 构建 | 结果 |
|---|---|
| `LINE_MAX=2048` | 编译失败 |
| 上游 `-ansi` | tal 自身 SIGSEGV |
| 跳过 tal、直接用未对齐头文件 | 程序报 1161 行续行符未对齐并返回 1 |

## 验证结果

```bash
# conan-verify: conan create -pr:h/-pr:b ci/conan/profiles/ohos-aarch64（本机 x86_64 + qemu-aarch64）
G1 / G2 / G3 / G4 PASS，编译零告警
tal consumer: header 1201 continuation lines aligned at column 3002   # 鸿蒙特有消费者用例
tal consumer: 1200 error codes, value sum 599971, E_BLOB=2971
tal consumer: OK
TAL_TEST_SUMMARY pass=15 fail=0 total=15         # test_tal.sh，实跑交付产物 bin/tal

# 交付产物属性
bin/tal: ELF 64-bit LSB pie executable, ARM aarch64, static-pie linked
FLAGS BIND_NOW, FLAGS_1 NOW PIE, GNU_RELRO, GNU_STACK RW（不可执行栈）

# 负向对照（同一 test_tal.sh）
上游 make linux 口径（-ansi -O）构建的产物: pass=4 fail=11（11 项 SIGSEGV）
产物缺失: 立即 FAIL（与 CI L1e 破坏性反向验证一致）
```

## 注意事项

- test_package 在非 AArch64 运行器上依赖 `qemu-aarch64`；缺失时测试失败，不会静默跳过。
- 本地验证在 x86_64 + qemu-aarch64 上完成，未在 HarmonyOS 真机实跑；真机结果以 PR CI 为准。
- 未在 Windows/macOS 验证（`validate()` 限定 Linux/OHOS）。

## 对话记录

### 对话 #1 — 2026-09-24

- W0：无第三方依赖；lang-preflight 判定主体为 C（与 cpp 任务兼容）；仓库无 tal 历史归档。
- 手工交叉编译：上游 `make linux` 口径（`-ansi -O`）产物运行即 SIGSEGV，定位为严格 ANSI 隐藏 POSIX 声明导致的 64 位指针截断；改通用目标 `make tal` + 默认 C 方言后功能正常。
- 从上游示例页抽取 9 组输入/输出金样写入 test_package，并用 `-ansi` 口径产物做负向对照（4/15）确认测试能拦住该缺陷。
- conan-verify 与 finish W3 本地 conan create 均通过，test_package 实跑交付产物 15/15；新增知识草稿 E585-draft-04E7。

### 对话 #2 — 2026-09-25

- PR 评审 rule12 不通过：适配后统计中「鸿蒙特有测试」为 0。
- 先补了检查脚本 `test_tal_ohos.sh`。审核人在群内指出新增测试不能只是断言，因此改为上面的完整消费者用例：tal 格式化生成代码 → OHOS 工具链编译消费者程序 → 运行。原脚本删除。conan-verify 与 finish W3 本地 conan create 通过：消费者 OK，test_tal.sh 15/15。
---

**编译结束**: 2026-09-26 04:06
**最终状态**: built
