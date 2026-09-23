# lddtree 1.27 HarmonyOS PC 适配笔记

## 编译环境

- 构建系统: makefile（仅用于驱动测试；产品本身是一份 POSIX shell 脚本，**无编译步骤**）
- 编译日期: 2026-09-15
- 编译器: 不适用（无 C/C++ 源码）；测试运行时用平台的 `/bin/sh`（mksh）
- 目标: HarmonyOS/OHOS 6.0 aarch64（armv8, clang 15, libc++）
- 状态: built
- 语言预检（R47）: `task=cpp, detected=c` → 命中 c↔cpp 兼容族，继续适配主流程

## 编译步骤

```bash
conan create archives/l/lddtree/1.27 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

配方要点：

- `package_type = "application"`（产物是 `bin/lddtree.sh` 命令行工具，R38），
  软件级 `commands.json` 已声明 `lddtree.sh`（`version_arg: -V`）。
- `settings` 四项齐全（L0p）。
- `source()` 用 `get(self, **self.conan_data["sources"], strip_root=True)`。
- `build()` 不编译代码，只做两件事：`sh -n lddtree.sh` 语法检查、
  运行上游测试套件（`make -r check`），并把完整测试记录回显到日志。
- `package()` 安装 `bin/lddtree.sh`（0644→0755）、`doc/README.md`、`licenses/`。
- `package_info()`：`bindirs=["bin"]`，`runenv_info` 把包内 `bin/` 前置到 PATH。

## 上游测试三步法申报表（R51）

### 第 1 步 — 清点上游测试（命令 + 原始结果）

上游源码 `/storage/Users/currentUser/tmp/lddtree-1.27/`：

```bash
$ grep -c '^lddtree_.*_body()' tests/lddtree_test
13                      # 13 个测试用例函数

$ grep -n 'init_tests' -A 14 tests/lddtree_test | head -16
init_tests \
	lddtree_usage \
	lddtree_version \
	lddtree_sh \
	...（共 13 个注册项）
lddtree_rpath_origin_lib

$ ls tests/
lddtree_test  test_env.sh  testdata/

$ sha256sum tests/lddtree_test tests/test_env.sh
19b97aad014553792c6e357a3d32e971456cc14af6ff47bd51dbdba5d0fc848e  tests/lddtree_test
72eb4e3a267a8726c256e54252a1eb7c1fbbff5ec9fcd937c606bccd9da3ef8a  tests/test_env.sh
```

**清点结论：上游 13 个测试用例**（单个 ATF 程序 `tests/lddtree_test`，
用例名：`usage / version / sh / sh_list / sh_all / sh_debug /
sh_missing_scanelf / root / no_auto_root / no_auto_root_list / ldso_conf /
ld_musl_path_conf / rpath_origin_lib`）。上游无独立集成测试套件。

### 第 2 步 — 在可运行环境中实际运行

见下方「验证结果」。13 个用例**全部真实执行**，无一跳过。

### 第 3 步 — PR 如实回填

通过率 **13/13（100%）**、断言 **21 passed / 0 failed**、退出码 0，
已回填至 PR 正文与本目录 `test-report.md`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 任何选项解析都失败（连 `-V` 都报 usage 并退出 1） | 上游用外部 GNU `getopt(1)`；本平台 toybox/busybox 不提供该命令，制品仓也无 util-linux | `patches/0001` 用等价的 POSIX shell 手工解析替换之（短选项捆绑 `-la`、`-R<arg>`、长选项 `--list`、`--root=<v>` 与 `--root <v>` 全部支持） |
| 2 | `make check` 直接失败 | 上游依赖 ATF + kyua（`kyua test` + 生成 Kyuafile）；本平台既无 `kyua` 也无 `atf-sh`，制品仓亦无 | `patches/0002` 保留 `check` 目标，新增 `tools/atf-sh-mini`（POSIX sh 的 ATF 兼容层），**上游测试文件一字未改** |
| 3 | `conan create` 报 `BadZipFile: File is not a zip file` | 源码 URL 写成 `…/tar.gz/refs/tags/v1.27`，以裸 tag 结尾 → Conan `get()` 按 zip 处理 gzip 流 | URL 改为以 `.tar.gz` 结尾的 `https://github.com/ncopa/lddtree/archive/refs/tags/v1.27.tar.gz`（sha256 不变） |
| 4 | `make` 报 `bmake: no system rules (sys.mk)` | 制品仓 bmake 的 `sys.mk` 位于 `share/mk`，bmake 默认不搜索该目录 | 以 `make -r`（禁用内建规则）调用：lddtree 的 Makefile 显式声明了全部规则，且 `-r` 为 GNU make 同样接受 |
| 5 | 工具运行报 `needs either scanelf or binutils` | 本平台无 `scanelf`，CI worker 的 PATH 也没有 `objdump`/`readelf` | 把 `binutils/2.46.0` 声明为**运行时依赖**（`requires` 而非 `tool_requires`），其 `runenv_info` 会把 `objdump`/`readelf` 加入 PATH，用户 `conan install` 后即可用 |

## 源码修改

```bash
patches/0001-portable-option-parsing.patch   # 73 行，仅改 lddtree.sh
patches/0002-self-contained-test-runner.patch # 186 行，改 Makefile + 新增 tools/atf-sh-mini
```

- 补丁内**无平台宏**（`grep -c __OHOS__` = 0，符合 PF5/R8）。
- `tests/lddtree_test` 与 `tests/test_env.sh` **未被改动**（sha256 与上游一致，见上方第 1 步）。
- 未削弱、未删除、未跳过任何上游断言；`patches/0002` 只替换测试驱动方式并新增断言级计数。

## 依赖版本

| 依赖 | 类型 | 说明 |
|------|------|------|
| binutils/2.46.0 | requires（运行时） | 提供 `objdump` + `readelf` 后端 |
| bmake/20200710 | tool_requires（构建期） | 提供 `make` 以驱动 `make check` |

## 验证结果

### 上游测试套件（`make -r check`，隔离 PATH：无 getopt、有 readelf/objdump）

```
lddtree_usage                    PASS
lddtree_version                  PASS
lddtree_sh                       PASS
lddtree_sh_list                  PASS
lddtree_sh_all                   PASS
lddtree_sh_debug                 PASS
lddtree_sh_missing_scanelf       PASS
lddtree_root                     PASS
lddtree_no_auto_root             PASS
lddtree_no_auto_root_list        PASS
lddtree_ldso_conf                PASS
lddtree_ld_musl_path_conf        PASS
lddtree_rpath_origin_lib         PASS

13 tests, 13 passed, 0 failed, 0 skipped
ASSERTIONS: total=21 failures=0
```

退出码 0。

### 破坏性反向验证（证明用例与计数非空转）

把 `lddtree.sh` 的 interpreter 输出改为固定 `BOGUS` 后重跑：

```
13 tests, 8 passed, 5 failed, 0 skipped
ASSERTIONS: total=21 failures=8
make: *** [Makefile:3: check] Error 1
```

退出码 2 —— 失败被真实捕获（`failures` 非 0），随后还原。

### test_package 消费者测试（`conan create` 内自动执行）

```
ASSERTIONS: total=38
consumer test passed: 38 assertions, 0 failures
```

### 本地 CI 模拟（`ci/conan/build_and_test.sh`，CI_PACKAGES=archives/l/lddtree/1.27）

```
L0_RESULT=pass: all checks passed
L1_RESULT=pass: upstream tests + test_package executed
L2_RESULT=pass: lddtree.sh --version OK
L4_RESULT=warn: dangerous functions in patches
L5_RESULT=pass: bin/ has content
  Pass rate: 100.0% (1/1)
```

`L4=warn` 为**误报**：门禁用 `grep -E '(strcpy|sprintf|gets|strcat)\b'` 扫描补丁，
未加词首边界，命中的是补丁注释里的普通英文词 `targets` 中的 `gets`
（补丁中不存在任何 C 危险函数调用——本项目根本没有 C 代码）。非阻塞项，已记录。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `bin/lddtree.sh` | 11 KB | 唯一交付产物（POSIX shell 脚本） |
| `doc/README.md` | 2.9 KB | 上游 README |

## 注意事项

- **上游测试失败即构建失败**：`build()` 里把 `make check` 的退出码、用例级汇总
  与断言级汇总一并检查，任何失败/跳过都会抛 `ConanException`，避免"红测试但绿色构建"。
- 该工具**不执行**被分析的文件，只读取 ELF 头与动态段，因此可安全用于分析
  不可信二进制；`--root` 模式常用于剖析镜像而非本机。
- 若使用者自行部署（不经 conan），需保证 `objdump` 与 `readelf` 在 PATH 中。
