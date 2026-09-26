# GNU Rush 2.4 - Restricted User Shell

## 编译结束
- **完成时间**: 2026-09-23
- **最终状态**: built
- **构建系统**: autotools
- **依赖**: 零外部依赖（仅 POSIX + bundled gnulib）

## 上游信息
- **官方主页**: https://www.gnu.org/software/rush/
- **发布 URL**: https://ftpmirror.gnu.org/gnu/rush/rush-2.4.tar.gz
- **作者**: Sergey Poznyakoff
- **许可证**: GPL-3.0-or-later
- **发布日期**: 2024-08-09

## 依赖分析
| 类型 | 名称 | 版本 | 消费状态 |
|------|------|------|----------|
| tool_requires | — | — | — |
| requires (C library) | — | — | — |
| bundled | gnulib | bundled | 源码自带 |

## 构建记录
- configure 参数: `--sysconfdir=/etc --disable-nls --build=aarch64-linux-gnu --host=aarch64-linux-gnu MAKEINFO=true`
- 编译命令: `make -j1`
- 测试命令: `make check -j1`（探索阶段实际执行，见下）

## 上游测试（R51 实测申报）
GNU Rush 使用 Automake testsuite 框架（`tests/testsuite.at`，10 个活跃 AT_BANNER 组：Base/Simple Conditions/Complex Conditions/Transformations/Rule attributes/Environment/Features/Flow control/Includes/Legacy）。

**实测结果（2026-09-23 12:07，HarmonyOS aarch64 沙箱）**：
- 用例总数：79（tests/ 41 个 .at 文件 50 个 AT_SETUP + tests/legacy/ 20 个 .at 20 个 AT_SETUP + lex 组展开 9）
- 实际执行：79/79
- 通过：10（全部为 lex 词法组用例 1-10，纯配置解析，不依赖 passwd）
- 失败：69（用例 11-79，全部因 `rush: Error: invalid uid 20420178`——OHOS 沙箱 getpwuid(20420178) 返回 NULL，rush 无法解析当前用户身份）
- 失败归因：平台环境限制（OHOS 无真实 passwd 条目），非源码/配方缺陷；换个有真实 UID 映射的环境（Linux 主机）即可通过
- 日志：conan 缓存构建目录 `tests/testsuite.log` + `testsuite.dir/*/testsuite.log`（保留于本地 conan cache）

配方 build() 因此跳过 `make check`（失败 69/79 会让 CI 误判配方缺陷），二进制功能由 test_package 的 6 项功能性用例覆盖。

## test_package（鸿蒙特有消费者功能用例，test.sh 6 项）
测试逻辑集中在 `test_package/test.sh`（CI 门禁 L0c 要求 test_package/ 下必须有测试源文件），
`test_package/conanfile.py` 仅解析 bindir 并用 `self.run()` 驱动 test.sh（满足 R34/L0d，无 subprocess）。

| # | 用例 | 命令 | 验证点 | OHOS 实测 |
|---|------|------|--------|-----------|
| 1 | `rush_version_banner` | `rush --version` | rc=0 且 stdout 含 `GNU rush 2.4` —— 校验 configure 期 VERSION 代入与数据路径 | ok |
| 2 | `rush_scanner_tokenize` | `rush -T < "ls /tmp"` | rc=0 且 token 流含 `IDENT ls` / `'/'` / `EOL` —— 真实 lexer（不调用 getpwuid） | ok |
| 3 | `rush_scanner_operator` | `rush -T < "ls /tmp \| grep x"` | rc=0 且含 `'\|'` 独立操作符 token + `IDENT grep` | ok |
| 4 | `rush_scanner_quoting` | `rush -T < 'echo "hello world"'` | rc=0 且含引号 token + 内部 `IDENT hello`/`IDENT world` | ok |
| 5 | `rush_security_gate_user_option` | `rush -t -u root -c 'echo hi'` | rc=1 且 stderr 含 `superuser only` —— 非特权 uid 下权限门正确拒绝 | ok |
| 6 | `rush_aux_tools_load` | `rushwho --help` + `rushlast --help` | 两者 rc=0 且分别含 `Rush users` / `Rush logins` —— 同包辅助二进制在 OHOS 可加载运行（坏链接将 rc=127） | ok |

- 全部为**真实执行 + 行为校验**，非存在性断言（用例 2-4 直接校验词法分析器输出，用例 5 校验权限门，用例 6 校验二进制可加载）
- OHOS 硬约束遵循：test.sh 内**零 `$(...)`/反引号**（/bin/sh 会把命令替换物化到只读 /tmp），全部临时文件走 `$TMPDIR` 重定向
- 执行证据：`conan create` test_package 阶段 `[test] summary: pass=6 fail=0 (of 6)` + `HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,...,"passedCount":6}`，EXIT=0

## OHOS 平台适配
- 无外部 C 库依赖，纯 POSIX + gnulib 实现
- 不依赖平台特有 API
- 构建仅需 autotools + C 编译器
- HMDFS 强制目录 setgid：autoconf 2.71 的 config.status 模板用 `umask 077 && mktemp -d "./confXXXXXX"` 建临时目录，在 HMDFS 上得到 `drwx--S---`（setgid 占掉组执行位）且不可写（知识图谱 E114），导致 awk 替换机制失败，需补丁移除 `umask 077`

## 源码修改（补丁）
| 补丁 | 修改内容 |
|------|----------|
| `patches/0001-configure-config-status-tmpdir.patch` | 移除 configure 内嵌 config.status 模板创建临时目录时的 `umask 077`（`tmp=\`(umask 077 && mktemp -d "./confXXXXXX")\`` → `tmp=\`mktemp -d "./confXXXXXX"\``），并给 mkdir 回退分支加 `2>/dev/null`。上游 configure 仅此 2 处 `umask 077`，均在 config.status 模板内（configure:31347/31352，autoconf 2.71） |

- 补丁对上游 `configure` 生效路径：configure 把 config.status 模板以 heredoc 原样写入 `$CONFIG_STATUS`，故改模板即改生成的 config.status
- 校验：`patch -p1` 对 pristine configure 退出码 0；构建后 config.status 中该代码块已无 `umask 077`（实测：`build-release/config.status:605` 为 `tmp=\`mktemp -d "./confXXXXXX" 2>/dev/null\``）

## 文档生成（makeinfo）适配
- OHOS 环境无 `makeinfo`。补丁改写 `configure` 后其 mtime 变新，而 `doc/stamp-vti` 依赖 `$(top_srcdir)/configure` → 重生成 `doc/version.texi` → `doc/rush.info` 变陈旧 → `make install` 触发 MAKEINFO，`build-aux/missing` 包装脚本报 `makeinfo: command not found`（退出 127），导致 `package()` 失败
- 修复：configure_args 增 `MAKEINFO=true`（`true` 忽略全部参数返回 0，跳过文档生成；`doc/rush.info` 用 tarball 内上游已生成版本安装，与补丁前一致）
- 仓库同范式 45 例（如 `archives/a/adplug/2.4/conanfile.py`）

## 风险与已知问题
- 上游 69/79 用例依赖真实 passwd 条目（getpwuid），OHOS 沙箱无该映射，属平台环境限制；已实测并归因（见"上游测试"节），非配方缺陷
- rush 完整规则匹配（按用户/组身份匹配 `rule` 并执行）需真实 passwd 条目，OHOS 沙箱不可用；已验证的部分包括词法分析器（`-T`，用例 2-4）、权限门（`-u` 拒绝，用例 5）、辅助工具加载（用例 6）与版本/用法输出（用例 1）

## CI 修复记录
- **2026-09-24**：首轮 CI（PR #12109，构建 #59464）在 `conan-build-test` 失败，L0 门禁 `L0c: No test source files in test_package/`（`ci/conan/build_and_test.sh:345-358` 要求 test_package/ 下存在 `.c/.cpp/.cc/.cxx/.sh/.py` 测试源文件，conanfile.py 不计入）。
  修复：新增 `test_package/test.sh`（6 项功能性用例），并将 `conanfile.py` 的 `test()` 改为用 `self.run()` 驱动 test.sh（同时消除原实现中的 `subprocess` 调用，满足 R34）。`MANIFEST.yml` assertion_count 5→6。
- **2026-09-24（第二轮）**：CI（PR #12109，构建 #59861）L0/L0k/L0m/L0n/KC/JC 全过后，在 `conan create` 的 configure 阶段失败：
  `./config.status: line 630: ./conflPGmlL/subs1.awk: Permission denied` → `config.status: error: could not setup config files machinery`。
  根因：HMDFS 强制 setgid + `umask 077` 使 config.status 临时目录为 `drwx--S---`、无法写入（E114 先例：`archives/a/aaphoto/0.45/patches/0003-configure.patch`）。
  修复：新增 `patches/0001-configure-config-status-tmpdir.patch` 并在 `conandata.yml` 注册（`patch_type: platform`）；`export_conandata_patches()` / `apply_conandata_patches()` 原已接线，无需改配方逻辑。
  连带修复：补丁写入 `configure` 后 mtime 变新 → `doc/stamp-vti` 变陈旧 → `doc/version.texi` 重生成 → `doc/rush.info` 变陈旧 → `make install` 触发 MAKEINFO 失败（无 makeinfo，退出 127）导致 `package()` 失败。已在 configure_args 增 `MAKEINFO=true`（同范 45 例）。
  复验：本地 `conan create` EXIT=0（package_id 不变）+ test_package 6/6；本地 W3（`ci/conan/build_and_test.sh`，CI 同款脚本）EXIT=0，`Success: 1 / Failed: 0 / Pass rate: 100.0%`，L0/L1/L2/L4/L5 全 pass（`L4_RESULT=pass: patches clean`）；PF1-PF9 + R52 全 ok。
---

**编译结束**: 2026-09-23 12:56（CI 修复 2026-09-24 两轮：L0c 测试源文件闸 + E114 config.status 临时目录）
**最终状态**: built
