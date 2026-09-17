# gnuit 4.9.5 适配笔记（GLM-28）

## 编译环境
- 构建系统: autotools（autoconf 2.61 生成，configure 随 tarball 预生成分发）
- 编译日期: 2026-09-15
- 编译器: clang/clang++（/data/service/hnp/bin/clang，OHOS aarch64）
- 状态: built
- conan: 2.29.1（os=OHOS），profile ci/conan/profiles/ohos-aarch64

## 任务信息
- 任务号：13469（依赖活动），分支 `feat/gnuit-4.9.5`
- worktree：`~/qzy/GLM-28-gnuit-4.9.5`（基线 upstream/main @ 6b5087b97a）
- 上游：https://ftp.gnu.org/gnu/gnuit/gnuit-4.9.5.tar.gz
  SHA256 `6b6e96db13bafa5ad35c735b2277699d4244088c709a3e134fb1a3e8c8a8557c`
- 语言：C（86 .c / 76 .h）；安装 6 个编译工具（gitfm/gitps/gitview/gitwipe/gitkeys/gitwhich）+ git* 脚本与 `git` 转发脚本，无库产物

## 编译步骤

1. W0：依赖核验——终端能力库为 configure 硬依赖（AC_MSG_ERROR [no library for handling terminal capabilities]），探测优先级 ncursesw→…→termcap；选 conan `ncurses/6.6`（ohpcd 制品仓 6.4/6.5/6.6 均已发布，`conan download --only-recipe` 实测）。readline 为 configure 遗留探测，源码零引用，显式 `--without-readline`。
2. 补丁准备（conandata.yml 全量申报，9 个，均 portability 类、无平台宏），驱动 W3 流程（init-build → patches → configure → make → make install DESTDIR → make check）与 conan create 双路径均验证通过。
3. configure 关键参数（W3 本地 CI 同源）：`--prefix=$HOME/usr/local --without-readline`，manifest configure_options 注入 `LDFLAGS=-L~/usr/local/lib`、`CPPFLAGS=-I~/usr/local/include`、`ACLOCAL=/bin/true AUTOHEADER=/bin/true AUTOMAKE=/bin/true`（E041 旁路）。
4. `conan create ... --user=ohpcd --channel=stable --build=missing`（G2 干净构建）→ test_package 实际运行 → G3/G4、L2/L4/L5 全 PASS。
5. `finish gnuit 4.9.5 built`（.ci-result.json exit_code=0）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 报 cannot guess build type | 2008 年版脚本：①HarmonyOS 分支缺失；②patch-autotools-ohos.pl 插入的是 2017+ 的 `GUESS=` 变量风格，老脚本分支需 `echo`+`exit` 才生效；③set_cc_for_config 里 `umask 077 && mktemp/mkdir` 在 HMDFS 下目录不可写 | 0001：echo/exit 风格分支 + 三处 umask 移除 |
| 2 | config.sub 报 machine aarch64-unknown not recognized | 2008 版 case 结构且无 aarch64 定义（2012 年才加入），perl 脚本只认 2018+ field 风格 | 0002：手工补 maybe_os 识别 `linux-ohos*`、CPU 别名与规范清单加 aarch64、OS 清单加 `-linux-ohos*`，双端实测三元组回显一致 |
| 3 | configure 报 no acceptable C compiler | autoconf 2.61 只搜 gcc/cc/cl.exe | 0004：`AC_PROG_CC` 前注入 `: ${CC=clang}` |
| 4 | configure 报 no library for handling terminal capabilities | 原始 configure 找不到 ncurses（conan 依赖不在系统路径） | manifest configure_options 注入 LDFLAGS/CPPFLAGS 指向 cmd-pkgs/conan 头文件库路径 |
| 5 | 链接 gitfm 报 duplicate symbol UP/BC/ospeed/PC | tty.c 自带 BSD termcap 全局定义，现代 ncurses 也提供 | 0007：改为 extern 声明 |
| 6 | 链接 gitfm/gitps/gitview 报 duplicate symbol refresh | 各工具自定义 refresh() 与 ncursesw 导出的 refresh 同名 | 0008/0009：加 static（作用域仅本文件） |
| 7 | make install 报 install: not found | 设备无 install 命令，configure 记录 ginstall 路径 | cmd-pkgs coreutils 提供 ginstall + PATH 优先 |
| 8 | 驱动装后探针 gitrgrep --version 超时崩溃 | gitrgrep 脚本对 --version 会遍历目录树并阻塞 stdin；gitkeys 无参数处理直接进终端捕获循环 | 0005/0006：两者支持 --version 非交互退出 |
| 9 | W3 预下载改写 conandata 为镜像列表后，还原残留旧补丁名 | 预下载备份机制与补丁目录规范化重命名交叠 | 以 git 为准恢复官方 URL，conandata 与 patches/ 文件名逐一同步 |

## 源码修改

见 conandata.yml 9 个补丁（详见 PR 补充说明）：0001 config.guess、0002 config.sub、0003 configure（umask+CC 默认）、0004 git.c、0005 gitkeys.c、0006 gitps.c、0007 gitrgrep、0008 gitview.c、0009 tty.c。

## 依赖版本

- ncurses/6.6（conan，ohpcd 制品仓已发布，裸 ref 无 @user/channel）
- 设备侧原始构建另用 cmd-pkgs ncurses 6.4 库（libncursesw.a）+ conan 6.6 包头文件（termcap API 跨小版本稳定，头库小版本差异已记录）

## 测试四维账本（诚实口径）

- `N_static = 0`：上游无任何自动化测试（无 tests/ 目录；src/Makefile.am 无 TESTS/check_PROGRAMS；grep TEST_CASE/add_test/ASSERT_ 零命中；make check 无目标）
- `N_registered = 0`；`N_executed = 0`（无上游测试可执行）
- `N_consumer = 1`（test_package/conanfile.py，3 处断言，conan create 内实际运行通过）：
  1. `gitwhich gitfm` → 退出码 0
  2. `gitwhich gitwhich` → 退出码 0
  3. `! gitwhich no-such-gnuit-tool-xyz` → 反向查找非 0 退出经 sh `!` 归零断言

## 验证结果

```bash
ohc-run.py conan-verify gnuit 4.9.5   # G0/G1/G2/G3/G4 + L2/L4/L5 全 PASS
ohc-run.py finish gnuit 4.9.5 built   # W3 本地 CI 模拟通过，.ci-result.json exit_code=0
```

## 路径 A/B 判断

- 路径 A 主体如上。
- 路径 B 候选知识（已查重 E007/E072/E122/E149）：「2017 年前的老式 config.guess/config.sub 的 OHOS 适配差异」——perl 脚本分支风格不匹配（GUESS= vs echo/exit）、2008 版 config.sub 缺 aarch64 需手工补 CPU 定义、config.guess 自身含 umask 077 需一并移除。E007/E072/E122 均只覆盖 2018+ field 风格，本例为可跨仓库复用的新增知识（候选池 fontutils 0.7 等一批上古包同型）。验证证据：本任务双路径构建通过。知识草稿与知识库扩展 Issue 见 PR 关联。

## 对话记录

- 2026-09-14 23:40 GLM-28 领坑（foliot 语言不匹配终止后顺延）；23:5x 导入平台任务 13469 并自领取；建 worktree/分支
- 2026-09-15 00:0x 归档骨架/配方/补丁/测试就绪；W3 因设备内存门槛（MemFree<1000MB）多次择窗
- 01:1x 门槛打开，发射构建；依次修复 config.guess 分支风格/umask、CC 默认、refresh 同名、install 缺失、gitrgrep 探针挂起
- 02:5x conan-verify 全 PASS；03:4x finish W3 通过、.ci-result.json 生成（exit_code=0）
---

**编译结束**: 2026-09-15 04:36
**最终状态**: built
