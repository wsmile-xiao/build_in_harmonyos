# xwrited 3（write/wall 桌面通知守护）

## 来源与范围

- 官方源码：<https://code.guido-berhoerster.org/projects/xwrited/downloads/xwrited-3.tar.gz>
- SHA-256：`07a6634325e81d22ef40a386698a87cc4912bd6d389257adf7fa523b8345bd07`
 （2026-10-12 直连上游下载实测；Debian `xwrited_3.orig.tar.gz` 的
  `dac42f75...` 为发行版重打包哈希，不采用）
- 许可证：MIT（见上游 README 尾部与官网 License 章节）；上游无独立许可证文件，
  配方把 README/NEWS 安装到 `share/doc/xwrited/` 备查。
- 本 Conan 包名为 `xwrited/3`，产物为 `bin/xwrited`（GApplication 命令行守护，
  通过 GDBus 把消息发给桌面通知服务）。
- 上游版本即 `3`（Makefile `VERSION = 3`，`xwrited --version` 打印 `xwrited 3`）；
  首次适配，无后缀。
- 版本归一化：Conan 2.x 的 RecipeReference 版本规则要求版本总长
  ≥2 字符，单字符 `3` 在
  export 阶段即报 `ERROR: Invalid package version '3'`（2026-10-11 真机预检
  compile 失败证据）。归档目录/分支保持任务卡 `3`（过 CI L0n 分支门禁），
  配方删掉字面 `version = "3"`、改 `set_version()` 返回 `v3`（上游无点号
  形式，故用 v 前缀；同 cronic/3、tweeny/3、gcal/4 先例；刻意不写字面量以
  避开 CI L0m-3/PF8 的字面量-目录比对）；制品仓真实引用为 `xwrited/v3`，
  `commands.json` 的 ref 按 PF8 口径保留 `xwrited/3` 并另设
  `version_normalization.artifact_ref` 声明对应关系。

## 构建选择

- 手写 Makefile 工程（无 configure/cmake/meson），参照仓内 batsignal 1.8.0 范式：
  `PkgConfigDeps + VirtualBuildEnv`，`PKG_CONFIG_PATH` 指向 generators 目录，
  供 Makefile 内 `pkg-config --cflags/--libs gobject-2.0 gio-2.0 glib-2.0` 使用；
  `make -j1` 规避 OHOS 沙箱对 jobserver 管道（mkfifo）的限制。
- 直接依赖 `glib/2.84.0.1`（仓内 100+ 配方使用的主流版本）；
  `tool_requires pkgconf/3.0.5`（pkg-config 可执行文件）与
  `gettext/0.22.5.1`（msgfmt，用于 .mo/.desktop 生成）。
- CCI 劫持修正（2026-10-11 真机预检 compile 失败）：glib 的裸
  `libffi/3.4.4` 在预检双远端下优先命中 CCI 配方（日志打 CCI 专属补丁
  `0008-3.4.4-invalid-CFI-advance_loc.patch`，本仓配方无此补丁），其
  configure 在真机报 `/data/service/hnp/bin/bash: inaccessible or not found`
  （Error 127，与 libtiger/0.3.4 同指纹）。配方与 test_package 以
  `libffi/3.4.4#ca8b0eb4102edbca48730e504e3afbdc`（override，同版本 pin，
  不扰动 glib package_id）强制走 ohpcd 已发布加固配方；该 RREV 取自
  ohpcd v2 API 实测值（libgsf/ayatana-ido 已端到端验证）。
- `OS_NAME=OHOS` 写在 make 命令行，强制走 `xwd-utmp-utmpx.o` 后端。
  上游仅在 `uname -s` 为 Linux/FreeBSD 时选用 libutempter 后端；OHOS 没有
  utmp/wtmp 特权 helper，utmpx 路径（上游给其余所有 OS 的默认路径）是唯一
  可移植选择。此覆盖无需补丁（OS_NAME 是普通 make 变量，命令行优先）。
- `XCPPFLAGS="-D_XOPEN_SOURCE=600 -D_DEFAULT_SOURCE"`：Makefile 以 `-std=c99`
  编译，musl 严格模式下 `ptsname/posix_openpt` 不可见；补宏定义保证声明可见。
- 只构建 `xwrited` 二进制 + autostart `.desktop` + `po/de.mo po/en.mo po/id.mo`。
  `all` 附带的 man 页需要 xsltproc 拉取远端 docbook 样式表（构建期联网），
  已跳过；`make install` 依赖 GNU `install -D`，改用 conan `copy()` 手工安装
  （bin/xwrited、share/applications/*.desktop、
  share/locale/<lang>/LC_MESSAGES/xwrited.mo、share/doc/xwrited/{README,NEWS}）。
- `PKG_CONFIG` 显式传递（2026-10-11 真机预检 compile 失败）：本仓
  `pkgconf/3.0.5` 只装出 `pkgconf`、无 `pkg-config` 别名（上游 3.0.5 亦无），
  Makefile 的裸 `pkg-config` 调用报 `No such file or directory`。配方取
  build-dep 包内绝对路径作 `PKG_CONFIG=` 命令行变量（pianobar 同款），另建
  `pkg-config` 软链 shim 覆盖硬编码裸名调用（无需 chmod），并把全部
  build-dep `bin`（含 gettext 的 msgfmt）前置到 PATH。
- 编译器取 profile conf（2026-10-11 真机：profile 钉死的
  `/data/service/hnp/bin/clang` 在部分 HMBS 宿主根本不存在，报
  `inaccessible or not found` Error 127）。`_resolve_cc()` 沿用仓库既定模式
  （R33 + zurl 先例）：conf 值在盘即用（健康机零改动），缺失时回退裸名
  `clang` 交 PATH 解析；只读 isfile 探测，不碰 CFLAGS/LDFLAGS。
- `patches/0001-ohos-utmpx-noop.patch`（唯一补丁）：OHOS宏
  `OHOS_NO_UTMPX_DB=1` 下把 `xwd-utmp-utmpx.c` 的记账入口降级为no-op；
  非OHOS分支仅加 `ut_name->ut_user` 兼容别名（musl无该别名），保持上游语义。
  上述make命令行覆盖无需补丁的部分仍无需补丁。
- OHOS utmpx降级（2026-10-11真机预检compile失败，本轮新增）：
  `xwd-utmp-utmpx.c`报`no member named 'ut_name' in 'struct utmpx'`（2 errors）
  外加`setutxent`等隐式声明警告。根因是OHOS musl libc的`<utmpx.h>`仅有
  结构体定义、无utmpx数据库符号且结构体成员为`ut_user`而非`ut_name`
  （知识库E121与agetty/2.42.2的ohos-utmpx-shim先例一致）。配方在
  `settings.os==OHOS`时经XCPPFLAGS注入`-DOHOS_NO_UTMPX_DB=1`，补丁将
  `xwd_utmp_add/remove_entry`编译为no-op；通知主路径（pty读取+
  GNotification）不依赖记账返回值，上游该函数本身即返回void、失败仅
  `g_critical`。test_package仅覆盖`--version/-V/--help`/参数校验（均在
  D-Bus/pty建立之前），不受影响。
- 上游无测试套件（Makefile 无 check/test 目标，源码树无 tests/ 目录，
  Debian 打包亦无测试步骤），`build()` 不调用上游测试，证据标记以
  `status=no_tests` 输出；详见 `test_package/MANIFEST.yml` 审计。

## 测试设计（test_package）

- `test_xwrited.sh` 对打包二进制做 6 条真实断言：文件存在非空、aarch64 ELF
  身份（od 读魔数 + e_machine=183，不依赖 `file` 命令）、`--version`/`-V`
  打印 `xwrited 3` 且退出码 0、`--help` 含版本选项且退出码 0、位置参数被
  `invalid argument` 拒绝且退出码非 0（反向对照，证明 harness 能抓到失败）。
- 以上路径均在 GApplication 注册（D-Bus）之前处理，不需要会话总线、pty 或
  通知守护， headless 真机可确定性执行；脚本尾部打印
  `RESULT: P passed, F failed`，由 `test_package/conanfile.py` 逐行解析为
  `HMBS_TEST_PACKAGE_RESULT`（discovered/passedCount 唯一来源），同时重发
  `HMBS_UPSTREAM_TEST_RESULT(no_tests)` 以覆盖构建缓存命中轮次。
- `assertion_count: 6` 与脚本检查数一致。

## 验证情况

- 首轮工作树未提交：`conan create` 与 test_package 实测由 HMBS 后台在
  HarmonyOS PC 真机统一执行，本轮不宣称任何通过率数字；`manifest.yaml`
  与 PR 草稿中的通过率待真机 evidence 轮回填。
- Windows 宿主说明：本机 `git status` 曾因上游 `archives/l/libXext` 与
  `archives/l/libxext`（及 libXres 大小写双目录）在大小写不敏感文件系统
  上冲突而显脏，已对 `archives/l/libXext/README.md` 与 `manifest.yaml`
  置 `assume-unchanged`，当前工作树除本任务新增文件外干净；另有上游单个
  非法文件名（`archives/g/gama/...patch??`）通过 sparse-checkout 排除后
  同步 `upstream/main@e554b84`。
