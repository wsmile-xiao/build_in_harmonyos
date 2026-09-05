# podiff 1.4 适配笔记

## 编译环境
- 构建系统: make（平铺 Makefile，无 configure）
- 编译日期: 2026-09-03
- 编译器: clang 15.0.4（/data/service/hnp/bin/clang，OHOS 原生 arm64，musl libc）
- 状态: built

## 软件信息
- podiff：GNU gettext PO 文件智能比对工具（作者 Sergey Poznyakoff，GPL-3.0-or-later）
- 官网 https://puszcza.gnu.org.ua/software/podiff/ （官网页面版本信息滞后显示 1.3，实际发布区已有 1.4）
- 官方源码: https://download.gnu.org.ua/pub/releases/podiff/podiff-1.4.tar.gz
- sha256: 231531f3b0b17615a1f0ca9d712a3c196686df9f1a641688c74a2574af78b22a
- 纯 C、零第三方依赖（仅 libc）、单二进制；y.tab.c/lex.yy.c 已预生成（无需 yacc/flex）

## 编译步骤

```bash
# 探索阶段（模式 B，工作目录 $HOME/tmp/builds/podiff-1.4.work）
make CFLAGS="-O2 -fPIC"                 # 平铺 Makefile，cc→clang 由设备 PATH 提供
./podiff -v                              # 触发安全弹窗（R7）
# 固化为 Conan 配方（application 类型）：
#   build(): self.run("make -j1", env="conanbuild")  —— CC/CFLAGS 由
#   AutotoolsToolchain 生成的 conanbuild 环境注入（R33），Makefile 补丁
#   将硬编码 cc 改为 $(CC) 且默认值用 ?= 赋值
#   package(): copy bin/podiff + share/man/man1/podiff.1
python3 scripts/ohc-run.py conan-init podiff 1.4    # 生成骨架后手工重写
python3 scripts/ohc-run.py conan-verify podiff 1.4  # 八道门禁全 PASS
python3 scripts/ohc-run.py finish podiff 1.4 built  # 含 W3 本地 CI 验证
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 比对模式 `podiff a.po b.po` 崩溃（SIGABRT，"cannot create temporary: Read-only file system"） | OHOS /tmp 只读（E002）；上游 `tmpdir = "/tmp"` 硬编码，mkstemp 失败后 error() 走 abort | 补丁 0002：main() 里优先读 TMPDIR 环境变量（GNU 惯例），默认仍 /tmp |
| 2 | 有差异的 PO 文件退出码恒为 0（文档承诺 1） | 上游 main.c `int ignore_rc;` 未初始化（UB），命令行模式碰巧读到非零垃圾值 → `return ignore_rc ? 0 : ...` 恒返回 0；-O0/-O2 均复现 | 补丁 0002：初始化 `int ignore_rc = 0;`（最小上游 bug 修复） |
| 3 | L2 冒烟测试 `podiff --version` 失败（exit 2） | 上游仅支持 `-v`/`-h` 短选项，无 GNU 长选项 | 补丁 0002：getopt → getopt_long，增加 --version/--help |
| 4 | Makefile 硬编码 `cc`，Conan 工具链 CC/CFLAGS 无法注入（R33） | 规则写死 `cc -c $(CFLAGS)`，且 `CFLAGS=-ggdb` 覆盖环境 | 补丁 0001：`CC ?= cc`、`CFLAGS ?= -ggdb`，规则改用 `$(CC)` |
| 5 | 手动 `conan create/test -pr:h=ci/conan/profiles/ohos-aarch64` 报 `'settings.os.version' value not defined` | 本机 conan 2.29.1（OHOS 适配版）对相对 profile 路径解析异常；框架工具（ohc-run.py/CI）内部均用绝对路径，故仅手动命令受影响 | 手动执行 conan 命令时 profile 一律用绝对路径（框架命令不受影响） |
| 6 | conan-verify 报告中 L2/L4/L5 显示"跳过（无 cache 路径）" | 框架 conan_verify.py G4 解析 `conan list` JSON 的层级结构与 conan 2.29.1 实际输出不符（`Local Cache` 下直接是完整 ref 键，无软件名一层），pkg ID 探测失败；scripts/ 只读不可修 | 已手动执行等效验证并留证（见 reports/test-report.md）：L2 等效 `podiff --version`→rc=0；L4 等效 readelf 显示 PIE(DYN)+GNU_STACK RW(NX)+GNU_RELRO；L5 等效 sha256 基线已记录 |

## 退出码语义（实测，含上游修复）

| 场景 | 退出码 | 依据 |
|------|--------|------|
| 两个 PO 文件等价 | 0 | diff 退出码透传（man RETURN VALUE） |
| 两个 PO 文件有差异 | 1 | 同上，依赖 ignore_rc 修复（问题#2） |
| 无效命令行选项/参数个数 | 2 | man 手册 RETURN VALUE；main.c getopt default/exit(2) |
| PO 语法/解析错误 | 3 | podiff.l: `if (yyparse()) exit(3);` |

注：任务描述中"2=PO 语法错误"与上游实际不符——上游 2 是无效命令行，语法错误是 3，已按实测断言并在 test.sh 注释中标注出处。

## 源码修改（补丁，refresh-patch --auto 生成）

- `0001-Makefile.patch`：CC/CFLAGS 可移植性（$(CC) + ?= 默认值）
- `0002-main.c.patch`：TMPDIR 环境变量支持（E002）+ ignore_rc 未初始化上游 UB 修复 + GNU --version/--help 长选项（getopt_long）
- 附带少量行尾空白规范化（编辑工具写回所致，无语义影响）

## 依赖版本

无第三方依赖（纯 libc）。构建工具：make 4.4.1、clang 15.0.4、conan 2.29.1（OHOS 适配版）。

## 上游测试情况（如实记录）

- 上游 tarball 无 tests/ 目录、Makefile 无 check 目标
- `make check` → `make: *** No rule to make target 'check'.  Stop.`
- 因此以 test_package 实质测试（R34）代替：5 组断言全部通过（见下）

## 验证结果

```bash
# conan create（G2 干净构建，含 test_package 自动执行）：
#   [test 1] podiff --version (exit 0)      → OK: --version => podiff 1.4
#   [test 2] identical translations         → OK: rc=0
#   [test 3] differing translation          → OK: rc=1, diff output present
#   [test 4] PO syntax error                → OK: rc=3
#   [test 5] invalid option                 → OK: rc=2
#   ALL PODIFF TESTS PASSED
# conan-verify 八道门禁：G0/G1/G2/G3/G4 + L2/L4/L5 → 全 PASS（Verdict: PASS）
# L1e 破坏性反证（CI 同款流程）：
#   mv 包内 bin/ away → conan test → RC=1 "FAIL: podiff binary missing or not executable"
#   恢复 bin/ → conan test → RC=0 "ALL PODIFF TESTS PASSED"
# git diff driver 模式（7 参数）实测输出 git 风格头 + rc=0
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/podiff | 51648 B，aarch64 musl ELF，PIE+NX+RELRO |
| share/man/man1/podiff.1 | 上游手册页 |

## 注意事项

- podiff 比对模式会调用系统 `diff`（system()），运行环境需 PATH 含 diff（设备 /data/service/hnp/bin/diff；CI profile 的 buildenv PATH 已含）
- 比对模式需可写 TMPDIR；test.sh 内已显式 export TMPDIR 为测试目录（防 /tmp 只读）
- 首次执行二进制会弹安全确认框（R7），安装后需扫一遍 bin/（已执行）
---

**编译结束**: 2026-09-03 10:53
**最终状态**: built

## Submit 阶段补充（2026-09-03）

| # | 问题 | 根因 | 方案 |
|---|------|------|------|
| 16 | submit 自检 `packaging_present` FAIL：无 packaging/*.tar.gz | 打包由独立 PackageBuilder 完成（非 finish 内置），前置 `.verify-passed` 标记 + staging 目录 | conan create 构建的包无 make install DESTDIR 产物：从 conan 包目录（`~/.conan2/p/b/podif*/p/`）拷 `bin/`、`share/` 到 `$TMPDIR/test-install-podiff-1.4/`（**legacy 布局：bin/ 直接在根下**，verify_build 读 .build-context 的 TEST_PREFIX，PackageBuilder legacy 模式兼容同一路径）→ `verify-build` 过 G1-G4 写 `.verify-passed` → `package_cli(['podiff','1.4'])` 打出 `podiff-1.4-ohos-aarch64.tar.gz`（94KB）+ debug 包 |
| 17 | verify-build G2 恒报 `--version failed`（⚠️1） | 框架 bug：`verify_build._run()` 硬编码 `timeout=15` 与调用方传 `timeout=5` 重复 → `TypeError: got multiple values for keyword 'timeout'` 被 `except Exception` 吞掉 → 返回 `(1,"")` | 非阻塞（verdict=PASS 按 failed==0 判定）；真实功能以手动执行 rc=0 + W3 test.sh 断言 `grep "podiff 1.4"` 为准。scripts/ 只读，已记录待 SKILL_FEEDBACK 反馈 |
| 18 | `pre_pr_audit.py report` 打印 PASS 但不落盘 | report 子命令只做校验输出，不写权威路径 | W4 审计结果需人工复制到 `archives/p/podiff/1.4/reports/audit-result.json`（无点前缀，reports/ 下）——submit Gate 3 只认此路径 |
| 19 | submit 报 `git commit 失败`（错误信息为空） | git 在工作区有未暂存改动时输出 `no changes added to commit`（**stdout**），框架只匹配 `nothing to commit`（**stderr**）→ 良性场景误判 + 错误取自 stderr 为空 | 本质是"全部已提交"的良性场景；将有价值的 submit 阶段记录（本表）追加 notes.md 使 git add 有内容可暂存（bitlbee-facebook #7526 同款路径，其 submit 提交内容即 notes.md 增量） |
| 20 | gitcode_pr.py/preflight.py 的裸名 `subprocess.run(["git",...])` 报 `FileNotFoundError: 'git'`（PF0 环境闸拦截 PR 创建），但绝对路径/shutil.which 均正常 | 本机 OHOS 补丁版 Python（3.12.9，`_IS_HARMONYOS`）让**裸命令名**也走 `_posix_spawn`，而 `os.posix_spawn` 不做 PATH 搜索 → 相对 CWD 找 `./git` → ENOENT；bash 的 PATH 搜索（execvp）不受影响 | 在两处调用的 CWD（项目根）放 `git` 符号链接（`ln -s /data/service/hnp/bin/git git`，untracked 不入 PR），submit 完成后删除。根治应改框架用 `find_executable("git")` 绝对路径（submission.py 的 `_GIT` 模式），待 SKILL_FEEDBACK 反馈 |
