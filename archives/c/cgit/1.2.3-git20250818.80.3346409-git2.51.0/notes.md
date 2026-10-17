# cgit 1.2.3-git20250818.80.3346409-git2.51.0 适配笔记

## 编译环境

- 构建系统: makefile (cgit 定制 Makefile, 经由 git/Makefile 的 cgit.mk 联编)
- 编译日期: 2026-09-09
- 编译器: clang/clang++
- 状态: built (待真机预检回填实测数字)

## 版本与源码说明

- 任务版本 `1.2.3-git20250818.80.3346409-git2.51.0` 对应 Debian 快照
  `1.2.3+git20250818.80.3346409+git2.51.0-1`: cgit v1.2.3 之后 80 commits 至
  3346409 (2025-08-18) + 捆绑 git 2.51.0.
- 本配方使用稳定官方源:
  - cgit 3346409 (2025-08-18, "git: update to v2.51.0" 同步点):
    `https://github.com/zx2c4/cgit/archive/334640962c7fa96d407d1c71df709c94708bcef9.tar.gz`
    (sha256 `21bf7220...884ffa2`, 113620 字节, 由 git 对象生成, 稳定可校验)
  - git 2.51.0: `https://cdn.kernel.org/pub/software/scm/git/git-2.51.0.tar.xz`
    (sha256 `60a7c225...8990b62`, 与 FreeBSD ports/Buildroot 一致)
- 未直接使用 `https://git.zx2c4.com/cgit/snapshot/cgit-1.2.3.tar.xz` 的原因:
  该端点每次重新打包, Windows 实测 90640 字节, 与 FreeBSD/Gentoo 存档的 90632 字节
  (sha256 `5a5f12d2...414a6da4`) 不一致, 哈希会漂移, 不适合作为 conandata 唯一真相源.
- 80 个 post-1.2.3 commits 含对 git 2.51 头文件重构的同步 (3346409 将
  `object-store.h` 换成 `odb.h`, 对应上游 8f491517; v1.2.3 的 cgit.h 仍含
  `<cache.h>/<object-store.h>`, 与 git 2.51.0 不兼容, 真机报 `cache.h not found`
  与 `object-store.h not found`), 故必须用 3346409 基线, 不可用 v1.2.3 tag.

## 编译步骤

1. `source()` 分别下载 cgit 与 git 归档, git 解到 `git/` 子目录 (`strip_root=True`).
2. `generate()` 从 Conan conf 取 CC/AR/RANLIB, 拼 openssl/zlib 的 `-I/-L` 写入环境.
3. `build()` 执行 `make -j1 GIT_VER=2.51.0 NO_LUA=1 NO_REGEX=NeedsStartEnd NO_GETTEXT=1 HAVE_DEV_TTY=YesPlease NO_GETPASS=YesPlease NO_PTHREADS=1`, 再顺序执行 `tests/t*.sh` 共 14 个.
4. `package()` 安装 `bin/cgit`、`share/cgit/` (css/png/ico/txt + filters) 及
   `hmbs_upstream_result.json`.

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | snapshot 哈希漂移 | zx2c4 snapshot 端点再生 tarball | 改用 git 对象生成的 GitHub commit 归档, 稳定可校验 |
| 2 | cgit 需 git 源码树 | README 要求 `make get-git` 或 submodule | recipe 内下载 git 2.51.0 到 git/ 子目录 |
| 3 | Lua 依赖 | 默认自动探测 luajit/lua | `NO_LUA=1` 关闭, 零新增依赖 |
| 4 | t0010 需 tidy | OHOS 真机一般无 tidy | 缺失时计跳过并披露, 不计通过 |
| 5 | v1.2.3 配 git 2.51 报 `cache.h`/`object-store.h not found` | v1.2.3 的 cgit.h 沿用旧头, git 2.51 已重命名为 odb.h 系 | cgit 基线换成 3346409 (含上游 8f491517 同步) |
| 6 | `Git requires REG_STARTEND support` | OHOS libc 无 REG_STARTEND | 加 `NO_REGEX=NeedsStartEnd` (git-compat-util.h 指引值) |
| 7 | `gettext`/`ngettext` 隐式声明致 `-Wint-conversion` 错误 | OHOS 真机无 libintl, git 的 gettext.h 回退分支要求关 i18n | 加 `NO_GETTEXT=1`, 与 `NO_LUA=1` 同为 OHOS 首轮零新增依赖策略 |
| 8 | `compat/terminal.c` 报 `getpass` 未声明 + `-Wint-conversion` 升为错误 | OHOS libc 在 C99 严格模式下不暴露已废弃的 `getpass`, 且 uname 非 Linux 时 git 的 `config.mak.uname` 不会自动开 `HAVE_DEV_TTY`, 回退分支直调 `getpass` | 加 `HAVE_DEV_TTY=YesPlease` 切到 `/dev/tty` 实现(与 Linux 默认一致, 彻底避开 `getpass`), 叠加 `NO_GETPASS=YesPlease` 用 `compat/getpass.o` 兜底残留调用 |
| 9 | 链接 `ld.lld: undefined symbol: pthread_setcancelstate` (run-command.o) | OHOS musl 未导出 pthread cancellation 系列符号, `-pthread` 无法解决; git 上游 Makefile 预留 `NO_PTHREADS` 开关 | 加 `NO_PTHREADS=1` (命令行变量自动透传到 git 子 make), 异步路径回退到 fork, 不 stub、不跳测试 |
| 10 | 真机 13/13 上游套件报 `No such file or directory: 'bash'` | 真机仅保证 `/bin/sh` (HMBS shell 能力), 无 `bash`; 配方硬编码 `bash` | 解析顺序改为 hnp-bash → PATH bash → `$SHELL` → `/bin/sh` → `sh`; 上游脚本均为 `#!/bin/sh` POSIX, 用 sh 可跑; 同步补齐 git 脚手架 (系统 git 作 `GIT_TEST_INSTALLED` + 最小 `GIT-BUILD-OPTIONS` + `CHAIN_LINT=0` + test-tool 存在门 stub, 懒 prereq 未命中走 skip 不走 pass)。复检 10/13 通过, 剩余 3 个失败见 #11 |
| 11 | 复检 10/13 通过, t0001/t0108/t0111 失败 (相对路径 `../../Makefile`、`../../VERSION`、`../filters` 错位 + 缺 `GIT-VERSION-FILE`) | 上轮把 `TEST_OUTPUT_DIRECTORY` 覆写到 build 目录, 而套件依赖 trash 相对路径 (`../../`→cgit 根、`../filters`→tests/filters), 覆写后全部指错; 另 tarball 无 `GIT-VERSION-FILE` (git 构建产物), t0001 的打包检查无法比对 | 删除 `TEST_OUTPUT_DIRECTORY` 覆写 (沿用 setup.sh 默认 tests 目录); 缺失时按 cgit Makefile 的 `GIT_VER` (解析、非硬编码) 生成 `git/GIT-VERSION-FILE`; `source/VERSION` 沿用构建产物不伪造 |
| 12 | Signal9-empty-tails | libgit ~150 TU clang -g -O2 RSS spike OOM plus silent big-TU watchdog SIGKILL | CFLAGS -g0 -O0 -Wall via cmdline plus make V=1 plus 20s heartbeat in _stream_make/_stream_cmd, line-streamed log |
| 14 | preflight compile 阶报 /tmp 只读 (mktemp /tmp/sh*.tmp Read-only file system, E002) | OHOS /tmp 为 erofs 只读,配方上一版只透传已存在的 TMPDIR、无兜底创建,bare mktemp 仍默认走 /tmp;test_cgit.sh 亦硬编码 mktemp -d | generate/build/test_package 统一 ensure TMPDIR(优先 HMBS 注入,回退 HOME/tmp)并创建导出;_run_upstream_tests 前置 mktemp shim 仅重定向 /tmp 前缀到 TMPDIR;test_cgit.sh 改走 TMPDIR 模板,不删测试 |
| 13 | tidy vendor configure rc=1, t0010 failed 13/14 | tidy-html5 5.8.0 与 CMake 4 不兼容(需 BLFS cmake4_fixes 补丁: minimum 2.8.12...4.0 + add_custom_command 加 POST_BUILD)且 CMAKE_SYSTEM_NAME=HarmonyOS 无 Platform 文件 | 配方法内等价应用 BLFS 补丁并加 -DCMAKE_SYSTEM_NAME=Linux -DTRY_COMPILE_STATIC_LIBRARY; CMake 仍失败时用 OHOS CC 直接编译 src/*.c+console/*.c 得真 tidy(探针验 5.8.0), 缺失计失败不计跳过 |
| 15 | CI #44288 0/14 全败 `pwd: getcwd: cannot access parent directories` + `setup.sh: /../git/t/test-lib.sh: No such file` + 全员 `test_expect_success: command not found` rc=127 | 新鲜 shell 以 source/tests 为 cwd 时 `$(pwd)` 即失败返回空, TEST_DIRECTORY 坍缩为 `/../git/t`, harness 未加载; FUSE 下 getcwd 不可靠, 而非测试逻辑问题 | 在 `$TMPDIR/cgit-stage` 镜像源根布局 (cgit 二进制+Makefile/VERSION 拷贝, tests/filters 实拷贝使 trash 落 TMPDIR, git 以 symlink 共享脚手架), 以绝对 TEST_DIRECTORY/TEST_OUTPUT_DIRECTORY + 绝对脚本路径 + stage 首位 PATH 运行, 保留 trash 相对假设 (../..→stage, ../filters, ../../Makefile), 不跳过任何套件 |
| 16 | CI #45021 13/14，t0107 not ok 4 verify gzip format，head：shell-init getcwd cannot access parent，tail显 zip ok 30-35 | 上一版 head/tail 截断丢弃了真正失败行附近内容；更关键的是 CI 日志显示 stage 落在 /storage/Users/.../.cache/tmp/cgit-stage（FUSE）而非可靠挂载——工人启动时 TMPDIR=/data/storage/el2/base/cache，到 conan build 时已被覆盖为 FUSE 路径，所以上一版盲直用 TMPDIR 的 stage 仍触发 getcwd 不可靠 | stage 前增加 getcwd 可靠性探测：候选 [TMPDIR, /data/storage/el2/base/cache, HOME/tmp]，每个创建临时子目录并以新鲜 shell 为 cwd 跑 `pwd`，rc=0 且无 cannot-access-parent 才接受，首个通过者作为 stage 根；同时失败日志改为打印 first_nok 前后 12 行 ctx 窗口，t0107 失败时附加 pwd/which gunzip-gzip-tar-xz-unzip 版本与 trash 目录出诊，不跳过任何套件 |

## 上游测试

- 源码 `tests/` 共 14 个 shell 套件: t0001/t0010/t0020 + t0101-t0111.
- `build()` 内用 sh (bash 优先、缺失回退 `/bin/sh`, 与 HMBS shell 能力一致) 顺序执行, 动态计数 discovered/executed/passed/failed/skipped,
  输出 `HMBS_UPSTREAM_TEST_RESULT` (framework=shell).
- `t0010-validate-html.sh` 依赖 `tidy`, 缺失时计 skipped=1.
- 真机实测数字待 HMBS 预检回填, 不得猜测. 证伪要求: 检查 CGI 输出非空且含仓库
  标记; 必要时用 `exit 1` 桩确认 harness 能抓失败; 区分通过与静默跳过.

## 依赖版本

- openssl/3.5.6.1 (制品仓已发布, curl 8.15.0.1 同款)
- zlib/1.3.1.1 (制品仓已发布, curl 8.15.0.1 同款)

## 验证结果

- 本地 Windows 仅做配方静态检查与源码可达性验证, 未跑 conan (按守则只在真机跑).
- `cgit --version` + 新建 git 仓库 CGI 查询作为 test_package 3 断言
  (`test_cgit.sh`), 输出 `HMBS_TEST_PACKAGE_RESULT`.
- 真机 `conan create` 日志中的执行数/通过数以预检返回为准, 本轮不填写.

## 交付物

| 文件 | 说明 |
|------|------|
| bin/cgit | CGI 主程序 |
| share/cgit/cgit.css,png,ico,txt | Web 静态资源 |
| share/cgit/filters/ | exec 过滤器示例 |
| hmbs_upstream_result.json | 上游 14 套件聚合结果 (供 test_package 重发) |

## 注意事项

- `cgit` 运行时需要 `git` 二进制与 CGI 服务器, 包内不捆绑 git.
- 默认 `cgitrc` 路径为 `/etc/cgitrc`, 使用时通过 `CGIT_CONFIG` 环境变量覆盖.
- 适配路径为路径 A (基础适配).
