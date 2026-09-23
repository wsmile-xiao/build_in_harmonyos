# alive 2.0.3 适配笔记

## 编译环境

- 构建系统: autotools（configure + make + make install）
- 编译日期: 2026-09-15
- 编译器: clang / clang++
- 状态: built（本地 create 通过前不标 published）
- 产物类型: application（命令行工具，bin/alive + info 文档）

## 上游调研

- 上游: https://www.gnu.org/software/alive/
- 源码: https://ftp.gnu.org/gnu/alive/alive-2.0.3.tar.xz
- SHA256: 8bf41150ade07b86a806ce40ce99509713e2abcc92c4182a8d961aa3cf757014（经 http 下载实测 187396 字节，与 GSRC sha256sums 一致）
- 内容: 共 30 个文件，主程序为 `src/body.scm`（Guile Scheme），configure 由 `@GUILE@` 替换生成可执行的 `src/alive`，以 `bin_SCRIPTS` 安装到 `$(bindir)/alive`；文档为 texinfo（`doc/alive.texi`）。
- 依赖: README 明确要求 GNU Guile（任意版本）+ 支持 `-n -c COUNT` 的 ping(1)。configure.ac 通过 `SNUGGLE_PROGS` 硬性检查 guile/guile-config，缺失即报错；通过 `AC_PATH_PROG([PING],[ping])` 检查 ping，并执行 `$PING -n -c 1 localhost` 探针。
- 测试: 源码包内无 test/tests 目录、无 `make check` 目标、无 gtest/pytest/criterion 绑定（详见 MANIFEST 审计）。Gentoo 的 ping-test 补丁为外部发行版补丁，非上游自带。

## 编译步骤

1. `get()` 解压官方 tar.xz。
2. `generate()`：AutotoolsToolchain 追加 `--disable-dependency-tracking`、`--build/--host=aarch64-unknown-linux-gnu`（跳过老 config 探测）、`alive_cv_nice_ping=yes`（Guix 同款预置，跳过构建期 ping 联网探针）；注入 fake makeinfo（解决 OHOS 无 texinfo 导致 doc 重建 Error 127，与 akku 同模式）；从 `guile/2.2.7.1` 依赖注入 PATH/GUILE/GUILE_CONFIG/GUILE_TOOLS/LD_LIBRARY_PATH/GUILE_LOAD_PATH/GUILE_LOAD_COMPILED_PATH；固定 `SHELL/CONFIG_SHELL=/bin/sh`、`GUILE_AUTO_COMPILE=0`。
3. `build()`：幂等替换 `configure` 内 `umask 077` 为 `022`（HMDFS 权限惯例）；修正 `conanbuild.sh` 尾部 SHELL 覆盖；`autotools.configure()` + `autotools.make()`。不调用 `make check`（上游无测试）。
4. `package()`：`autotools.install()`；将 `bin/alive` 首行绝对 guile shebang 改写为 `#!/usr/bin/env guile -s`（conanrun PATH 可解析，保证可重定位）；拷贝 COPYING 到 licenses。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 guile required but not found | SNUGGLE_PROGS 硬性要求 guile/guile-config | requirements 声明 guile/2.2.7.1，并经环境变量预置 GUILE/GUILE_CONFIG/GUILE_TOOLS 绝对路径 |
| 2 | doc 构建缺 makeinfo 报 Error 127 | OHOS 无 texinfo | fake-bin/makeinfo 触碰 -o 输出后 exit 0（与 akku 同模式） |
| 3 | 构建期 ping 探针依赖联网/localhost | configure 执行 ping 实测 | 预置 alive_cv_nice_ping=yes（Guix 官方同款），运行时仍要求系统 ping 支持 -n -c |
| 4 | 安装后 shebang 指向构建机绝对路径 | @GUILE@ 替换为构建期缓存路径 | package() 改写为 /usr/bin/env guile -s，行为不变、可重定位 |
| 5 | guile 依赖尚未 published | guile 2.2.7/2.2.7.1 当前为 built | 仍如实声明依赖（R36 要求先有依赖）；若 CI 判 dependency_missing，则按拓扑先发布 guile |

## 依赖版本

- guile/2.2.7.1（Conan 依赖，与 akku 同版本）
- 系统运行时: ping(1)（需支持 `-n -c COUNT`，如 iputils/inetutils；仅运行时需要，构建期已预置跳过）

## 验证结果

- 本轮为未提交工作树，等待 HMBS 后台真机预检（conan create + test_package + 上游审计）。
- test_package 设计：仅运行离线断言 `alive --help` / `alive --version`（不执行真实 ping，避免联网与常驻），断言输出包含版本与用法；同步输出 HMBS_TEST_PACKAGE_RESULT 与 HMBS_UPSTREAM_TEST_RESULT（no_tests）机器标记。
- 上游测试：经审计确认无测试框架，MANIFEST 与 marker 均声明 no_tests + reason，不伪造通过率。

## 注意事项

- 不要直接运行无参 `alive`（会进入 ping 循环）；测试仅用 --help/--version。
- 运行时需保证 guile 在 PATH 且能解析（conanrun 自动处理），以及系统提供 ping。
- GUILE_AUTO_COMPILE=0 避免 OHOS 上自动编译字节码失败（与 akku/guile 惯例一致）。

## 真机 test_package 修复轮（2026-09-16，readonly_tmp + Error 127）

- 现象：预检 test_package 阶段 `self.run(... test.sh ...)` 报 Error 127；
  日志显示 test.sh 已启动（bindir 解析与 guile 解析均打印），死在
  `alive --version` 一步；同时伴随
  `can't create temporary file /tmp/sh*.tmp: Read-only file system`。
- 根因（两处，均在 test.sh，不改测试口径，仍为 2 断言）：
  1. `VOUT="$(run_alive --version)"` 等 `$(...)` 命令替换迫使 /bin/sh 在硬编码
     /tmp 建临时文件（部分 shell 忽略 TMPDIR），只读 erofs 上直接失败。
  2. 可执行时直接 exec `bin/alive`，其 shebang `#!/usr/bin/env guile -s`
     依赖 minimal OHOS 上不存在的 /usr/bin/env，exec 报 127。
- 修改（仅 test_package/test.sh）：
  1. 删除全部可执行的 `$(...)`/反引号（含 `$(pwd)`→`$PWD`、
     `$(command -v ...)`→TMPDIR 文件 + 内建 `read`）；版本/help 输出改走
     `> "$TMPDIR/*.txt"` 重定向 + `grep -q` 判定 + `cat` 回显。
  2. `run_alive()` 有 guile 时一律 `guile --no-auto-compile -s <script>` 调用
    （与 shebang 等价；不再依赖 /usr/bin/env 与 exec 位）。
  3. 断言/标记不变：失败仍走 `fail()` 或 `passedCount:0/exit 1`，无跳过。
- 有效性待下一轮真机预检判定。

## 真机 Signal 9 修复轮（2026-09-15）

- 现象：HMBS 预检 compile 阶段报 Signal 9（SIGKILL），stdout/stderr 尾部为空，
  上游测试计数全 0（编译未完成故未到达测试）。
- 诊断：
  1. alive 本体只是 Guile 脚本替换（configure 生成 src/alive + fake makeinfo
     跳过 doc），自身几乎不占内存；空日志尾 + SIGKILL 指向两类诱因——源码下载
     阶段卡住被看门狗杀掉，或构建并行度在真机上造成内存峰值。
  2. 核对上游源码确认 `alive_cv_nice_ping=yes` 预设正确（savannah configure.ac
     用 `AC_CACHE_CHECK(... [alive_cv_nice_ping] ...)` 包裹 `$PING -n -c 1
     localhost` 探针，命令行传 `alive_cv_nice_ping=yes` 可跳过，与 Guix 做法一致），
     故 ping 联网探针不是挂起点。
  3. SNUGGLE/GUILE_PROGS 在 configure 期会执行 `$GUILE -c` 取版本号，环境变量
     GUILE/LD_LIBRARY_PATH/GUILE_AUTO_COMPILE=0 已在 generate() 正确注入，无需改动。
- 修改（均有仓库先例，未改测试口径）：
  1. `conandata.yml`：单 URL 改为 4 项有序镜像列表（tuna → ustc → aliyun →
     ftp.gnu.org 官方回退），与 `ci/conan/build_and_test.sh` 的 GNU 映射及
     libtool/2.5.4.1 等包惯例一致；sha256 保持不变。
  2. `conanfile.py`：`autotools.make(args=["-j1", "SHELL=/bin/sh"])` 显式限单作业
     压低内存峰值（与 akku 同模式），`autotools.install(args=["SHELL=/bin/sh"])`
     固定 POSIX shell。
- 有效性待下一轮真机预检判定；若仍 Signal 9 且日志仍为空，需 HMBS 提供完整
  conan create 日志定位是依赖链（guile 源码构建）还是本包步骤被杀。
