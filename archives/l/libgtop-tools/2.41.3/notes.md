# libgtop-tools 2.41.3 适配笔记

**生成日期**: 2026-09-19
**Wiki 上游**: https://gitlab.gnome.org/GNOME/libgtop
**源码**: https://download.gnome.org/sources/libgtop/2.41/libgtop-2.41.3.tar.xz
**SHA-256**: 775676df958e2ea2452f7568f28b2ea581063d312773dd5c0b7624c1b9b2da8c

---

## 适配定位（拆分包）

libgtop 2.41.3 库本体已适配入库（`archives/l/libgtop/2.41.3`，PR 已合并）。
本包按 **util-linux-login 拆分包模式** 从同一 libgtop 源码树只构建并交付
**命令行工具**：

| 二进制 | 源 | 说明 |
|---|---|---|
| libgtop_daemon2 | src/daemon/{gnuserv,slave,main,io,version}.c | 系统监控守护进程（gnuserv 协议） |
| libgtop_server2 | src/daemon/{server,slave,io,version}.c | suid server 辅助进程（stdin/stdout 协议） |

上游将两者安装到 `libexecdir`；conanfile.py 的 package() 把它们归集到
`bin/`，其余（库/头文件/pc/locale）全部剔除——库本体由 libgtop 包交付。

## 编译环境

- 构建系统: autotools (configure.ac + Makefile.am)
- 编译器: clang 15（OHOS，aarch64）
- conan: 2.29.1（OHOS 适配版），profile ci/conan/profiles/ohos-aarch64
- 依赖: glib/2.84.0.1（daemon 动态链接 glib；libgtop-2.0 库在树内静态链接进
  工具，不作为 conan 依赖声明——库本体由 libgtop 包交付）

## 编译步骤

1. `ohc-run.py init-build libgtop-tools 2.41.3 --url=<gnome 官方源>` 拉源码。
2. `lang-preflight`：detected=c（406/408 源文件为 C），与 cpp 兼容族，通过。
3. 配方手工编写（参照已验证的 libgtop 2.41.3 配方），generate() 与 libgtop
   完全同构：PkgConfigDeps + AutotoolsToolchain（--disable-nls、
   PKG_CONFIG_PATH、--build/--host aarch64-unknown-linux-gnu、MAKEINFO=true、
   LDFLAGS=-L<glib libdir> -lintl -Wl,-rpath,<glib libdir>）。
4. `ohc-run.py conan-verify`（G2 conan create 全流程验证）。
5. `ohc-run.py finish`（W2 结构 + R36 依赖 + W3 本地 CI 复验）。

## 关键适配点（继承 libgtop 库包的已验证结论）

1. **config.status tmpdir umask 077 → 022**（patches/0001）：setgid HMDFS 下
   umask 077 生成的临时目录不可写，config.status 报 Permission denied。
2. **mountlist 回退 /proc/self/mounts**（patches/0002）：OHOS 无 /etc/mtab，
   回退读 /proc/self/mounts；daemon 的 fsusage/mounts 命令依赖此表。
3. **g_libintl_ngettext 链接**：glib 包的 libintl.h 把 ngettext 映射为
   g_libintl_ngettext，需 -L<glib libdir> -lintl + 运行期 rpath。
4. **MAKEINFO=true**：CI 无 texinfo，跳过 info 手册生成。
5. **--disable-nls**：OHOS 无完整 gettext 生态。
6. **package() 裁剪**：只保留两个 daemon 二进制归集到 bin/，剔除
   lib/include/pc/share——这是 application 拆分包与库包的交付边界。

## 上游测试三步法（R51）

| 步骤 | 结果 |
|---|---|
| 清点 | `make check` 无注册测试（test_count=0）；examples/ 19 个 noinst_PROGRAMS 不随 install 安装 |
| 运行 | 上游无可运行测试套件；以 test_package 消费者测试替代 |
| 申报 | 上游 N=0，适配后补增 test_package（test.c 2 断言 + libgtop_daemon2 --help 实际执行；libgtop_server2 执行结果记录但不作失败判据，见下） |

## test_package 消费者测试

- test.c：验证 libgtop_daemon2 / libgtop_server2 存在且可执行（2 断言）。
- conanfile test()：实际执行 `libgtop_daemon2 --help`（GOption 解析在
  daemonize/setreuid 之前，exit 0；验证动态 glib + 静态 libgtop-2.0 链接正确、
  二进制真实可运行）。
- libgtop_server2 为上游设计的 **suid root 辅助进程**：main() 无条件调用
  setreuid()，OHOS 普通用户环境下被 seccomp 拦截（Signal 31/SIGSYS）——
  这是上游 suid 设计与 OHOS 沙箱的已知边界，非适配缺陷。测试中仍执行该
  二进制并记录结果（ignore_errors），不作为失败判据；libgtop_daemon2
  非根运行路径同样调用 setreuid，故其真实执行选择 --help 早期退出路径。

## 依赖版本

- glib/2.84.0.1（制品仓已发布，conan download 验证通过）
- libgtop/2.41.3（库本体，制品仓已发布；本包不 require 它——工具在树内
  静态链接库本体，避免未使用依赖）

## 验证结果

```bash
# conan create 全流程（G2）：编译 + 打包 + test_package 全部通过，见 reports/
# libgtop_server2 < /dev/null → setreuid 处 Signal 31/SIGSYS（suid 设计与 OHOS 沙箱边界，详见上文）
```
---

**编译结束**: 2026-09-19 08:30
**最终状态**: published
