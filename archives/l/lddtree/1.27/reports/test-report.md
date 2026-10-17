# 测试报告 — lddtree 1.27

> **项目**: lddtree
> **测试日期**: 2026-09-15
> **测试环境**: HarmonyOS HongMeng Kernel 1.11.0 aarch64 (OHOS 6.0, armv8, clang 15, libc++)
> **测试类型**: 上游官方测试套件（ATF 风格，13 用例）+ 消费者视角测试（test_package）

---

## 一、测试摘要

### 1.1 上游官方测试套件（`make -r check`）

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 总测试数 | 13 | 100% |
| 通过 (PASS) | 13 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |

**上游测试通过率**: ✅ **13/13（100%）**

断言级实测：**`ASSERTIONS: total=21 failures=0`**，进程退出码 **0**。

### 1.2 适配后新增测试（test_package 消费者视角）

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 断言总数 | 38 | 100% |
| 通过 | 38 | 100% |
| 失败 | 0 | 0% |

**新增测试通过率**: ✅ **38/38（100%）**

**合计**: 51 项全部通过（13 用例 + 38 断言）。

---

## 二、测试结论

### 2.1 总体评价

✅ **通过** — 上游全部 13 个用例在本平台真实执行并全部通过，无跳过、无豁免；
消费者测试对打包产物发起的 38 条断言全部通过；破坏性反向验证证明测试非空转。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| 上游测试驱动依赖 ATF/kyua（本平台不存在） | 无法直接运行 `make check` | 🟡 已由 patch 0002 解决（新增自带 ATF 兼容层，上游测试文件未改） |
| 工具运行时依赖外部 `getopt`（本平台不存在） | 所有选项解析失败 | 🟡 已由 patch 0001 解决（改为 POSIX shell 解析） |
| 运行时缺少 ELF 解析后端 | 工具无法解析任何依赖 | 🟢 已由 `requires(binutils/2.46.0)` 解决（runenv 注入 PATH） |
| CI L4 门禁误报 | 无功能影响 | 🟢 误报（详见 4.4），非阻塞 |

### 2.3 可用功能清单

```
✅ 树状依赖输出       lddtree.sh /bin/sh
✅ 扁平输出           lddtree.sh -l /bin/sh    （每行一个绝对路径）
✅ 显示全部重复依赖   lddtree.sh -a /bin/sh
✅ 调试跟踪           lddtree.sh -x /bin/sh
✅ 指定根目录解析     lddtree.sh --list --no-auto-root --root <dir> <elf>
✅ 符号链接链解析     （上游相对 pax-utils 版本的增强点）
✅ 版本/用法输出      -V / -h / --version / --help
✅ 错误处理           缺失文件、目录入参、非法选项、缺后端均给出诊断并非零退出
✅ 多目标分析         lddtree.sh file1 file2 ...
```

### 2.4 已知限制

1. 本平台无 `scanelf`（pax-utils 未适配），后端固定为 binutils（`objdump` + `readelf`）。
   上游代码保留 scanelf 路径，若将来发布 pax-utils 会自动优先使用。
2. 仅支持 ELF 目标（与上游一致）；非 ELF 文件不会被解析。
3. `lddtree.sh` 是 shell 脚本，不产生 ELF 产物，因此 CI 的 L4 静态安全属性扫描
   （NX/PIE/RELRO）对其不适用——安全属性取决于运行它的 `/bin/sh`。

---

## 三、测试详情

### 3.1 通过的上游测试用例（13/13）

| 测试项 | 功能 | 结果 |
|--------|------|------|
| `lddtree_usage` | `-h`/`--help` usage 到 stdout 且退 0；无参数 usage 到 stderr 且退 1 | ✅ PASS |
| `lddtree_version` | `-V`/`--version` 输出 `lddtree-<x.y>` 且退 0 | ✅ PASS |
| `lddtree_sh` | 对 `/bin/sh` 输出 `sh => /bin/sh (interpreter …)` 且退 0 | ✅ PASS |
| `lddtree_sh_list` | `-l`/`--list` 只输出以 `/` 开头的行、不带 interpreter 装饰 | ✅ PASS |
| `lddtree_sh_all` | `-a`/`--all` 输出包含 interpreter 行 | ✅ PASS |
| `lddtree_sh_debug` | `-x`/`--debug` 在 stderr 产生 shell trace（`^+`） | ✅ PASS |
| `lddtree_sh_missing_scanelf` | 无 scanelf/binutils 时报 `needs either scanelf or binutils` 并退 1 | ✅ PASS |
| `lddtree_root` | `-R`/`--root` 前缀解析测试数据树 | ✅ PASS |
| `lddtree_no_auto_root` | `--no-auto-root --root` 组合 | ✅ PASS |
| `lddtree_no_auto_root_list` | `--list --no-auto-root --root` 扁平输出且不串到 gnu 分支 | ✅ PASS |
| `lddtree_ldso_conf` | `etc/ld.so.conf` 中的搜索路径被采纳 | ✅ PASS |
| `lddtree_ld_musl_path_conf` | musl 的 `ld-musl-*.path` 配置被采纳 | ✅ PASS |
| `lddtree_rpath_origin_lib` | `$ORIGIN` 相对 RPATH 解析（跨 2 个二进制） | ✅ PASS |

> 说明：以上用例名、断言字面量与期望值**全部取自上游 `tests/lddtree_test` 原文，
> 未作任何修改**（文件 sha256 `19b97aad…`，与上游一致）。

### 3.2 新增测试（test_package，38 条断言）

| 断言组 | 覆盖内容 | 断言数 |
|--------|----------|-------:|
| 版本输出 | `-V`/`--version` 退出码与 `lddtree-1.27` 字符串 | 4 |
| 用法输出 | `-h`/`--help` 退出码 0 且 usage 在 stdout | 4 |
| 无参数 | 退出码 1 且 usage 在 stderr | 2 |
| 非法选项 | 退出码 1 且 usage 在 stderr | 2 |
| 树状输出 | 根行、interpreter 行、至少一条依赖行 | 4 |
| `-l`/`--list` | 退出码、有输出、全部为绝对路径、无 interpreter 装饰 | 8 |
| `-a`/`--all` | 退出码、包含 interpreter | 4 |
| `-x`/`--debug` | 退出码、stderr 有 shell trace | 4 |
| 缺失文件 | 非零退出 + `does not exist` 诊断 | 2 |
| 目录入参 | 非零退出 + `is a directory` 诊断 | 2 |
| `--root` 模式 | 退出码 + 列出被分析文件 | 2 |
| **合计** | | **38** |

### 3.3 跳过的测试

无。13 个上游用例全部真实执行（`0 skipped`）。

---

## 四、关键问题分析

### 问题 1: 上游选项解析依赖外部 GNU `getopt`

**现象**：

```
$ sh lddtree.sh -V
lddtree.sh: invalid option -- 'V'      # 或 usage + exit 1
```

**根因分析**：上游第 334 行调用 `getopt -n "$argv0" -o "ahlR:Vx" -l …`。
本平台 CI worker 的 PATH（`/data/app/bin:/system/bin:/system/sbin:/vendor/bin`）
中 `/system/bin` 是 toybox，**不提供 `getopt`**；制品仓也无 util-linux。
因此脚本在解析任何参数前就失败。

**解决方案**：`patches/0001-portable-option-parsing.patch`（73 行，仅改 `lddtree.sh`）
用纯 POSIX shell 手工解析替换，保持全部可观测行为（含短选项捆绑 `-la`、
`-R<arg>`、`--root=<arg>` 与 `--root <arg>`、`--` 终止符、错误路径退 1）。

### 问题 2: 上游测试套件依赖 ATF + kyua

**现象**：

```
$ make check
kyua: command not found        # 本平台无 kyua，也无 atf-sh
```

**根因分析**：上游 `Makefile` 的 `check` 目标为 `kyua test || (kyua report --verbose && exit 1)`，
并通过 `tests/Kyuafile`/`Kyuafile` 注册 ATF 程序；用例本体 `tests/lddtree_test`
是 ATF 风格脚本，依赖 `atf_get_srcdir` / `atf_check` / `atf_fail` / `atf_skip` 等 API。

**解决方案**：`patches/0002-self-contained-test-runner.patch`（186 行）保留 `check`
目标，新增 `tools/atf-sh-mini`——一个 158 行 POSIX sh 的 ATF 兼容层，实现上述
API 与 `-s exit:N` / `-o match:` / `-o not-match:` / `-e match:` 判定语义，
每个用例在独立进程与独立临时目录中执行，并输出用例级与断言级汇总。
**上游测试文件未作任何修改**（`tests/lddtree_test`、`tests/test_env.sh` sha256 未变）。

### 问题 3: `conan create` 报 `BadZipFile: File is not a zip file`

**现象**：

```
lddtree/1.27: Uncompressing v1.27 to .
ERROR: lddtree/1.27: Error in source() method, line 81
	get(self, **self.conan_data["sources"], strip_root=True)
	BadZipFile: File is not a zip file
```

**根因分析**：源码 URL 写成 `…/tar.gz/refs/tags/v1.27`，以**裸 tag** 结尾；
Conan 的 `get()` 依据文件名后缀选择解压器，无 `.tar.gz` 后缀时按 zip 处理 gzip 流。

**解决方案**：改用 `https://github.com/ncopa/lddtree/archive/refs/tags/v1.27.tar.gz`
（sha256 不变，实测内容一致）。

### 问题 4: 制品仓 bmake 报 `no system rules (sys.mk)`

**现象**：

```
lddtree/1.27:   bmake: no system rules (sys.mk).
lddtree/1.27:   bmake: stopped in …/b
```

**根因分析**：制品仓 bmake 把 `sys.mk` 放在 `share/mk/`，而 bmake 默认不在该
目录搜索系统规则文件，因此在读取项目 Makefile 前就中止。

**解决方案**：以 `make -r`（禁用内建规则）调用。lddtree 的 `Makefile` 显式声明了
全部规则与变量，`-r` 不影响其语义；`-r` 亦为 GNU make 所接受，故此改动可移植。

### 问题 5: 运行时缺少 ELF 解析后端

**现象**：

```
$ lddtree.sh /bin/sh
lddtree.sh: This tool needs either scanelf or binutils (objdump and readelf)
```

**根因分析**：lddtree 本身不做 ELF 解析，必须外部后端。本平台无 `scanelf`
（pax-utils 未适配发布），且 CI worker 的 PATH 中也没有 `objdump`/`readelf`。

**解决方案**：把 `binutils/2.46.0` 声明为**运行时依赖**（`requires`，而非
`tool_requires`），其 `runenv_info` 会把 `objdump`/`readelf` 加入 PATH，
使 `conan install lddtree/1.27` 直接得到可用工具。

### 问题 4.4（CI 门禁）: L4 静态扫描误报

**现象**：

```
[warn] L4: Dangerous functions found in patches:
archives/l/lddtree/1.27/patches/0002-self-contained-test-runner.patch
```

**根因分析**：CI 门禁使用 `grep -rlE '(strcpy|sprintf|gets|strcat)\b' patches/`，
**未加词首边界**，因此命中补丁注释中的普通英文单词 `targets` 里的子串 `gets`
（该补丁第 38 行）。本项目为纯 shell，补丁中**不存在任何 C 危险函数调用**。

**解决方案**：无需修改代码（误报、非阻塞，`L4_RESULT=warn`）。如实登记于此。

---

## 五、测试环境

```
Conan:      2.29.1 (OHOS 适配版，ohpcd profile)
Profile:    ci/conan/profiles/ohos-aarch64
Target:     os=OHOS 6.0, arch=armv8, compiler=clang 15, libcxx=libc++, build_type=Release
make:       bmake/20200710 (制品仓，调用方式 `make -r`)
ELF 后端:   binutils/2.46.0 (制品仓) — objdump + readelf
解释器:     平台 /bin/sh (mksh)
TMPDIR:     $HOME/tmp （平台 /tmp 只读，E002）
```

上游测试命令：

```bash
make -r check        # → sh tools/atf-sh-mini tests/lddtree_test
```

消费者测试命令：

```bash
conan create archives/l/lddtree/1.27 -pr:h=ci/conan/profiles/ohos-aarch64 \
    -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

---

*报告生成时间: 2026-09-15*
