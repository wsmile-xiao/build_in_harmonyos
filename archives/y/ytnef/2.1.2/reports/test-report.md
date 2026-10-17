# ytnef 2.1.2 测试报告

> **项目**: ytnef 2.1.2（Yerase's TNEF Stream Reader）
> **测试日期**: 2026-09-18
> **测试环境**: HarmonyOS PC，HongMeng Kernel 1.12.0，aarch64（clang 15.0.4 / os=OHOS / armv8）
> **测试类型**: 上游官方集成测试套件（`test-data/test.sh`）+ conan test_package 消费者测试

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 上游总测试数 | 8 | 100% |
| 上游通过 (PASS) | 8 | 100% |
| 上游失败 (FAIL) | 0 | 0% |
| 上游跳过 (SKIP) | 0 | 0% |
| test_package 断言 | 8 | 100% |
| test_package 通过 | 8 | 100% |
| CLI 冒烟（ytnef/ytnefprint -h） | 2 | 100% |

**核心功能通过率**: ✅ **100%（18/18）**

---

## 二、测试结论

### 2.1 总体评价

✅ **通过。** 上游唯一测试套件 `test-data/test.sh` 的 8 组校验在 HarmonyOS PC 上全部通过，
逐字节附件比对无差异；`conan create` 的 test_package 消费者测试（链接 libytnef 的真实 API 调用）
8/8 通过，已安装的 `ytnef` / `ytnefprint` 命令行工具均可正常执行。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| config.guess 无 HarmonyOS 分支（E007） | configure 无法确定构建三元组 | 🟡（已解决） |
| HMDFS 下 `umask 077 && mktemp -d` 目录不可写（E114） | config.status 无法生成 Makefile | 🟡（已解决） |
| conan automake 包装脚本与 conan perl ABI 不匹配 | autoreconf 无法启动 | 🟡（已解决） |
| make jobserver FIFO 被禁（E074） | `make -j>1` 告警 | 🟢（`-j1` 规避） |

### 2.3 可用功能清单

```
✅ libytnef: TNEF 签名识别、TNEFParseFile/TNEFParseMemory 解析、附件枚举、RTF 解压
✅ ytnef    : 命令行附件/正文提取（-f/-F/-H/-v/-s/-a/-h）
✅ ytnefprint: MAPI 属性打印（PR_MESSAGE_DELIVERY_TIME、PR_TNEF_CORRELATION_KEY 等）
⚠️ ytnefprocess: 上游 perl 脚本（硬编码 /usr/bin/ytnef，依赖 MIME::Parser 等 CPAN 模块，上游原样安装，CI 不执行）
```

### 2.4 已知限制

1. `ytnefprocess` 是上游遗留 perl 脚本，硬编码 `$reader = "/usr/bin/ytnef"` 且依赖 `MIME::Parser` /
   `Mail::Mailer` 等 CPAN 模块；本包按上游 `make install` 原样安装，未做改动，也未在 CI 中执行。
2. 默认 `shared=False`（静态，与仓库 autotools 模板一致）；需要共享库时用 `-o ytnef/*:shared=True`
   可产出 `libytnef.so.0.0.0`（libtool 默认同样支持）。

---

## 三、测试详情

### 3.1 上游测试（test-data/test.sh，8 组断言全通过）

| # | 测试项 | 功能 | 结果 |
|---|--------|------|------|
| 1 | `ytnef -f data winmail.dat` | 提取 winmail.dat 附件（zappa_av1.jpg、bookmark.htm） | ✅ PASS |
| 2 | `ytnef -f data *.tnef`（6 个夹具） | 提取 one/rtf/long-filename/missing-filenames/multi-value-attribute 附件，共 13 个 | ✅ PASS |
| 3 | `diff results data` | 与 `test-data/results/` 逐字节比对 | ✅ PASS（无差异） |
| 4 | `PR_MESSAGE_DELIVERY_TIME` | 值 = `Tuesday June 17, 2003 3:23:00 pm` | ✅ PASS |
| 5 | `PR_TNEF_CORRELATION_KEY` | 值 = `[00000000CFF233DD7623274EB78A4912C247A0E464532700.]` | ✅ PASS |
| 6 | `PR_RTF_SYNC_BODY_CRC` | 值 = `872404792` | ✅ PASS |
| 7 | `PR_RTF_SYNC_BODY_COUNT` | 值 = `90` | ✅ PASS |
| 8 | `PR_RTF_COMPRESSED` | 含 `\pard Casdasdfasdfasd\par`（grep 打印 `stray \ before p` 警告，属上游脚本固有） | ✅ PASS |
| 9 | 畸形输入 `ytnef-oob-TNEFVersion-SwapWord` | 断言输出 `ERROR: Field with size of 0` | ✅ PASS |

### 3.2 test_package 消费者测试（8 断言全通过）

| 测试项 | 功能 | 结果 |
|--------|------|------|
| fixture one-file.tnef 可读 | 上游夹具随包分发 | ✅ PASS |
| `TNEFCheckForSignature(fixture 前 4 字节)` | 签名识别（真值） | ✅ PASS |
| `TNEFCheckForSignature(0)` | 签名识别（假值拒绝） | ✅ PASS |
| `TNEFParseFile("one-file.tnef")` | 端到端解析（返回 0） | ✅ PASS |
| 附件链表非空 | 解析器填充 `starting_attach` | ✅ PASS |
| 附件名 = `AUTHORS` | 标题解码正确 | ✅ PASS |
| `messageClass` = `IPM.Microsoft Mail.Note` | 消息类解码正确 | ✅ PASS |
| `TNEFInitialize()` 空链表 | 结构体生命周期 | ✅ PASS |
| `ytnef -h` / `ytnefprint -h` | 已安装 CLI 可执行（退出码 0） | ✅ PASS |

### 3.3 失败的测试

无。

### 3.4 跳过的测试

无（上游测试套件与 test_package 均完整执行）。

---

## 四、关键问题分析

### 问题1: configure 无法识别 HarmonyOS（E007）

**现象**：
```
./config.guess: unable to guess system type
configure: error: cannot guess build type; you must specify one
```
`uname -m = aarch64`、`uname -s = HarmonyOS`、`uname -r = HongMeng Kernel 1.12.0`。

**根因分析**：GNU config.guess 无 HarmonyOS 分支。直接后果是 configure 无法确定 build/host 三元组；
同时 config.guess 的编译器探针用 `mktemp -d`（umask 077）建临时目录，在 HMDFS 上得到不可写的
`drwx--S---`，追加 `Permission denied`。

**解决方案**：在 `autoreconf` 之后向生成的 config.guess 注入 `*:HarmonyOS:*:*)` → 输出
`${MACHINE}-unknown-linux-ohos`；该分支不进入 Linux/GNU 段，因此无需 `__OHOS__` LIBC 探针，
规避平台宏红线。未使用 `--build/--host`（E205 禁止）。实测 configure 打印
`checking build system type... aarch64-unknown-linux-ohos`、`checking whether we are cross compiling... no`。

### 问题2: config.status 无法建立临时目录（E114）

**现象**：
```
./config.status: line 819: ./confmAOPle/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
```

**根因分析**：HMDFS 把 mode 0700 的目录变成 `drwx--S---`（setgid、属主亦不可写）。系统 autoconf
生成的 config.status 走 `umask 077 && mktemp -d "./confXXXXXX"` 通用分支即失败。注意 `mkdir`（umask 077）
得到 `drwxrws--x` 可写，只有 `mktemp -d` 得到不可写的 `drwx--S---`。

**解决方案**：运行 configure 前删除生成脚本里的 `umask 077`（configure 与内嵌的 config.status 模板一并覆盖），
与 abiword-plugin-*、abook 同款处置；不改动任何上游源码。

### 问题3: autoreconf 侧 perl ABI 冲突

**现象**：
```
Can't load Cwd.so for module Cwd: Permission denied / Error relocating Cwd.so: Perl_my_cxt_init: symbol not found
```

**根因分析**：conan `automake/1.18` 的 `aclocal`/`automake` 包装脚本 shebang 指向系统 perl（5.42.0），
而 `VirtualBuildEnv` 的 `PERL`/`PERL5LIB` 指向 conan perl（5.42.2 thread-multi），两套 perl 模块混用。

**解决方案**：引导阶段统一使用系统 perl，并把 conan automake 的 `share/automake-*` 加入 `PERL5LIB`
（`Automake/Config.pm` 所在），全链路 perl 一致。

---

## 五、测试环境

```
$ ytnef -h
Yerase TNEF Exporter v2.1.2

$ conan create archives/y/ytnef/2.1.2 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
[settings] os=OHOS os.version=6.0 arch=armv8 compiler=clang compiler.version=15
           compiler.libcxx=libc++ compiler.cppstd=17 build_type=Release
[conf]     tools.build:compiler_executables={c: /data/service/hnp/bin/clang, cpp: /data/service/hnp/bin/clang++}
[tool_requires] automake/1.18, libtool/2.5.4
```

---

*报告生成时间: 2026-09-18*
