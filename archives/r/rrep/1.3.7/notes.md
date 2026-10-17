# rrep 1.3.7 适配笔记

## 编译环境
- 构建系统: autotools (configure + make)
- 编译日期: 2026-10-03
- 编译器: clang/clang++ (OHOS aarch64, profile ci/conan/profiles/ohos-aarch64)
- 状态: built (待真机 rule4 门禁验证后由 HMBS 统一提交)
- 认领身份: GitCode 用户名 gcw_uQ09W7jl, 队伍名称 干

## 上游信息
- 官方主页: https://sourceforge.net/projects/rrep/
- 源码包: https://download.sourceforge.net/rrep/rrep-1.3.7.tar.gz
- 大小: 1259919 字节, sha256 6179798a5e86833c455cf3e5f65ce6cc35f6d3888f47d74de8346e1bfa211fcd
- 许可证: GPL-3.0-or-later (COPYING)
- 发布日期: 2022-09-11 (SourceForge files)
- 内容: pattern replacement utility, bin_PROGRAMS = rrep (src/rrep.c + messages/bufferio/pattern + bundled gnulib lib/)

## 依赖分析
| 类型 | 名称 | 版本 | 说明 |
|------|------|------|------|
| requires | — | — | 零外部 C 库依赖 (bundled gnulib, --disable-nls 关闭 gettext) |
| tool_requires | — | — | 无 (tarball 自带 configure/Makefile.in, 无需 bootstrap) |
| bundled | gnulib | 随包 | lib/ 下 gnulib 模块编译为 libgnu.a, 静态链接进 rrep |

- configure 参数: `--disable-nls MAKEINFO=true`
- `--disable-nls`: AM_GNU_GETTEXT external 需要 libintl, OHOS 无系统 gettext, 上游 po/ 仅翻译目录, 关闭后不影响核心替换功能
- `MAKEINFO=true`: OHOS 无 makeinfo, doc/rrep.info 已随包生成, 跳过 version.texi 重生成 (仓库 45 例同范式)

## 上游测试审计 (R51)
- tarball 共 602 条目, 无 tests/ 或 test/ 目录
- 仅含测试字样的文件为 m4/progtest.m4 (autoconf 宏, 非测试)
- 所有 Makefile.am (顶层 SUBDIRS = lib src po doc, src/Makefile.am bin_PROGRAMS = rrep) 无 TESTS/check_PROGRAMS 声明
- configure.ac 无 AC_CONFIG_TESTDIR, 无 testsuite.at
- 结论: 上游无测试套件, `make check` 为 automake 空操作
- 配方 build() 因此不运行 make check (upstream_test_in_build: false), 功能由 test_package 7 项覆盖
- MANIFEST 声明: upstream_tests_exist: false, upstream_check_command 空 (无可运行的上游检查命令), upstream_test_total: 0, upstream_test_count_method: autotools_tests, 结构化 upstream_test_audit (tarball/条目/sha/扫描项/结论)
- 2026-10-04 真机 6/7 根因: case6 误将 -i 与 -F 联用, 但 src/pattern.c match_pattern() 的 OPT_FIXED 分支用大小写敏感 strstr() 且忽略 REG_ICASE, FOO 永不命中 foo; 改为正则模式 -i foo bar (regcomp REG_ICASE) 后可命中

## test_package (鸿蒙消费者功能用例, test.sh 7 项)
| # | 用例 | 命令 | 验证点 |
|---|------|------|--------|
| 1 | rrep_version_banner | rrep --version | rc=0 且 stdout 含 rrep 1.3.7 (PACKAGE_STRING 代入) |
| 2 | rrep_help_output | rrep --help | rc=0 且含 Usage + PATTERN (messages.c print_help) |
| 3 | rrep_stdin_filter | rrep -F foo bar < input | rc=0, stdin 两行 foo 全变 bar (无 FILE 时 stdin->stdout 路径) |
| 4 | rrep_file_replace | rrep -F foo bar file | rc=0, 文件原地改写 (hello foo->hello bar) |
| 5 | rrep_dry_run | rrep --dry-run -F foo bar file | rc=0, 文件保持 foo 不变 (模拟模式) |
| 6 | rrep_ignore_case | rrep -i foo bar file (regex mode, no -F) | rc=0, Hello FOO->Hello bar (REG_ICASE 路径) |
| 7 | rrep_recursive | rrep -r -F foo bar dir | rc=0, 子目录两文件全替换 (fts 递归路径) |

- 全部真实执行 + 输出/文件校验, 非存在性断言
- OHOS 约束: test.sh 零 $(...)/反引号, 临时文件全走 $TMPDIR 重定向
- 机器证据: test.sh 末尾输出 HMBS_UPSTREAM_TEST_RESULT (no_tests/0) + HMBS_TEST_PACKAGE_RESULT (discovered=7/passedCount=7)

## 源码修改 (配方内 Python 补丁, 无 patches/ 静态补丁)
- 原因: 静态 0001 锚定 GUESS 风格 `*:Minix` 上下文, 与 tarball 内 echo/exit 复古版 config.guess 不匹配, 真机 `apply_conandata_patches` 报 `source file is different - build-aux/config.guess (actual *:DragonFly:*:*))`。改按 rarian/radvd 范式在 build() 内做容忍式插入。
- `conanfile._patch_config_guess_sub_for_ohos(source_folder)`: 递归定位全部 config.guess/config.sub (build-aux/ 或根目录); config.guess 按 `aarch64:Linux` → `NetBSD` → `Minix` → `DragonFly` 多锚点回退插入 echo/exit 风格 `*:HarmonyOS` 分支 (输出 *-unknown-linux-ohos, aarch64/arm/x86_64/i686), 找到 HarmonyOS 标记则幂等跳过, 无锚点则 loudly 失败; config.sub 同时覆盖 2018 双白名单布局 (radvd 式 `linux-ohos*`/`-linux-ohos*`) 与新版 kernel-os 校验 + ohos-linux 三元组, 缺 linux-ohos 则报错。
- `conanfile._patch_configure_umask(configure)`: 纯字符串删除 `umask 077 && ` (不限行上下文, 任意 autoconf 复古版适用), 解决 HMDFS 强制 setgid 下 `umask 077 && mktemp -d` 得 drwx--S--- 不可写 (E114)。
- 三处均无 __OHOS__ 平台宏 (R8/PF5), 可移植方式修复。
- 毒 shell 加固 (rarian/zurl 范式): 共享 profile 注入的 CONFIG_SHELL=/data/service/hnp/bin/bash 在迁移后真机不可达, configure[139] 重 exec 报 `inaccessible or not found` (Error 127)。generate() 经 build-scope save_sh 覆盖为 _resolve_shell() (/bin/sh 优先, 跳过 /data/service/hnp/ 前缀); build() 内 scrub configure 毒字面 + 文件头硬编码 CONFIG_SHELL/SHELL, 再经 Environment 上下文跑 configure/make; package() 前复 scrub 后 install。

## 构建记录
- 本轮为首轮工作树准备, 未在本地运行 conan (按任务守则, 真机验证由 HMBS 后台统一执行)
- 待 HMBS 真机预检: conan create (configure --disable-nls + make -j1 + test_package test.sh 7/7)
- 若预检报 shell/编译器/TMPDIR 等环境问题, 下轮按结构化日志修复

## 验证结果
- 本地: 新 conanfile.py `python -m py_compile` 通过, conandata.yml 已移除 patches 段 (静态补丁删除, 改为 build() 内 Python 容忍式插入, 不再依赖行上下文)
- 真机: 待 HMBS 预检返回后填写 (上游 0 用例 no_tests, 新增 7 用例通过率待实测, 不得猜测)

## 注意事项
- 本包为 application (CLI 工具), package_info 仅声明 bindirs, 无 libs
- software 级 commands.json type=tool 已创建 (R38, CI L0k)
- 版本号 1.3.7 为首次适配上游版本, 无后缀 (R37)
- 稀疏检出说明: Windows 本机因 archives/g/gama/2.29 含非法文件名 (CR 字符) 无法全量检出, 当前为 cone 稀疏 (ci/code/config/docs/feedback/knowledge/probes/references/scripts/skills/temp/templates/tests/.gitcode + archives/r), 与本任务无关目录未检出; 不影响 PR (单包 archives/r/rrep), HMBS Linux 侧可全量处理
