# edlin 2.24 适配笔记

## 软件信息

- 上游：FreeDOS edlin（SourceForge 项目 freedos-edlin），作者 Gregory Pietsch
- 主页：https://sourceforge.net/projects/freedos-edlin/
- 版本 2.24（2023-04 发布，FreeDOS Edlin 2.24 is out! 邮件列表确认）
- 许可证：GPL-2.0-or-later（COPYING 为 GPLv2 文本，源码头声明 "version 2 or (at your option) any later version"）
- 语言/构建：纯 C（4 个编译单元：defines.c dynstr.c edlib.c edlin.c），autotools（autoconf 2.71 生成的 configure + automake Makefile.in）
- 定位：MS-DOS EDLIN 行编辑器的功能克隆，可移植 POSIX 版；交互式 stdin 驱动命令（I 插入 / E 保存退出 / L 列表 / Q 退出 / D 删除 / M 移动 / C 复制 / S 搜索 / R 替换等）

## 编译环境

- 构建系统: autotools
- 编译日期: 2026-09-11
- 状态: built（本机前置适配完成，真机 shadow CI 待执行）

## W0 依赖检查结论

```text
依赖数量：0（运行时/构建时/测试时均无第三方依赖，仅 libc）
已满足依赖：无外部依赖
缺失依赖：无
是否需要拆分依赖适配：否
阻塞点：无
下一步：W5 真机 shadow CI
```

## 源码归档

- URL: https://downloads.sourceforge.net/freedos-edlin/freedos-edlin/2.24/edlin-2.24.tar.bz2
- tag/版本: 2.24 官方发布包（SourceForge 官方，非 PyPI/镜像）
- SHA256: ce3e64083744923cc38ae9ffe712fcc97d9256c9d973786bcc8018528e158fe7
- 格式: tar.bz2，解压后单根目录 edlin-2.24/，结构稳定
- 是否包含测试：否（无 tests/ 目录，Makefile.am 无 TESTS；与 guix/debian 打包结论一致）

## 源码与构建分析（W1）

1. `config.guess`/`config.sub` 为 2002-07-23 版，无法识别现代系统 → 以显式 `--build=aarch64-unknown-linux-gnu` 绕过（acct/6.6.4 同法），未打补丁。
2. `Makefile.in` 定义 `edlin_MANS = edlin.1.gz`，但 tarball 未附 man 页。因 `edlin_MANS` 不是 automake 标准 primary（标准为 `man_MANS`/`man1_MANS`），automake 未生成任何 man 安装规则，`make install` 不会触碰缺失文件 → 无需补丁。
3. 平台相关代码全部宏门控：DOS/Windows 头（process.h/io.h/conio.h/dos.h/jctype.h）由 `HAVE_*`/`_MSC_VER` 等控制；kitten/catgets 消息目录回退由 `USE_KITTEN`/`USE_CATGETS` 控制，默认未定义不编译；自带 nl_types.h 只在无系统 nl_types.h 时使用。Linux/OHOS 编译面为纯 POSIX。
4. configure 检查均为常规项（AC_FUNC_MALLOC/REALLOC、access/stat/strchr 等），musl 全部满足；malloc(0) 语义 musl 返回非 NULL，不会触发 rpl_malloc 替换。
5. `edlin_MANS` 之外无已知坑；`make -j1`（E074 规避，且本项目仅 4 个编译单元，无并行需求）。

## 上游测试核验（W1/W3）

- 上游无测试用例：源码包无 tests/ 目录，Makefile.am 无 TESTS 定义，tar 包内无测试文件
- `make check` 为空目标（automake 默认空目标，退出码 0，不运行任何用例）
- 上游测试通过率：`0/0（N/A，上游无测试用例）`
- 新增测试：test_package/test.sh 以 stdin 驱动安装后的 edlin，共 **8 个断言**：
  - T1（4 断言）：新文件 `1I`/文本/`.`/`E` 保存 → 退出码 0、文件创建、两行内容正确
  - T2（2 断言）：已有文件无操作 `E` → 退出码 0、内容保留
  - T3（2 断言）：`L`+`Q` → 退出码 0、stdout 打印缓冲区行

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 主仓库无法在 Windows 上新建 worktree checkout | origin/main 中 `archives/g/gama/2.29/patches/0002-dataparser-ungated.patch` 文件名含 CR 字符（`\r\r`），Windows 文件系统拒绝创建 | worktree 启用 sparse-checkout 本地排除该路径（仅本地 checkout 策略，不改任何仓库文件）；该坏文件属于 gama 库，待其维护者修复 |
| 2 | 2002 版 config.guess 不识别目标系统 | 上游打包时未更新 GNU config 脚本 | configure_args 显式 `--build=aarch64-unknown-linux-gnu` |
| 3 | edlin.1.gz 缺失可能导致 install 失败 | tarball 未附 man 页 | 核实 `edlin_MANS` 非 automake 标准 primary，无安装规则生成，`make install` 不受影响，无需补丁 |
| 4 | shadow CI r1：L0k `commands_json_r38` 失败 | CLI 工具包必须有软件级 commands.json（R38） | 新增 `archives/e/edlin/commands.json`（type=tool） |
| 5 | shadow CI r2：KC `permission denied: bash` | 隔离 job env.sh 生成的 PATH 缺 `/data/service/hnp/bin`（bash 所在地） | 重跑时外部注入 `export PATH=/data/service/hnp/bin:$PATH`（env.sh 继承外部 PATH） |
| 6 | shadow CI r3：configure 执行 `Permission denied`（exit 126） | E087：conan-home 位于 HMDFS，exec 域拒绝执行缓存目录里的脚本文件 | build() 改为 `/system/bin/sh "<configure>"` 显式调用（只读脚本不 exec），与 elfutils/0.195.1、dominion/2.8.2 同法 |
| 7 | r4/r5：config.status 写 `conf*/subs1.awk` Permission denied（mktemp 与 mkdir fallback 目录均失败） | conan-home HMDFS 深缓存路径对新目录写入有域限制；`~/usr/local/bin` 里的真 GNU mktemp 排在失败型 wrapper 之前建了 setgid 坏目录 | r5 内联 `PATH=<wrapper>:$PATH` 使 wrapper 绝对优先；r7 起改用 dominion 式 `~/tmp/edlin-build-2.24` 浅层副本构建，彻底绕开深缓存路径 |
| 8 | r7：test.sh `./test.sh` 无法执行（exit 126） | E087：HMDFS 检出脚本无执行位 | test_package 以 `/system/bin/sh ./test.sh` 绝对路径调用 |
| 9 | r8/r9：edlin 以 E/Q 退出时 Signal 6 (abort) | 两层原因：① E/Q 触发 `quitting()` 读 Y/N 确认，EOF 时 read_line 返回 0，main 里 `abort()`；② **上游 bug**：命令 switch 用 `tolower(*ip)` 匹配（大写 E 进入分支），但分支内 `exiting = (*ip == 'e') && quitting()` 检查原始大写字符 → 大写 E 保存文件后不退出 → stdin 耗尽 → abort（Q 分支无此检查故正常） | test_package 在 e/Q 后补 `Y` 确认行，保存退出用**小写 e**（switch 语义等价且 `*ip=='e'` 为真）；上游 bug 不打补丁，已在 test.sh 注释归因 |
| 10 | r2：KC `permission denied: bash` | 隔离 job env.sh 生成的 PATH 缺 `/data/service/hnp/bin` | 重跑时外部注入 PATH（见 #5） |

## 真机 shadow CI 最终结果（r10，2026-09-29）

```text
job_base = $HOME/ohos-users/codex/edlin-2.24-20260929（设备端脱敏）
run_dir  = $HOME/ohos-test-runs/codex-2.24-edlin-2.24-20260929-conan-20260929-115543-19803
exit code = 0
G0_RESULT = pass（知识图谱 541 条完整）
KC_RESULT = pass
JC_RESULT = pass: empty
L0_RESULT = pass: all checks passed（R37 版本无冲突 / R38 commands.json / R39 目录结构）
L1_RESULT = pass: upstream tests + test_package executed
           上游测试：make check 空目标 0/0（N/A，上游无测试套件）
           test_package：test.sh 8/8 断言通过（0 failing）
L2_RESULT = skip: edlin version/help failed（non-blocking —— CI 探测
           --version/--help，edlin 为交互式行编辑器，无版本/帮助开关，
           传入未知参数会进入编辑循环。属工具固有交互特性，非缺陷）
L4_RESULT = pass: no patches
L5_RESULT = pass: bin/ has content
Build Summary: Success 1/1, Pass rate 100.0%
```

## 本机验证（W4）

- 源码归档 SHA256 复核：ce3e…8fe7 ✅（下载后 Get-FileHash 与 conandata.yml 一致）
- Python 语法检查（py_compile）：conanfile.py ×2 ✅
- YAML 结构检查：conandata.yml / manifest.yaml / MANIFEST.yml ✅
- Shell 语法检查：bash -n test_package/test.sh ✅
- `git diff --check` ✅
- 变更范围 `git diff --name-only origin/main...HEAD` 仅含 archives/e/edlin/2.24/ ✅
- 本机（Windows）无 make/autotools 完整环境，conan create 本机全流程未执行，留待真机 shadow CI（如实记录，未把未执行的测试写成通过）

## 验证命令（真机 / shadow CI 下一步）

```sh
# 1) 隔离 job
sh "$HOME/bin/ohos-prepare-isolated-conan-job.sh" \
  --user codex \
  --job edlin-2.24 \
  --package archives/e/edlin/2.24 \
  --repo-source <existing-repo>

# 2) runner
sh "$HOME/ohos-users/codex/edlin-2.24/run-conan-heavy.sh"

# 等价本机验证（真机 conan 环境）：
conan create archives/e/edlin/2.24 \
  -pr:h ci/conan/profiles/ohos-aarch64 -pr:b ci/conan/profiles/default \
  --build=missing
```

重点记录：job 路径、run 目录、exit code、L0/L1（make check 空目标）/L2/L4（test.sh 8 断言）/L5 结果。

## 路径判断

- 路径 A 候选（1 分）：普通基础适配，纯 C + Autotools，无第三方依赖
- 测试框架候选：不申报（上游无测试用例）
- 新知识候选：worktree sparse-checkout 绕过含 CR 文件名坏文件为本轮工程问题，非 HarmonyOS 系统差异，不另立草稿

---

**最终状态**: built（本机前置完成；issue 编号待补；真机 shadow CI 待排队）
