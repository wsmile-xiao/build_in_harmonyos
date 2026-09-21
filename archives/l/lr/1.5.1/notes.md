# lr 1.5.1 适配笔记

## 编译环境

- 构建系统: makefile（上游 1.5.1 为纯 POSIX Makefile，无 configure，单翻译单元 lr.c）
- 编译日期: 2026-09-19
- 编译器: clang 15.0.4（OHOS SDK 26.0.0.18 native/llvm，来自 conan profile 的 `tools.build:compiler_executables.c`，目标 aarch64-linux-ohos / armv8）
- 任务: 平台贡献任务 #8564（开源鸿蒙PC专项积分赛），分支 `feat/lr-1.5.1`，语言预检 R47 detected=c（c↔cpp 兼容族，exit 0）
- 状态: built（本地验证通过，未 upload；合入 main 后由 release 流水线上传制品仓）

## 上游测试申报表（R51 三步法之"清点"）

| 清点项 | 结果 | 证据 |
|--------|------|------|
| `tests/` 等测试目录数 | 0 | `tar tzf lr-1.5.1.tar.gz` 共 14 个条目 = 12 个普通文件 + 2 个目录项（`lr-1.5.1/`、`lr-1.5.1/contrib/`）：LICENSE、Makefile、NEWS.md、README.md、`_lr`、contrib/{lr.el,lr.vim,lrls,lrocate}、lr.1、lr.c、lr.png |
| Makefile 中 test/check 目标 | 无 | `grep '^[a-zA-Z_.-]*:' Makefile` → `all:`、`clean:`、`install:`、`FRC:` |
| 测试框架注册数（ctest/pytest 等） | 0 | 无 CMakeLists.txt / meson.build / configure.ac；上游 README「Installation」仅 `make all` / `make install` |
| 文件名匹配 `*test*` | 0 | 在解压后的源码目录 `find . -iname '*test*'` |

结论：**上游 N=0，无任何官方测试用例**（不是"没环境跑不了"，而是上游确实不携带测试）。按赛事规则第 6 条，适配补全行为回归套件 `test_package/test_lr.sh`（43 条断言 A01–A43，真实执行安装后的二进制），清点证据同时登记在 `test_package/MANIFEST.yml`。

## 编译步骤

```bash
# 探索编译（模式 B，源码未做任何修改）
cd $BUILD_SRC_DIR                       # tmp/builds/lr-1.5.1.work
make -j1 CC=<ohos-clang>                # → ./lr（ELF64 AArch64，DYN/PIE）
./lr --version                          # rc=2，Usage 走 stderr（上游无 --version）
./lr                                    # 递归列目录、-1/-d/-A/-t/-f/-l 全部工作正常

# conan 配方验证与收尾
python3 scripts/ohc-run.py conan-verify lr 1.5.1 --profile ohos-aarch64-device
CONAN_PROFILE=ohos-aarch64-device zsh ci/conan/build_and_test.sh archives/l/lr/1.5.1
python3 scripts/ohc-run.py finish lr 1.5.1 built
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 设备直连 `https://github.com/.../archive/...` 下载失败：`SSL: UNEXPECTED_EOF_WHILE_READING` | 设备网络对 github.com 域名的 TLS 通道被干扰（同机 `codeload.github.com` 可达，返回 200） | 走 `init-build` 的 tarball 缓存分支：先从 `codeload.github.com` 取同一 tag 归档，放入 `$TMPDIR/builds/lr-1.5.1.tar.gz` 后再跑 init-build（命中"已存在则跳过下载"）。**归档 conandata.yml 仍声明官方 `github.com` tag URL（R39/PF7，不使用搬运源）**；两条独立通道（设备 codeload + 本机 github.com）下载哈希一致：`3c9337b9…27cc4a` |
| 2 | `init-build` 把项目探测为 autotools，conan-init 模板不适用 | 启发式仅按 URL/常规文件判断，lr 只有裸 Makefile | 按 `templates/conanfile-makefile.py.tmpl` 与 `archives/u/unifdef/2.12` 先例手写纯 make 配方，版本级 manifest 的 `build.system` 记为 `makefile` |
| 3 | 上游 `make install` 会把二进制装到写死的系统前缀（Makefile 里 `PREFIX` 的默认值），且依赖 `install(1)` | 该默认前缀是共享系统目录；实测设备 **toybox 不提供 `install(1)`**（`make install` 在 Makefile:19 以 127 退出）；向共享前缀写入亦违反 R49 | `package()` 直接 `copy()` 三件产物到 `self.package_folder`（bin/lr、share/man/man1/lr.1、share/zsh/site-functions/_lr）并 `os.chmod` 0755；不运行上游 install 目标，配方与测试文件中不出现系统前缀字面量 |
| 4 | CI L2 冒烟以 `--version` 探测可执行文件 | lr 1.5.1 的 getopt 串为 `01ABC:DFGHLQPST:UWXde:f:lho:st:x`（含字符 `l`，即 A25 断言的 `-l` 长格式，不接参数），无长选项 `--version`/`--help`；`-h` 是"人类可读大小"开关（`case h: hflag++`）而非帮助，Usage 只在未知选项的 default 分支打印并以 2 退出 | L2 为非阻塞项：在 `build()` 内实际执行一次产出的 ELF（`./lr -1 -f '%f\n'` 并在 Python 侧断言列出 lr.c）+ 断言 `e_machine == 0xB7`，把"能编译"升级为"能运行且是目标架构"；退出码语义（1=顶层路径无法 stat，2=用法错误）由 test_package 的 A38 断言覆盖 |
| 5 | 回归用例 `-t 'name ~ "log$"'` 报 `lr: parse error: invalid string operator` | lr 的字符串/正则运算符集合是 `=~ !=~ !~ =~~ !=~~` 等，单独的 `~` 非法（README 的 EBNF 中 `<strop>` 不含裸 `~`） | 改用 `=~`；同时 `-t 'name =~ "\\.log$"'` 也匹配不到 —— lr 字符串不支持反斜杠转义，两个反斜杠被当作一个字面反斜杠。最终用例写作 `"log$"`（已记入 knowledge_gained） |
| 6 | 回归用例 `-os/-oS` 断言取不到首行 | `-f '%s'` 未带换行时，lr 把全部记录输出在同一行（列宽右对齐），`head -1` 取到整串 | 格式串改为 `-f '%s\n'`（lr 的 `%` 格式支持 `\n` 转义）后按行断言 |
| 7 | 断言若写死 mode/大小/人类可读值的期望，会与设备 umask、HMDFS 权限语义冲突 | HMDFS 上 `chmod` 不生效（E046），umask 随执行环境变化 | 期望值全部在运行时独立反查：`SZ_BIG=$(wc -c < big.bin)`、`EXP_H_BIG=$(awk …)`、`N_LEVEL1=$(find -maxdepth 1 …)`、模式取 `lr -f '%m'` 后**同时做正向与负向对照**（`mode = 000` 必须不命中），既保证 umask 无关又不让断言自我循环 |
| 8 | `%Y`（文件系统类型）在 OHOS 上是否有值 | lr 走 `#if defined(__linux__)` 的 `setmntent(_PATH_MOUNTED)`→回退 `/proc/mounts` 分支；musl 提供 `mntent.h` 与 `_PATH_MOUNTED` | 真机实测 `%Y` 返回 `hmdfs`。但上游 `fstype()` 在查不到挂载表时会回退打印**数字设备号**，因此"非空"恒真 —— 断言 A35 额外要求结果不含数字，才能真正证明走的是挂载表分支（`%x` 输出 `@` 同理证明 xattr 路径可用） |
| 9 | 本地 CI 门禁 L1 `conan create` 失败：`NotADirectoryError: .../predl_cache/a12a604a_lr/archive/refs/tags/v1.5.1.tar.gz`，conan 侧先报 `Could not download from <门禁注入的镜像前缀>/<本地缓存路径>/...`（镜像前缀与缓存路径均由门禁自行注入，非本包声明） | `ci/conan/build_and_test.sh` 的"镜像重写 + 预下载"会抓取 conandata.yml 内**所有** http(s) 字面量（含注释），按文件名落 `predl_cache/<hash>_<filename>` 后把 URL 回写为本地缓存路径协议。我在注释里写的裸仓库地址恰是 `sources.url` 的字符串前缀，回写时把真实 URL 的前半段替换成了那个缓存文件路径 | 从 conandata.yml 移除一切额外 URL（只保留 `sources.url`），并在文件内注释登记规避理由；已记入 knowledge_gained，供后续使用 GitHub tag 归档 URL 的包直接避开 |
| 10 | 深度过滤断言 A41 首轮失败（`lr -t 'depth = 1'` 得 9，`find` 预计算得 6） | fixture 目录内文件数会随断言推进变化：A38 为捕获 stderr/stdout 在 fixture 根留下 `e1.err/e2.out/e2.err` 三个文件 | 期望值改为**在断言当场**重新 `find . -maxdepth 1 ! -path .` 统计，而不是在 fixture 创建时预算 |
| 11 | A37（man 手册 + zsh 补全完整性）按 `sh test_lr.sh` 单独复现时必失败 | 该断言依赖外部注入的 `LR_PACKAGE_FOLDER`，未设置时无回退 | 增加自洽回退：由 PATH 上 `lr` 的位置反推包目录（`dirname $(command -v lr)/..`），并让 MANIFEST.yml 的 `command` 字段写出与 `test_package/conanfile.py` 一致的完整命令行；同时在 A01 断言"PATH 解析到的正是被测包的 bin/lr"，避免宿主同名命令串扰 |

## 源码修改

无。零补丁（`patches/` 不存在，`conandata.yml` 为 `patches: {}`），无平台宏（R8/PF5：配方与测试文件中不出现任何平台宏定义或注入）。lr.c 只用 ANSI C + POSIX 接口，未经修改即可在 OHOS aarch64 上编译运行；`#ifdef __linux__` 分支（xattr、mntent）在 OHOS 上编译通过且行为正确，无需屏蔽。

## 依赖版本

无（W0 依赖检查：`requires`/`tool_requires` 均为空；纯 C 只链接系统 libc。构建期只需要 make + clang，二者由 CI worker 与 conan profile 提供）。

## 验证结果

```text
# 上游测试：N=0（无任何上游用例，见上文申报表），故不存在"上游通过率"
# 适配补全回归（test_package/test_lr.sh）：43/43 PASS
#   1) 设备侧独立验证（对交叉编译产物 + 已安装布局，2x2 四种跑法均 rc=0）：
#        toybox sh        × 设置 LR_PACKAGE_FOLDER  → 1..43 / pass=43 fail=0 total=43
#        toybox sh        × 不设置（脚本自洽回退）   → 同上
#        harmonybrew bash × 设置 LR_PACKAGE_FOLDER  → 同上
#        harmonybrew bash × 不设置                  → 同上
#   2) 破坏性自检（本地复刻 CI L1e）：lr 换成无输出 exit 0 的 stub → pass=8 fail=35，rc=1；
#        从 PATH 移除 lr → pass=7 fail=36，rc=1
#   3) fixture 目录残留（trap 清理后统计）：0
#   4) conan create 内真实执行（test_package，W3 门禁日志，完整 43 行 TAP 见 reports/test-report.md §4.1）：
#        RUN: LR_PACKAGE_FOLDER="<pkg>" $CONFIG_SHELL test_lr.sh
#        1..43
#        # lr functional assertions: pass=43 fail=0 total=43
```

- `conan-verify`（profile `ohos-aarch64-device`）：**PASS**，G1/G2/G3/G4 全通过；G0 因上游为纯 Makefile、构建系统未被识别而跳过预查询（非阻塞）；L2/L4/L5 在设备侧为 `skip: 无 cache 路径`（本地限制，交由平台 CI 复验）。工具报告生成于 `reports/conan-verify-report.md`（本地证据，按 review-memory #19 不入 PR）。
- `finish` step [5/10] 的 W3 本地 CI 阻塞门禁：**通过**，`.ci-result.json`（工具写入，含 `integrity_hash` 与 `log_sha256`）`exit_code=0`；与平台同源的 `ci/conan/build_and_test.sh` 输出 `L0/L1/L1e/L4/L5 pass`、`L2_RESULT=skip: lr version/help failed`。
- 平台 L2 冒烟（`--version`）不适用：上游 CLI 无该长选项，`-h` 亦为"人类可读大小"开关而非帮助（见问题表 #4）；已用 `build()` 内的真实执行冒烟 + ELF 架构断言 + A38 退出码断言替代。

## 设备端 staging 等价验证（上游 install 目标不可用的处置）

上游 `make install` 在本设备直接失败——toybox 不提供 `install(1)`：

```console
$ make -j1 CC=<ohos-clang> install DESTDIR=$TEST_PREFIX PREFIX=/usr
mkdir -p $TEST_PREFIX/usr/bin $TEST_PREFIX/usr/share/man/man1 $TEST_PREFIX/usr/share/zsh/site-functions
install -m0755 lr $TEST_PREFIX/usr/bin
make: install: No such file or directory
make: *** [Makefile:19: install] Error 127
```

因此按等价方式手工 stage 到隔离 DESTDIR（`PREFIX=/usr`，不触碰任何共享系统前缀）后执行验证：

```console
$ mkdir -p $TEST_PREFIX/usr/{bin,share/man/man1,share/zsh/site-functions}
$ cp lr $TEST_PREFIX/usr/bin/lr && chmod 755 $TEST_PREFIX/usr/bin/lr
$ cp lr.1 $TEST_PREFIX/usr/share/man/man1/lr.1
$ cp _lr $TEST_PREFIX/usr/share/zsh/site-functions/_lr
$ $TEST_PREFIX/usr/bin/lr -1 $TEST_PREFIX/usr      # rc=0，递归列出已安装布局
```

结论同时记录在 `.staging-verified`（本地标记，gitignored）；配方 `package()` 采用同样的直接 copy 策略，因此 CI 上不会出现对这一缺失工具的依赖。

## 有意保留的风格例外

- `test_package/test_lr.sh` 使用 `set -u` 而非 code-style §7 的 `set -euo pipefail`：A38 需要主动观察 lr 的非零退出码（1=顶层路径无法 stat，2=用法错误），`errexit` 会中断记录；且脚本首行为 `#!/bin/sh`（同一脚本要在 toybox ash 与 bash 下都跑通），`set -o pipefail` 非 POSIX，在 ash 上会直接报错。脚本头部注释已写明该理由。
- `conanfile.py` 的 `build()` 会把产出的 ELF 真实执行一次，并在 `arch=armv8` 时断言 `e_machine == 0xB7`：本仓口径为 native 编译（不使用 `--build/--host/--target`），该断言保证"在 armv8 profile 下产出的确是 arm64 二进制"，而不是依赖侥幸。

## 交付物

| 文件 | 说明 |
|------|------|
| bin/lr | 主程序（arm64 ELF，PIE） |
| share/man/man1/lr.1 | man 手册（上游原文，未改） |
| share/zsh/site-functions/_lr | zsh 补全脚本（上游原文，未改） |

## 备注

- W4 独立审计共进行四轮（上下文隔离的独立子任务，逐轮以 `pre_pr_audit.py generate` 的权威快照为输入），最终记录入库于 `reports/audit-result.json`：verdict=pass，P0=0 / P1=0 / P2=1 / P3=10。其中唯一的 P2（申报数字时效性）已用 W3 门禁日志的完整 43 行 TAP 内联到 `reports/test-report.md` §4.1 正面消解（该 TAP 来自含 `.hidsub` fixture 与强化判据的最终脚本）；其余 P3 为文档措辞与编号问题，已同步修订。
- 本地验证产物 `packaging/lr-1.5.1-ohos-aarch64.tar.gz` 由 conan 包目录手工打包（`ohc-run.py` 无 `package` 子命令），gitignored、不入 PR。
- W5（知识图谱完整性）在 `finish` step [7/10] 报出的字段缺失（E219/E253/E305）与 1229 条待审草稿均来自其他包的存量条目，非本包引入；本包 9 条 `knowledge_gained` 已写入版本级 manifest（`finish` step [7/10] 报的 `unreferenced=9` 即指这 9 条尚未提升为正式知识条目）。`gen_summary`（step [8/10]）在仓内当前版本崩溃（`'str' object has no attribute 'append'`），属工具缺陷。

---

**编译结束**: 2026-09-19 21:20
**最终状态**: built
