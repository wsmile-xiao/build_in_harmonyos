# zsync 0.6.3 适配交接

- issue：TBD（已在本地项目归档、汇总和会话上下文搜索，未找到明确编号）
- 分支：`feat/zsync-0.6.3`
- 源码：`cph6/zsync` tag `0.6.3`，SHA256 `1cb42733a28258b20c9ee804f6b0d218d15d0d6d7b6514a567b21c651bed1cc4`
- 构建系统：`c/configure.ac` + Autotools；源码包只有 `c/configure.ac`、没有生成的 `configure`，而 CI 环境没有 `autoreconf`，因此配方不依赖 Autotools 生成流程，直接按上游 `Makefile.am` 的源文件清单调用 OHOS clang 编译。源码包内置 zlib、librcksum、libzsync，无 Conan 依赖。
- 产物：`zsync`、`zsyncmake` 两个命令行工具。
- 上游测试：共 **4 个**，由三个 `Makefile.am` 的 `TESTS` 声明 —— `c/`：`check-zsyncmake`；`c/librcksum/`：`md4test`、`rsumtest`；`c/libzsync/`：`sha1test`。源码包无生成的 `configure`、CI 无 `autoreconf`，配方不走 Autotools，改为在 `build()` 中按 `Makefile.am` 的源文件清单编译并运行这 4 个测试（`check-zsyncmake` 需要 `perl`，见 `build_requirements`）；目标平台不可运行时自动跳过。

## 适配补丁

配方携带 2 个补丁（`patches/`），均在 `conandata.yml` 注册，并由 `export_sources()` 导出。

### 0001-make-use-writable-temp-dir.patch — 修复 zsyncmake 必然崩溃（portability）

**现象**：真机上 `zsyncmake` 对任何输入（空文件、短文件、`INSTALL`）都以 `SIGABRT`（exit 134）结束，**不打印任何信息**，也不生成 `.zsync`。

**根因**：`c/make.c` 用 `tmpfile()` 创建中间文件。`tmpfile()` 使用固定的 `P_tmpdir`（`/tmp`）并且**忽略 `TMPDIR`**；HarmonyOS 的 `/tmp` 是只读 erofs（`root:root 0755`），实测 `tmpfile()` 返回 `NULL`，`errno=13 (EACCES)`。代码没有检查返回值，随后把 NULL 当 `FILE*` 交给 stdio —— OHOS libc 对此直接 abort（而不是段错误），所以只看到 Signal 6、没有任何输出：

- 非空输入：在第一个 `write_block_sums()` 的 `fwrite(&r, sizeof r, 1, tf)` 中止。此时 `.zsync` 还没创建，所以目录里没有输出文件；
- 空输入：不会进入 `write_block_sums()`，会先执行到输出 URL 警告，再在 `fcopy_hashes()` 的 `fread()` 中止。

这解释了此前观察到的全部细节。同时可以排除「`libzsync/zsync.c:480` 的 `abort()`」这一猜测：`abort()` 在整个源码树中只出现一次，而 `make.c` 不引用任何 `zsync_*` API，该分支在 `zsyncmake` 中不可达。

**注意**：知识库的通用做法 `export TMPDIR=$HOME/tmp` **不能**修复本问题 —— 已实测 libc 的 `tmpfile()` 不读取 `TMPDIR`（设置与否都返回 NULL）。凡是直接调用 `tmpfile()` 的程序都需要改代码或另设可写的 `/tmp`。

**修复**：新增 `zsync_tmpfile()`，先沿用 `tmpfile()`，失败后依次回退 `$TMPDIR`、`/tmp`、当前目录（`mkstemp()` 后立即 `unlink()`，保持 `tmpfile()` 的自动清理语义）；`do_zstream()` 与 `main()` 两处调用点都补上 NULL 检查，失败时打印明确错误并 `exit(2)`，而不是解引用空指针。

### 0002-check-zsyncmake-update-expected-cksum.patch — 回填上游测试修正（upstream-backport）

**现象**：`c/check-zsyncmake` 断言 cksum 等于 `4103379992`；打完 0001 后测试终于能跑完，但实际得到 `3456223344`。

**根因**：**tag `0.6.3` 自带的测试期望值已过期**。上游在 tag 之后（2025-05-29）提交 `a5cb28f`「Update check-zsyncmake for changes in 208ef06」，只改了这一行：`4103379992` → `3456223344`。也就是说 tag 上的 `make.c` 与 tag 上的测试互相矛盾，该测试在**任何平台**都不可能通过 —— 这是上游测试缺陷，不是 OHOS 适配问题。

**证据**：修复后的 `zsyncmake` 输出为 `3456223344`，与上游修正后的期望值**逐字节一致**。独立核对：`Length: 9296`、`Blocksize: 2048` 与实际文件一致；`SHA-1: 4471a5dc5109bceca1f5e96f1694c2380737201f` 与 `INSTALL` 的真实 SHA-1 一致；`Hash-Lengths: 1,2,5` 与 `make.c` 的浮点公式手算结果一致。

**处理**：把 `a5cb28f` 原样回填为补丁，生成的 blob 哈希 `3006230..08791e1` 与上游提交一致。该修改属于「对上游测试用例的修改」，已在 PR 的对应栏目逐条声明。

## 上游测试的执行

`build()` 在编译出 `bin/zsyncmake`、`bin/zsync` 之后，编译并运行上游全部 **4 个**用例（等价于 `make check`）：

| 用例 | 来源 | 编译方式 |
|------|------|----------|
| `md4test` | `c/librcksum/Makefile.am` → `TESTS` | `md4test.c md4.c`（在该子目录内编译） |
| `rsumtest` | `c/librcksum/Makefile.am` → `TESTS` | `rsumtest.c rsum.c hash.c range.c state.c md4.c ../progress.c` |
| `sha1test` | `c/libzsync/Makefile.am` → `TESTS` | `sha1test.c sha1.c` |
| `check-zsyncmake` | `c/Makefile.am` → `TESTS` | perl 脚本，直接以 `sh -e` 执行 |

- 配方不走 Autotools（源码包只有 `c/configure.ac`、无生成的 `configure`，CI 无 `autoreconf`），因此不复用 automake 的 `check_PROGRAMS`/`TESTS_ENVIRONMENT`，改为按各 `Makefile.am` 的 `_SOURCES` 清单直接编译，显式传入 `check-zsyncmake` 用到的两个变量：`top_builddir=<build>/bin`（脚本按 `${top_builddir-.}/zsyncmake` 找二进制）与 `srcdir=<scratch>`（脚本按 `${srcdir-.}/INSTALL` 找输入）。
- 测试二进制与 `check-zsyncmake` 的工作目录都在 `build_folder/upstream-tests/`，`INSTALL` 先复制进去，不污染源码树。
- 三个单元测试均为自校验：`md4test`/`sha1test` 用 `exit(memcmp(...))` 与 RFC1320/RFC3174 向量比较，`rsumtest` 失败时 `exit(1)`；任一非 0 退出都会中断 `conan create`。
- `build_requirements()` 声明 `tool_requires("perl/5.42.2")`：`check-zsyncmake` 是 perl 脚本，`perl/5.42.2` 已发布在 `ohpcd` 远端，`conan create` 会自动拉取（约 17 MB），无需手工准备。
- 用 `can_run(self)` 保护：目标平台不可运行（交叉编译）时打印提示并跳过，不会误报通过。

> 注意：不要只数 `c/Makefile.am` 的 `TESTS`。上游测试分散在三个子目录的 `Makefile.am` 中，合计 4 个；只统计顶层会漏报成 1 个。

## CLI 参数面

两个工具都只实现短选项 `-V`（打印版本并退出 0）。长选项没有被实现：

- `zsync --version` / `zsync --help`：报 `unrecognized option` 后 **exit 3**；
- `zsyncmake --version` / `--help`：同样报 `unrecognized option`，但不退出，而是把后续字母当短选项继续解析（例如 `--help` 里的 `e` 命中 `-e`），最终无参数地读取 stdin 并把 `.zsync` 写到 stdout，**exit 0**，并不打印版本或帮助。

因此 `test_package/test.sh` 原先的 `zsync --help` 在 `set -e` 下必然失败，已改为 `-V`（并重定向 stdin，避免 `zsyncmake` 无参数时读 stdin 阻塞）。`test_package/conanfile.py` 的 `test()` 一直使用的是受支持的 `-V`。

Shadow CI 的 L2 通用探测只尝试 `--version` / `--help`：`zsync` 两者都返回 3，`zsyncmake` 在修复 0001 之前会因 tmpfile 缺陷崩溃、修复后 `--help` 能返回 0。L2 是非阻塞门禁。

## 真机验证

在真机独立目录用配方完全相同的编译命令重建 `zsyncmake`，再执行上游 `c/check-zsyncmake`：

| 步骤 | 期望 cksum | 结果 |
|------|-----------|------|
| tag 原始测试（未打 0001） | `4103379992` | `zsyncmake` SIGABRT，不生成 `foo.zsync` |
| 仅打 0001，`TMPDIR` 未设置（`/tmp` 只读） | `4103379992` | FAIL（期望值过期，实际 `3456223344`） |
| 打 0001 + 0002，`TMPDIR` 未设置 | `3456223344` | **PASS** |
| 打 0001 + 0002，`TMPDIR=$HOME/tmp` | `3456223344` | **PASS** |

三个单元测试在真机同样编译并运行通过：

```text
md4test compile rc=0 ; rsumtest compile rc=0 ; sha1test compile rc=0
md4test  rc=0
rsumtest rc=0
sha1test rc=0
check-zsyncmake rc=0 (PASS)
```

产物尺寸与 Shadow CI 记录一致：`zsync` 190912 bytes、`zsyncmake` 178624 bytes。

另外用隔离 `CONAN_HOME` + `ohpcd` 远端复刻 CI 的 `conan create` 验证过一次完整流程：自动下载 `perl/5.42.2`，日志中出现

```text
zsync/0.6.3: RUN: cd <build>/check-zsyncmake && top_builddir=<build>/bin srcdir=<build>/check-zsyncmake sh -e <source>/c/check-zsyncmake
```

且 `conan create` 返回 0，说明上游用例在配方 `build()` 中真实执行并通过。

## 真机 Shadow CI

修复前：`/storage/Users/currentUser/ohpc-ci-shadow/runs/56964fb2fa24-20260918T141505Z-16303`

- L0 pass、L1 pass、L2 skip、L4 pass、L5 pass；Total 1、Success 1、Pass rate 100.0%。
- L2 为 `skip`：通用探测只尝试 `--version`/`--help`，该旧版 CLI 不支持，且当时 `zsyncmake --help` 还会因 tmpfile 缺陷崩溃。

修复后：`/storage/Users/currentUser/ohpc-ci-shadow/runs/cb3fc5964ee0-20260927T042830Z-23995`

- L0 pass、L1 pass、L2 pass、L4 pass、L5 pass；Total 1、Success 1、Pass rate 100.0%。
- L2 由 `skip` 变为 `pass`：修复 0001 后 `zsyncmake --help` 不再崩溃并返回 0。
- L4 为 `pass: patches clean`（补丁文本不含 `strcpy/sprintf/gets/strcat`）。
- 产物：`bin/zsync` 190912 bytes、`bin/zsyncmake` 178624 bytes，另含 `licenses/COPYING`。

接入上游测试后：`/storage/Users/currentUser/ohpc-ci-shadow/runs/6944c01e7b49-20260927T043951Z-28630`

- L0 pass、L1 pass、L2 pass、L4 pass、L5 pass；Total 1、Success 1、Pass rate 100.0%。
- 日志证据：`perl/5.42.2` 由 `conan create` 自动从 `ohpcd` 下载（17.0 MB），build 阶段出现 `check-zsyncmake` 的 RUN 行。

补齐全部 4 个上游用例后（最终）：`/storage/Users/currentUser/ohpc-ci-shadow/runs/73829e31d9b4-20260927T101847Z-32376`

- L0 pass、L1 pass（`upstream tests + test_package executed`）、L2 pass、L4 pass、L5 pass；Total 1、Success 1、Pass rate 100.0%。
- 日志证据：build 阶段共 7 条 RUN 行 —— 3 个单元测试各「编译 + 运行」，外加 `check-zsyncmake`：

  ```text
  RUN: cd <src>/librcksum && clang -I. -I.. -DHAVE_CONFIG_H -o <build>/upstream-tests/md4test md4test.c md4.c
  RUN: cd <src>/librcksum && clang ... -o <build>/upstream-tests/rsumtest rsumtest.c rsum.c hash.c range.c state.c md4.c ../progress.c
  RUN: cd <src>/libzsync  && clang ... -o <build>/upstream-tests/sha1test sha1test.c sha1.c
  RUN: <build>/upstream-tests/md4test
  RUN: <build>/upstream-tests/rsumtest
  RUN: <build>/upstream-tests/sha1test
  RUN: cd <build>/upstream-tests && top_builddir=<build>/bin srcdir=<build>/upstream-tests sh -e <src>/check-zsyncmake
  ```

  三个单元测试均为自校验（md4/sha1 比对 RFC1320/RFC3174 向量，`rsumtest` 失败 `exit(1)`），任一非 0 退出都会让 `conan create` 中断。
- 关于 L1c 的判定方式：它只是对构建日志做 `grep -E "make.*check|ctest|meson test|pytest"`，本次命中的行是补丁文件名（`...make-use-writable-temp-dir.patch, 0002-check-zsyncmake-...`）。该判定所陈述的事实（上游测试在 build 阶段执行）由上面的 RUN 行独立证实，不再依赖文件名巧合。

## PC 鸿蒙化审查（rule4）

`Septest` 2026-09-27 17:46 的审查给出 `VERDICT=FAIL`，唯一不通过项是 **rule4 少报**：

```text
实测 N=4，声明 N=1 → ❌ 少报（实测 4 > 声明 1）→ 不通过
```

修正方式：按三个 `Makefile.am` 的 `TESTS` 口径把上游用例数改为 **4**，并在 `build()` 中真实执行全部 4 个，通过率改为 `[4/4]（100%）`。教训：**统计上游用例数必须遍历子目录的 `Makefile.am`**，只看顶层会漏报 `c/librcksum/`（`md4test`、`rsumtest`）和 `c/libzsync/`（`sha1test`）。

## 积分赛事 PR 测试填写

- 上游测试用例数：**4** —— `md4test`、`rsumtest`（`c/librcksum/Makefile.am` 的 `TESTS`）、`sha1test`（`c/libzsync/Makefile.am` 的 `TESTS`）、`check-zsyncmake`（`c/Makefile.am` 的 `TESTS`）。
- 上游测试通过率：`[4/4]（100%）`。配方在 `build()` 中编译并运行这 4 个用例（`tool_requires("perl/5.42.2")` 提供 perl 解释器，`ohpcd` 远端已有该包），任一非 0 退出都会使 `conan create` 失败，因此通过率由 CI 强制保证，不是手工记录。
- 上游测试用例修改：**是**，1 处 —— `c/check-zsyncmake` 的期望 cksum `4103379992` → `3456223344`，回填上游提交 `a5cb28f`（见补丁 0002）。其余 3 个单元测试未改动。
- 适配后新增/替代 smoke 用例通过率：`[2/2]（100%）`，分别执行 `zsync -V` 和 `zsyncmake -V`。

> ⚠️ 统计上游用例数时不要只看 `c/Makefile.am`。`TESTS` 分散在三个子目录的 `Makefile.am` 中，只统计顶层会得到 1，而实际是 4 —— 这正是 PC 鸿蒙化审查 rule4「少报」判定所依据的口径。

## 下一步

```sh
CI_PACKAGES="archives/z/zsync/0.6.3" zsh ci/conan/build_and_test.sh
```

Shadow CI 会拒绝有未提交改动的目标包（`git status --porcelain -- archives/z/zsync/0.6.3` 必须为空），运行前先提交。真机隔离仓库为 `$HOME/ohos-users/zsync/zsync-0.6.3/repo/build_in_harmonyos`，可用 `$HOME/ohos-users/zsync/zsync-0.6.3/retry-shadow.sh` 在设备锁繁忙时重试。
