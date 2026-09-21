# zile 2.6.4 适配笔记

## 编译环境
- 构建系统: autotools（configure + make，辅助脚本在 build-aux/）
- 编译日期: 2026-09-17
- 编译器: clang 15（/data/service/hnp/bin/clang，profile ohos-aarch64）
- 状态: built
- worktree: ~/qzy/917-GLM-48-zile，分支 feat/zile-2.6.4，主理 9/17-GLM-48
- CONAN_HOME: ~/tmp/ch/home-917-GLM-48-zile

## 编译步骤

conan create archives/z/zile/2.6.4 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable

配方要点：AutotoolsToolchain 自动 --host=aarch64-unknown-linux-ohos；
PkgConfigDeps 生成 glib-2.0/gobject-2.0/gio-2.0/gee-0.8/ncursesw.pc 并注入
PKG_CONFIG_PATH；configure 显式 CURSES_LIB=-lncursesw（conan ncurses 只出
widec）、ac_cv_path_HELP2MAN=/bin/true；make/check/install 均传 VALAC=:；
make check 注入 TERM=xterm 与 TERMINFO=<ncurses>/share/terminfo。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 "unable to guess system type" | config.guess 2024-07-27 不识别 uname -s=HarmonyOS | 补丁 0001 加 HarmonyOS case（libgee/vala 配方同款）；config.sub 同版已原生支持 ohos 三元组（实测），免补丁 |
| 2 | configure 临时目录 "Permission denied"（E011/E114 同类） | HMDFS 上 umask 077 包裹的 mktemp/mkdir 不可用 | 补丁 0002 两处 umask 077→022 |
| 3 | make 报 valac: command not found（Error 127） | 上游 2.6 以 Vala 编写；tarball 自带预生成 .c 与 *_vala.stamp，但 stamp 规则无条件 touch *.vala 并重跑 valac；AM_PROG_VALAC 缺失仅 WARN，Makefile 保留默认 valac | make 传 VALAC=:（POSIX no-op 替位），直接编译 tarball 发布 .c；build() 与 package() 的 install 均需传入 |
| 4 | make install 触发 doc/zile.1.in 重建报 help2man: not found（127） | man 页规则依赖新编译的 src/zile 二进制，每次构建必触发重建 | configure 传 ac_cv_path_HELP2MAN=/bin/true（rc=0 不产出，保留 tarball 自带 zile.1.in） |
| 5 | estr-test 与 175 个 lisp 用例全部 SIGABRT（134），gtype.c:2556 static_quark_type_flags 断言 | glib 多实例：制品仓 glib/2.84.0 仅 static 变体，消费程序静态链 glib，而 libgee shared binary 内嵌另一份 static glib，两份 gobject 类型系统状态分裂 | default_options {"libgee/*:shared": False} 使 libgee 也静态构建，全图 glib 单实例（--build=missing 本地构建 libgee；glib/libffi/pcre2 仍走制品仓 binary） |
| 6 | 修复 5 后 lisp 用例全部 exit 1："Error opening terminal" | make check 无 TTY 且 OHOS 无系统 terminfo 数据库，ncurses 初始化失败 | conan ncurses 包自带 terminfo；make check 注入 TERM=xterm TERMINFO=<ncurses>/share/terminfo |
| 7 | 依赖解析 "Unable to find libgee/0.20.8.1 in remotes" | 0.20.8.1 为工程修复版（同源码，配方加 Skipped 依赖守卫），制品未上传 | 改用 libgee/0.20.8（制品仓已发布） |
| 8 | 消费者测试批处理 lisp 断言同样需要终端描述数据 | 同 6 | test_package 显式 requires ncurses/6.5，将 package_folder/share/terminfo 以 TERMINFO 注入测试脚本 |

## 源码修改

- patches/0001-config.guess-harmonyos.patch：build-aux/config.guess 的 case 表首部加 HarmonyOS 分支，输出 aarch64-unknown-linux-ohos。
- patches/0002-configure-umask022.patch：configure 两处 umask 077→022（临时目录创建）。

## 依赖版本

- glib/2.84.0（transitive_headers=True, transitive_libs=True，制品仓 binary）
- libgee/0.20.8（static 变体，--build=missing 本地构建；0.20.8.1 制品未发布故不用）
- ncurses/6.5（制品仓 binary，widec）

## 验证结果

```bash
conan-verify: G0 PASS / G1 PASS / G2 PASS / G3 PASS
make check: # TOTAL 176 / # PASS 176 / # FAIL 0 / # ERROR 0
  （src/estr-test 1 项 + tests/*.el lisp 用例 175 项，N_static=N_registered=176）
消费者测试 test_zile.sh：version（GNU Zile 2.6.4）/ usage / 批处理 lisp
编辑往返（--no-init-file/--load 插入文本保存后 cmp 逐字节比对）三断言 OK
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/zile | 约 1.2MB | zile 编辑器可执行（静态链 glib/libgee/ncurses） |
| share/doc/zile/dotzile.sample | 小 | 用户配置样例 |
| man/man1/zile.1 | 小 | 手册页（tarball 自带） |

## 注意事项

- 消费者测试需 ncurses/6.5 提供 terminfo（运行时环境依赖），test_package 已显式 requires。
- 若制品仓后续出现 glib shared 变体且 libgee 有锁定同版的 binary，可回归全 shared 依赖图；当前 static 组合是制品仓变体约束下的唯一单实例方案。
- VALAC=: 依赖"tarball 自带预生成 .c"，若换用 git 快照源码需引入 valac 工具链。
---

**编译结束**: 2026-09-17 03:56
**最终状态**: built
