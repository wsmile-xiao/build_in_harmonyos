# libytnef 2.1.2 HarmonyOS 适配笔记

## 适配摘要

- autotools（autogen.sh/configure.ac + libtool），tag tarball **不含生成的 `configure`**：`build()` 先 `autoreconf -fi`（`automake/1.18`、`libtool/2.5.4` 经 `tool_requires` 声明，保证 CI worker 也有工具链）。
- **E007/E072**：生成的 `config.guess` 没有 HarmonyOS 分支；且 `config.guess` 与 `config.status` 都用 `umask 077` 建 `mktemp -d`，HMDFS 下该目录对创建者不可写——`dummy.c` / `subs1.awk` 报 `Permission denied`。配方在 configure 前把生成的 `configure`、`config.guess` 里的 `umask 077` 归一化为 `022`（保留真实临时目录创建），并显式传 `--build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos`（生成的 `config.sub` 已认 `ohos*`），完全跳过平台猜测；build == host 仍按原生构建处理，`AC_RUN_IFELSE` 探针照常执行。
- **jobserver FIFO**：`make -j2` 在 OHOS 报 `jobserver mkfifo ... Operation not permitted`，构建改为单 job（`autotools.make(args=["-j1"])`）。
- 产物：`libytnef.so`/`libytnef.a` + 头文件 + `libytnef.pc` + 上游命令行工具 `ytnef`、`ytnefprint`（软件级 `commands.json` 已按 R38 声明）。
- 构建为 out-of-source：`source_folder = <cache>/b/src`、`build_folder = <cache>/b/build-release`。上游测试脚本用相对路径 `../ytnef/ytnef` 驱动可执行文件，因此测试在 **build 树** 的 `test-data/` 下运行（把源码里的样例与期望结果 `results/` 拷入其中）。

## 上游测试口径（五维账本）

| 维度 | 数量 | 证据 |
|---|---|---|
| N_static（上游静态声明） | 7 项校验 | `test-data/test.sh`：1 次附件抽取 + `diff results data`（winmail.dat 与全部 `*.tnef` 样例，对照仓库内提交的期望结果），加 6 次 `ytnefprint` 字段断言（PR_MESSAGE_DELIVERY_TIME、PR_TNEF_CORRELATION_KEY、PR_RTF_SYNC_BODY_CRC、PR_RTF_SYNC_BODY_COUNT、PR_RTF_COMPRESSED、以及畸形流 `ytnef-oob-TNEFVersion-SwapWord` 的 `ERROR: Field with size of 0`） |
| N_registered（构建系统注册） | 0 | 上游 autotools **没有注册 TESTS**（`make check` 的 TESTS 列表为空，根 `Makefile.am`/`test-data/Makefile.am` 仅有 `SUBDIRS` 与 `EXTRA_DIST`）；`test.sh` 是其唯一可执行测试入口，按 R51 在 `build()` 内真实执行 |
| N_executed（实际执行） | 7/7 | `set -ex` 追踪：`+ diff results data` 1 次、`+ grep -A …` 6 次，脚本退出码 0 |
| 未执行/跳过 | 0 | 无 |
| N_consumer（消费者测试） | 1 个程序 / 8 组断言 | `test_package/test_package.c`：`TNEFParseFile()` 解析随包样例 `one-file.tnef`，断言流版本、主题（one-file）、消息类（IPM.Microsoft Mail.Note）、Message-ID、附件列表与载荷字节数、解码出的 MAPI 属性数量，逐项返回独立非零码；样例以上游 `test-data/one-file.tnef` 的 base64 文本形式随包（`one-file.tnef.b64`，`test()` 内解码后传入），避免二进制文件使 CI 的 `git apply` 检出失败 |

## 验证摘要

- `conan-verify`：PASS（G0–G4 + L2/L4/L5）
- 上游测试：**7/7 通过**（`sh test-data/test.sh` rc=0）
- 消费者测试：**1/1 通过**
- W3 本地 CI 模拟（`finish` step [5/10]）：PASS
- 分支基线：`feat/libytnef-2.1.2` 从 `upstream/main`(576aa6e6a1) 切出

## 路径判断

**纯路径 A。** 理由：本次的坑（config.guess 不认 HarmonyOS、`umask 077` 临时目录在 HMDFS 不可写、`make -jN` jobserver FIFO 不可建）在仓库知识库均有对应条目（E007/E072/E011/E114）与既有配方先例，处理方式是既有经验的直接应用；「上游无 autotools TESTS、在 build() 内跑其脚本」也已是 SKILL R51 的既定做法。未产生可跨仓库复用的新增知识，故不申报路径 B。

---

**编译结束**: 2026-09-16 00:5x
**最终状态**: built
