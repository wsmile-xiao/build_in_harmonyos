# pexec 1.0 适配笔记

## 版本坐标取证（本条是本任务最关键的前置结论）

任务 #9433 指定版本 `1.0`。**上游 GNU pexec 从未发布过 1.0 正式版**，取证三条：

1. 源码包内 `NEWS` 的版本链只有 11 个条目，全部是 pre/rc：
   `1.0pre1 → 1.0pre2 → 1.0rc0 → … → 1.0rc8`，**没有 `1.0:` 条目**
   （取数：`grep -cE '^1\.0' NEWS` → 11；`grep -nE '^1\.0( |rc|pre)' NEWS | tail -3` → rc0 / pre2 / pre1）。
2. `doc/version.texi` 的 `@set VERSION 1.0rc8`、`configure` 的 `PACKAGE_VERSION='1.0rc8'`、
   源码根 `VERSION` 文件内容 `1.0rc8` 三处一致；打包日期 2008-11-04。
   真机跑出的二进制自报 `pexec 1.0rc8 (2009.07.02)`。
3. GNU 发布目录 `gnu/pexec` 下只有 `pexec-1.0rc7.tar.gz` 与 `pexec-1.0rc8.tar.gz`
   （取数：`curl -s https://mirrors.tuna.tsinghua.edu.cn/gnu/pexec/ | grep -oE 'pexec-[0-9][^"<]*' | sort -u`；
   对 `pexec-1.0.tar.gz` 探测 tuna / aliyun 均 404，ftp.gnu.org / ustc 本机不可达）。
   Debian 侧同一软件最高版本记作 **`1.0~rc8`**（sources.debian.org/api/src/pexec），
   即按 Debian 的排序规则 "1.0" 系列唯一的已发布字节就是 rc8 这一份。

结论：本条按任务指定的版本键 `1.0` 打包 1.0 系列唯一已发布的 `pexec-1.0rc8.tar.gz`
（sha256 `a968e4774eef80b8b1de3c10e6c0ad2ebeeb732b10e438596f110aa6aaf94a64`，
与已合入的 `archives/p/pexec/1.0rc8` 同一份字节），**不改源码、不用任何分支顶替**。
版本键 `1.0` 与制品仓已有的 `1.0rc8` 精确区分，不触发 L0j/R37
（`node tools/ohpcd.mjs precheck pexec 1.0` → 「同版本未发布 → 可领」）。

## 与已合入 1.0rc8 配方的差异（不是复制粘贴）

| 项 | 1.0rc8（main 已合入） | 本条 1.0 |
|---|---|---|
| 上游测试 | 声明「上游无自动化测试 N=0」，`upstream_test_in_build: false` | **纠正**：`Makefile.in:126` 有 `check: src` 目标，build() 内真跑 `make -j1 check`，N=1 并在鸿蒙上实跑通过 |
| 消费者测试 | 3 条断言（--help / --version / 未知选项） | **16 条断言**：并行 `-n 3`、串行 `-n 1` 结果一致、参数文件 `-f` 驱动、`-R` 合并 stdout 行数、逐参数输出文件内容对拍，外加 OHOS shell 就地探测 |
| OHOS 运行期坑 | 未覆盖 | 发现并处理：pexec 的 `-c` 脚本模式依赖 shell，OHOS 上 `/bin/sh` 不保证存在 → 消费者测试探测后显式 `-s <shell>` |

漏掉 `check` 目标的直接原因：`grep -E '^(TESTS|check|installcheck)[[:space:]]*[:+]?='` 要求等号，
而 Makefile 的 `check: src` 是无等号的纯目标行。**清点上游测试必须同时 grep `^check:`。**

## 编译环境

- 构建系统: autotools（GNU 项目自带 configure，1990 年代脚本）
- 编译日期: 2026-09-20
- 编译器: clang 15（OHOS aarch64 真机，SDK `ohos-sdk@26.0.0.18`）
- 状态: built

## 编译步骤

1. W0 预检：零外部依赖（无 requires），不需要先发依赖。
2. 配方为 application 型（`bin/pexec` + 软件级 `commands.json`）：
   - `generate()`：`VirtualBuildEnv(self).generate()` —— conanbuild 环境提供 `CONFIG_SHELL/SHELL`，
     避免 configure 落到 HMDFS 受限的 `/bin/sh`（E386）。
   - `build()`：
     a. 源码整树拷到浅层目录 `~/tmp/uc2/pexec-build-1.0`（深 conan 缓存目录下 config.status
        报 `conf*/subs-1.sed: Permission denied`，E011/E114 同源）；
     b. 就地把 configure 里的 `(umask 077 && …)` 放宽（E011）；
     c. `sh configure --build=aarch64-unknown-linux-gnu --prefix=<pkg>` + `make -j1`
        （config.guess 不认识 HongMeng 内核，显式给 build 三元组跳过探测）；
     d. 断言 `src/pexec` 产物存在后 **`make -j1 check` 真跑上游自检**；
     e. 产物拷回 build_folder。
   - `package()`：拷 `bin/pexec` 并 chmod 0755；`package_info()` 清空 includedirs/libdirs，只留 bindirs。
3. R38：软件级 `archives/p/pexec/commands.json` 追加 `"1.0"` 条目，保留原有 `"1.0rc8"`。

## 上游测试账本（四维）

- 上游源码静态声明总数 N_static = **1**：`Makefile.in` 的 `check:` 目标 1 条
  （取数 `grep -nE '^check:' Makefile.in src/Makefile.in doc/Makefile.in` → `Makefile.in:126`）；
  其命令体为单条 `./src/pexec -n 2 -r 1 2 3 4 -e x -c -R -- 'echo $x'`，
  断言方式是 make 的退出码（子进程非零则 make 失败）。
- 全树无 `TESTS=` / `check_PROGRAMS` / `*.t` / 测试脚本（取数见下节「N=0 之外还有什么」），
  所以除这 1 条自检外没有更多用例可跑。
- 实际执行数 N_executed = **1**（`conan create` 日志第 247 行 `RUN: … make -j1 check`，
  第 252 行回显上游命令，随后输出 `1`/`2`/`3`/`4` 四行，make 未报错）。
- 跳过数 = 0。
- 新增消费者测试 N_consumer = 1 个脚本 / **16 条断言**：`test_package/test_pexec.sh`
  （`TOTAL=16 PASS=16 FAIL=0`），由 `test_package/conanfile.py::test()` 实际执行。

### N=0 之外还有什么（排除误报的取数）

```sh
# 全部为 0，说明除 Makefile.in 的 check 目标外上游再无用例
grep -rnE '^[[:space:]]*(TESTS|check-am|installcheck|check_PROGRAMS)[[:space:]]*[:+]?=' \
    Makefile.in src/Makefile.in doc/Makefile.in | wc -l      # → 0
find . \( -iname '*test*' -o -iname '*check*' -o -iname '*.t' \) | wc -l   # → 0
find . \( -name '*.sh' -o -name '*.py' \) | wc -l            # → 0
grep -rc 'dejagnu' Makefile.in                               # → 0
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan 缓存深目录下 configure 报 `conf*/subs-1.sed: Permission denied` | HMDFS 权限组合（E011/E114 同源） | build() 把源码拷到浅层 `~/tmp/uc2/pexec-build-<ver>` 编译；放宽 configure 中的 `(umask 077 && …)` |
| 2 | `working directory cannot be determined` / `shell-init: getcwd failed` | conan profile 的 `SHELL`/`CONFIG_SHELL` 指向 `/data/service/hnp/bin/bash`（HMDFS 下 getcwd 必挂，E386） | `generate()` 生成 VirtualBuildEnv |
| 3 | `cannot guess build type` | 1990 年代 config.guess 不认识 HarmonyOS，探针在 HMDFS 上还会 Permission denied | 显式 `--build=aarch64-unknown-linux-gnu` |
| 4 | 编译器定位（CLI 工具的 CC/CXX） | 设备交互 shell 的 PATH 不等于 conan 工具链 | 从 `tools.build:compiler_executables` 取 CC/CXX 显式传入（R33） |
| 5 | 上游测试被漏报为 0 | `check: src` 目标行无等号，常见 grep 口径漏掉 | 清点和 grep 都补上 `^check:`；配方 build() 内真跑 `make -j1 check` |
| 6 | pexec `-c` 在鸿蒙上依赖 shell | OHOS 的 `/bin/sh` 不保证存在（该真机恰好有） | 消费者测试就地探测 `/bin/sh`→`/system/bin/sh`→`$HOME/.harmonybrew/bin/{sh,bash}`→`command -v`，用 `-s` 显式传入 |

## 源码修改

无补丁（`conandata.yml` 的 `patches` 为空）；上述 umask / shell / 三元组三处适配全部在配方
`build()`/`generate()` 内就地完成。

## 依赖版本

无外部依赖（零依赖工具包）。

## 真机取证

独立缓存 `CONAN_HOME=/storage/Users/currentUser/work/psj/ch-pexec`
（全新 home，仅 `cp` 共享 profile `ohos-aarch64`，未读写共享 `~/.conan2`）：

```
conan create archives/p/pexec/1.0 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
CREATE_EXIT:0                                   (09:36:53Z 导出 → 09:38:17 CST 结束)
pexec/1.0: Full package reference:
  pexec/1.0#5083ee8454ed7654b0662e136dc8c2bb:6b129b068851896169fae42d399fa922d239ce8a#91396b7414551fa16de75417c0abaae6
settings: os=OHOS os.version=6.0 arch=armv8 compiler=clang compiler.version=15
          compiler.cppstd=17 compiler.libcxx=libc++ build_type=Release
RUN: … make -j1 check → ./src/pexec -n 2 -r 1 2 3 4 -e x -c -R -- 'echo $x' → 1 2 3 4
======== Testing the package: Executing test ========
  using shell for -c: /bin/sh
TOTAL=16 PASS=16 FAIL=0
pexec consumer tests passed
```

产物：`bin/pexec` 108928 B，`ELF64 / DYN (Shared object file) / Machine: AArch64`，
`NEEDED` 只有 `libc.so`；`pexec --version` → `pexec 1.0rc8 (2009.07.02)`
（二进制自报的是上游发布号，与包版本键 `1.0` 的关系见本文首节）。

日志：真机 `~/work/psj/pexec-ch1.log`（316 行 / 15657 B）。
配方字节校验：`tools/pxe_dev_run.sh` base64 上传后设备/本地 md5 全等。
