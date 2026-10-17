# ding-libs 0.7.0 适配笔记

## 编译环境
- 目标设备：HarmonyOS HongMeng Kernel 1.12.0，aarch64，`os=OHOS`、`arch=armv8`
- 构建系统：Autotools
- 编译器：clang/clang++ 15.0.4（HNP）
- Conan：2.29.1；profile：`ci/conan/profiles/ohos-aarch64`
- 配方默认：`shared=False`、`fPIC=True`

## 编译步骤
1. 从上游 HTTPS release tarball 解压源码，并在源码工作树中完成 OHOS 适配。
2. 通过 `refresh-patch --auto` 生成 14 个逐文件、仅源码层补丁；没有提交 `configure` 或 `Makefile.in` 补丁。
3. Conan `build()` 先应用补丁，再用 `autoconf/2.72`、`automake/1.18`、`libtool/2.5.4` tool-requires 重生成 Autotools 文件。`automake --add-missing --copy` 不覆盖已适配的 `build/config.guess`/`build/config.sub`。
4. Autotools bootstrap 显式使用设备端 `/data/service/hnp/bin/perl`，并把 `PERL5LIB` 限定为 Automake 的纯 Perl 模块，避免 Conan Perl 的 OHOS ABI 不兼容扩展。
5. `AutotoolsToolchain.extra_cflags` 注入 Check include 路径，避免修改生成的 `Makefile.in`；配方不传 `--build/--host/--target`。
6. `make check` 使用 `CK_FORK=no`，并将 `TMPDIR`、`TMP`、`TEMP` 指向构建目录；Check 动态库只在测试运行环境中加入 `LD_LIBRARY_PATH`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Autotools 无法识别设备系统 | 上游 `config.guess/config.sub` 不认识 HarmonyOS 与 `aarch64-unknown-linux-ohos` | 源码补丁增加 `__OHOS__`/HarmonyOS 和 `linux-ohos` 识别；配方保持 native 构建 |
| 2 | configure 临时文件创建失败 | HMDFS 对 `umask 077` 生成的目录权限组合不兼容 | 在 `configure.ac` 中覆盖 `AS_TMPDIR`，生成脚本使用最小的 `umask 027` |
| 3 | Check 头文件未找到 | 上游 dhash 测试目标的 CFLAGS 变量拼写错误且子目录规则未继承 Check flags | 由 Conan `AutotoolsToolchain.extra_cflags` 注入 Check include 目录；不修改生成文件 |
| 4 | Check fork/临时文件测试失败 | OHOS 设备的临时目录和 fork 行为与 Linux 不同 | 测试环境设置 `CK_FORK=no`，使用任务私有构建临时目录 |
| 5 | INI/path 测试的权限与诊断字符串不同 | HMDFS 归一化文件模式；musl/系统路径与 Linux 不同 | 按 OHOS 条件调整期望模式、使用设备可用路径，并改为语义诊断匹配 |
| 6 | `open_memstream` 最终大小未发布 | OHOS libc 在 `fclose` 前不会自动暴露最终 buffer size | 在 `fclose` 前调用 `fflush` |
| 7 | Conan Autotools 工具的 Perl 扩展加载失败 | Conan `perl/5.42.2` 的 `Cwd.so` 与设备 Perl ABI 不匹配 | bootstrap 命令显式选设备 Perl，并只暴露 Automake 纯 Perl 模块目录 |
| 8 | Automake 重生成后 OHOS 检测丢失 | `--force-missing` 会覆盖已修改的 config.guess/config.sub | 改用不带 `--force-missing` 的 `automake --add-missing --copy` |

## 源码修改

以下 14 个补丁均由 `refresh-patch --auto` 固化并在 `conandata.yml` 中声明：

- `0001`、`0002`：`build/config.guess`、`build/config.sub` 的 OHOS tuple 识别。
- `0003`：`configure.ac` 的 HMDFS 临时目录处理；生成文件在配方构建时重生成。
- `0004`、`0005`、`0009`、`0011`：HMDFS 权限归一化和保存比较。
- `0006`：OHOS `open_memstream` 大小发布。
- `0007`、`0008`、`0010`、`0013`：OHOS 无 gettext 声明时使用 identity translation macro。
- `0012`：使 regex 错误诊断匹配跨 libc 可移植。
- `0014`：避免 OHOS `/etc` symlink 对 path utility 测试的影响。

## 依赖版本
- 构建工具：`autoconf/2.72`、`automake/1.18`、`libtool/2.5.4`
- 测试依赖：`check/0.15.2`
- 运行时不新增 Conan 依赖；产物为 `dhash` 与 `ini_config` 两个组件。

## 验证结果

设备端最终 `conan create`（OHOS armv8 Release，14 个补丁）已通过：

- Autotools 重生成、configure、编译、安装：通过。
- 上游 `make check`：`20 TOTAL / 20 PASS / 0 FAIL`。
- Conan `test_package`：通过，实际调用 `dhash` 与 `ini_config` public API，输出 `ding-libs public API test passed`。
- Conan 包含 `libdhash.a`、`libini_config.a`、头文件和两个 pkg-config 文件。
- `conan-verify`：G1-G4 PASS；W3：1/1 包通过、RC=0。
- 检视意见整改后复验（PR #7133）：`conan-verify` G1–G4 PASS，上游 `make check` `20 TOTAL / 20 PASS / 0 FAIL`，`test_package` 通过。
- `finish`：Conan/W3 步骤通过；旧版 G0 的 HMDFS `getcwd` 检查、legacy tarball 收尾和知识图谱收尾存在框架警告，未修改框架代码。
- W4 独立审计：`verdict=pass`，P0=0、P1=0、issues=0；`pre_pr_audit.py report` 复核通过。
- `result` 已生成：`status=partial`；因无 PR/远端 CI 绿灯，不虚报 success。

复现命令（设备端）：

```sh
export PATH="/data/service/hnp/bin:$HOME/.local/bin:$HOME/usr/local/bin:$PATH"
export DEFAULT_PREFIX="$HOME/usr/local"
export TMPDIR="$HOME/tmp/ding-libs-0.7.0"
export TMP="$TMPDIR" TEMP="$TMPDIR"
export CONFIG_SHELL=/data/service/hnp/bin/bash SHELL=/data/service/hnp/bin/bash
python3 scripts/ohc-run.py conan-verify ding-libs 0.7.0 --profile ohos-aarch64 --project-dir "$PWD"
python3 scripts/ohc-run.py finish ding-libs 0.7.0 built --project-dir "$PWD"
```

## 注意事项
- W3/verify 预下载可能临时把 `conandata.yml` 的 `sources.url` 改成 `file://` 或镜像地址；运行后必须确认归档仍为官方 HTTPS URL。
- Check 的 `LD_LIBRARY_PATH` 仅作用于测试过程，不通过静态链接掩盖运行环境问题。
- 该版本是库包，无命令行工具，不需要软件级 `commands.json`。
- `finish` 的旧版打包收尾仍可能寻找已由 ARCHIVE-SPEC v3.0 废弃的 legacy tarball；该框架限制不等同于 Conan/测试失败。

### 对话 #1
- 完成源码适配、源码级补丁固化、Autotools tool-requires、Conan 配方和 API test package。
- 修复了生成文件补丁违反 R6、Conan Perl ABI 冲突和 `--force-missing` 覆盖 OHOS config 脚本的问题。
- 已重新通过设备端 Conan create、conan-verify、W3 和独立 W4；最终 result 已生成为 partial。

### 对话 #2（PR #7133 检视意见整改）

- **R8 口径复核**：`references/iron-rules.md:265`（SKILL.md:414 指定的铁律详解权威）写明
  「源码中可以使用，但 patches/ 补丁文件中不应引入 `#ifdef __OHOS__`」。本 PR 原有 10 处平台宏
  全部位于 patches/ 下，落在 R8 约束范围内；此前引用 SKILL.md §1.3 摘要与
  `.gitcode/review-memory.md` 的辩护不成立（三份文档对「源码 / patches」的口径不一致，
  已作为文档冲突另行记录）。
- **gettext 组（0007/0008/0010/0013）**：`__OHOS__` 恒等宏改为标准 `#ifdef ENABLE_NLS` 判据。
  配方以 `--disable-nls` 运行 configure，`config.h` 中 `ENABLE_NLS` 未定义，因此走恒等分支；
  写法平台无关，且将来启用 NLS 时自动恢复 gettext。0013 另为 `path_utils.h` 补
  `#include "config.h"`——该头自行决定 `_()` 的定义，不应依赖调用方先包含 config.h。
- **权限组（0004/0005/0009/0011）**：删除平台宏，期望模式保留上游值，改用入参 `mask` 限定比较位。
  `access_check_int()`（`ini/ini_fileobj.c:1521`）与 `config_access_check()`
  （`ini/ini_metadata.c:380`）语义一致：`mask == 0` 时比较低 9 位，否则只比较 `mask` 置位的位。
  HMDFS 实测把不含属主执行位的模式归一化为 0640，故取各平台表示一致的位集合：
  0444→0440、0664→0640、0600→0600、0660→0640。断言仍覆盖这些位，回归可被捕获。
  未采纳 fstat 读回实际模式当期望值的建议——那会让断言退化为用结果验证结果。
- **0014**：探测路径由 `/etc/passwd` 改为 `/usr/bin/env`（OHOS 上 `/etc` 是符号链接，
  `find_existing_directory_ancestor()` 不解析符号链接），平台无关；同时覆盖
  `test_find_existing_directory_ancestor_neg` 用例，避免该用例仍指向 `/etc/passwd`。
- **0011** 另保留 `cmp -l -b` → `cmp`：toybox 的 `cmp` 不支持 `-b`，属工具能力差异而非平台身份。
- **0001 保留 `__OHOS__`**：该宏位于 `config.guess` 生成的 C 探测程序内部，紧邻上游自带的
  `__ANDROID__` 分支，用于判定 libc；第二个 hunk 的平台识别本身基于 `uname`，不依赖该宏。
  识别 libc 无法用 POSIX 接口替代——判定平台身份正是该探测的目的。
- **配方新增 `os.environ["PWD"] = self.build_folder`**：HMDFS 下 Conan 建树后父目录对
  `getcwd()` 不可达，configure 在 `CONFIG_SHELL=bash` 下重执行时 `pwd` 失败并报
  `working directory cannot be determined`。该故障为间歇性（12 个构建目录中 4 个命中），
  与 adms / aribb24 / aircrack 等 37 个配方采用同一写法。
- 打完 14 个补丁后，源码（`.c`/`.h`）中 `__OHOS__` 残留 0 处。

---

**编译结束**: 2026-08-29 18:05
**最终状态**: built（检视意见整改后重新通过设备端 conan-verify G1–G4、make check 20/20、test_package；finish 的旧 G0/打包收尾存在框架限制）
