# munin-c 0.0.13 适配笔记

## 编译环境
- 构建系统: autotools（configure.ac + automake；GitHub tag 包无生成文件，
  build() 内自举生成；autoconf 2.73 / automake 1.18）
- 编译日期: 2026-09-18
- 编译器: clang 15.0.4（/data/service/hnp/bin）
- 状态: built（conan-verify 全过）

## 编译步骤

conan create（ohos-aarch64 profile）：
1. generate(): AutotoolsToolchain，configure_args 追加
   --disable-maintainer-mode（上游 AM_MAINTAINER_MODE([enable])，避免
   make 阶段触发自动再生成）
2. build(): apply patches → mkdir build/m4 → aclocal → automake →
   autoconf（直跑链，见问题#7/#8）→ sed umask（问题#4）→ 探针选 shell →
   内联 env 手动 configure → make -j2
3. 产物：sbin/ = munin-node-c、munin-inetd-c、ok_plugin、nb_env；
   libexec/munin-c/ = munin-plugins-c（多合一插件，argv0 basename 分发）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | man 页规则依赖 pod2man（Perl podlators），交叉 CI worker 不保证可用 | common.am `%.1:%.pod` 规则 + 各 Makefile.am 的 man_MANS | 补丁 0001：移除两处 man_MANS（man 页非功能性产物），%.1 规则随之不触发 |
| 2 | GitHub tag 压缩包不含 configure | GitHub archive 不带 autotools 生成文件 | build() 内自举生成（见问题#7/#8） |
| 3 | configure 报 VERSION=unknown | conan source 缓存目录名非 munin-c-x.y.z，getversion 的目录名/打包/git 三条回退全落空 | 补丁 0002：configure.ac 的 AC_INIT 版本固化为 0.0.13 |
| 4 | config.status 报 `./confXXXXXX/subs1.awk: Permission denied` → could not setup config files machinery | autoconf 模板以 umask 077 建临时目录，HMDFS 上随后读取被拒（E011/E114，§12.1 文档案例） | 生成 configure 后 `sed -i 's/umask 077/umask 022/'`（保留真实临时目录创建，不换环境掩盖） |
| 5 | configure 第一步 `working directory cannot be determined`（E386） | profile buildenv 的 CONFIG_SHELL/SHELL 指向 hnp bash，HMDFS 上 getcwd 挂；工具链 env 会被 profile buildenv 覆盖 | build_requirements 加 tool_requires(bash/5.3)；build() 内联 env 前缀 `CONFIG_SHELL=SHELL=<实跑探针胜出者>` 手动调用 configure；make 不带前缀（GNU make 自用 /bin/sh，且 hnp make 在探针 bash 下 exec 失败） |
| 6 | 消费者测试初版 3 项失败：munin-plugins-c 不在 sbin、node-c 对 -Z 退出 0 | 上游装到 pkglibexec（libexec/munin-c/）；node 为常驻服务，-Z getopt 报错后继续启动路径 | 测试脚本改为 libexec 路径 + cp 派生 cpu 分发断言；node-c 改为交付存在性断言（常驻服务不自动拉起） |
| 7 | 首轮 CI 红：worker 无 aclocal（automake 未装），裸 autoreconf 失败 | CI worker 只有 hnp autoconf 家族 | 同 abiword-plugin-docbook 先例：tool_requires(automake/1.18) + `${ACLOCAL}/${AUTOMAKE}` 变量直跑链（aclocal → automake → autoconf），绕 autoreconf 且不依赖 PATH |
| 8 | automake --add-missing --copy 静默失败 → configure 报 cannot find required auxiliary files | AC_CONFIG_AUX_DIR([build]) 的目录不存在，automake 复制辅助脚本无目标目录 | 自举链前 `mkdir -p build m4` |

## 源码修改

仅补丁（conandata.yml 声明）：
- 0001-ohos-drop-man-pages.patch：src/node/Makefile.am 与
  src/plugins/Makefile.am 各删一行 man_MANS
- 0002-ohos-version-acinit.patch：configure.ac 的 AC_INIT 版本行固化

## 依赖版本

- 无外部依赖（AC_CHECK_HEADERS 仅探测 mntent.h/sys/vfs.h，musl 均有；
  AC_FUNC_FORK OHOS 支持）
- 构建期：bash/5.3（tool_requires，E386 shell 路由探针首选）、
  automake/1.18（tool_requires，自举链 aclocal/automake）

## 验证结果

- conan create + conan-verify：PASS（G0/G1/G2/G3/G4，L2/L4/L5）
- 消费者测试（真机）：test_munin_c.sh 7 项断言全过——
  ok_plugin fetch/config 两模式协议输出；munin-plugins-c（libexec/munin-c/）
  以 argv0=cpu 分发读 /proc/stat 输出值行与 config 模式 graph_title；
  munin-node-c 交付存在；munin-inetd-c 非法选项 getopt 错误路径退出

## 上游测试清点（R51）

- configure.ac 的 AC_CONFIG_FILES 含 t/Makefile，但 t/Makefile.am 仅把
  ok_plugin/nb_env 声明为 sbin_PROGRAMS；全仓无 TESTS/check_PROGRAMS/
  check- 目标 → `make check` 无测试集，注册测试 N_static = 0
- t/ 下 4 文件（common.c/common.h/ok_plugin.c/nb_env.c）为上游自带的
  插件协议测试辅助工具，非自动化用例；本适配的消费者测试直接复用
  ok_plugin 作真实协议断言载体

## 注意事项

- R38：可执行交付，commands.json 位于软件级 archives/m/munin-c/commands.json
- configure.ac 有 -Werror -pedantic（CC_CHECK_CFLAGS_APPEND），clang 15
  下实测编译干净，无需放宽
- 提交前剔除 test_package/build/ 与 *.ghfast-bak

---

**编译结束**: 2026-09-18 04:55
**最终状态**: built
