# cdemud 1.0.0 适配笔记（上游发布名 cdemu-daemon 1.0.0）

## 编译环境
- 构建系统: autotools（发布 tarball 自带 configure；2006-07 版 config.guess/sub）
- 编译日期: 2026-09-04
- 编译器: clang 15.0.4（/data/service/hnp/bin），三元组 aarch64-unknown-linux-ohos
- 依赖: glib/2.88.0、dbus/1.14.10、dbus-glib/0.114、libdaemon/0.14、libmirage/1.0.0（已先行独立适配并合
  入官方 main）、libsndfile/1.2.2 + pcre2/10.45 + zlib/1.3.1（静态闭包直链输入）
- 产物: `bin/cdemud`（OHOS ELF 自签名）+ `etc/dbus-1/system.d/cdemud-dbus.conf` +
  `share/man/man8/cdemud.8`
- 状态: built（编译/打包级移植）

## 编译步骤

conan create（ci/conan/build_and_test.sh 权威入口，显式 -pr:h/-pr:b=
ci/conan/profiles/ohos-aarch64）内自动完成：

1. `get()` 拉取 SourceForge 平铺目录归档并校验 sha256。
2. 应用补丁 0001-0004。
3. configure：`--disable-alsa`；GLIB_/GOBJECT_/GMODULE_/DBUS_/LIBDAEMON_/LIBMIRAGE_*
   cache 变量（E236 la-free 目录；每个 *_LIBS 自带 start-group/end-group 全闭包）。
4. make -j1（BUILT_SOURCES 经依赖 bindir 注入 PATH 的 glib-genmarshal、
   dbus-binding-tool 完成 marshallers/service-glue 代码生成）。
5. install → 删除包内 `.la` → 复制 COPYING → cdemud ELF 自签名（opus-tools 先例）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1-4 | 同 libmirage 1.0.0 notes（E007 config.guess/config.sub、umask 077→022） | 2007 autotools | 0001-0003 补丁同方案 |
| 5 | `g_type_init()` 自 glib 2.36 起废弃（GOBJECT_DEPRECATED_IN_2_36）但 2.88 仍声明且链接可用，直呼仅触发 deprecation warning | 2007 代码 + 现代 glib | 0004 补丁：`#if !GLIB_CHECK_VERSION(2,36,0)` 卫语句，仅为消除 deprecation warning 的预防性保留，非功能必需（实测 gtype.h:737 仍声明、libgobject-2.0.a 含符号、无卫语句链接 rc=0）；静态链接验证无其他 API 缺口 |
| 6 | configure 需要 `dbus-1.pc`（dbus 包只出 `dbus.pc`） | PKG_CHECK_MODULES(dbus, dbus-1 dbus-glib-1) | 预置 DBUS_CFLAGS/DBUS_LIBS 后 pkg-config 探测整体跳过，无需 dbus-1.pc 别名（dbus-glib 0.114 notes #4 的等价替代） |
| 7 | cdemud 链接期静态闭包跨组顺序敏感 | cdemud_LDADD 顺序固定（glib→gobject→dbus→libdaemon→libmirage） | 每个 *_LIBS 值自带 `-Wl,--start-group ... --end-group` 全闭包，链接与求值顺序无关（lld 支持） |
| 8 | make 阶段 glib-genmarshal / dbus-binding-tool 不在 PATH | Makefile 规则用裸命令名 | generate() 把 glib、dbus-glib 包 bin/ 追加进构建 env PATH（dbus-binding-tool 为 OHOS ELF，实测 rc=0） |
| 9 | ALSA 可选后端在鸿蒙不可用（/dev/snd 为空） | 设备无音频节点 | `--disable-alsa`，内建 null 音频后端 |
| 10 | make 期 dbus-binding-tool 报 `Error loading shared library libexpat.so` | dbus-binding-tool 为预编译 OHOS ELF，DT_NEEDED libexpat.so，但其自带 rpath 指向已迁移的构建树（E236 族） | generate() 把 expat 包 libdir 注入构建 env 的 LD_LIBRARY_PATH（expat 在 OHOS 仅 .so） |
| 11 | 官方服务器 CI 链接 cdemud 报 7 条 `g_libintl_*` undefined symbol（bindtextdomain/bind_textdomain_codeset/dgettext/textdomain/gettext/dcgettext/dngettext；本地 CI 因设备 `/usr/local/lib/libintl.a` 恰为同源拷贝而全绿，属环境巧合掩盖） | libdaemon 制品 `libdaemon.la` 缺陷：`dependency_libs=' -L<构建机>/usr/local/lib'`、`libdir='//lib'`；libtool 解析 `-ldaemon` 命中此类 .la 时注入 `-L/usr/local/lib` 且排在依赖归档目录之前，`-lintl` 被该机器自身不含 `g_libintl_*` 的 libintl.a 截胡；`libglib-2.0.a`（全链接图唯一引用面）仅引用 7 个唯一 `g_libintl_*`——llvm-nm 可复算：glib 包 libintl.a 提供 9 个 T 定义，被引用其中 7 个（另 2 个为未引用余量），与官方 CI 7 条 undefined 一致 | 双保险：归档目录写入净化版 `libdaemon.la`（`dependency_libs=''`、`libdir` 指向归档目录，libtool 搜索序首选命中）+ LDFLAGS 末尾显式追加 libdaemon 包 `libdaemon.a` 与 glib 包 `libintl.a` 绝对路径（generate() 运行时解析，不硬编码缓存路径） |

## 运行时边界（如实声明）

- daemon 初始化第一步 open `/dev/vhba_ctl`（src/cdemud-daemon.c:211）失败即退出：
  鸿蒙内核无 vhba 模块 → 光驱仿真功能不可用。
- 设备无 D-Bus 总线工具（dbus-daemon/dbus-run-session 均不存在，dbus-glib 0.114
  notes 实测矩阵）→ D-Bus 服务面不可用。
- 可验证面：编译、链接、打包、`cdemud --help`（GOption 选项解析先于守护初始化）。

## 依赖版本

glib/2.88.0、dbus/1.14.10、dbus-glib/0.114、libdaemon/0.14、libmirage/1.0.0（已在官方 main）、
libsndfile/1.2.2、pcre2/10.45、zlib/1.3.1

## 验证结果

```bash
# 权威入口（ci/conan/build_and_test.sh 同参数形态）单包验证：
conan create archives/c/cdemud/1.0.0 -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build="cdemud/*"               # exit=0
#   日志: run 内留档（设备 /storage/Users/currentUser/tmp/oh-device-porting-v2/cd-create-2.log
#   由 Builder 抄录至 reports/builder/）
# test_package: "cdemud test_package: --help smoke passed"
#   （test.sh 执行打包后的签名 ELF，断言 Usage/CDEmu 输出）
# llvm-readelf -d bin/cdemud → NEEDED 仅 libc.so（全静态闭包，运行期不依赖 conan 包 .so）
# llvm-readelf -SW bin/cdemud → .codesign 段存在（OHOS 自签名）
# 直接执行打包产物 cdemud --help → Usage 输出，rc=0
```

上游 1.0.0 无任何测试套件：tarball 无 test/ 目录；全部 Makefile.am（顶层/src/man）
无 TESTS 变量、无自定义 check 目标 → NO_UPSTREAM_TESTS（discovery 五项 EVIDENCE_COMPLETE，
证据见 run 内 reports/builder/upstream-test-discovery.md）；未登记 ci/config/no_official_test.txt、
未修改任何 ci 文件；权威 CI L1 以非白名单真实执行分支通过（test_package executed + L1e 破坏性负测）。

## 注意事项

- 禁止提交：`.orig`/`.work` 树与 patches-cdemud 临时目录留在 /storage/.../tmp/builds，
  不入仓；`archives/l/libXext/` 伪改动（鸿蒙 FS 大小写碰撞幽灵脏文件）不入任何提交。
- R40 分支门禁：平台任务分支为 feat/cdemud-1.0.0，仅覆盖 cdemud-1.0.0；
  libmirage/1.0.0 已先行独立适配并合入官方 main（E458 依赖先行交付顺序），
  不在本候选内，本库为其下游消费方（L0i 探测 8/8 依赖在制品仓在册）。
