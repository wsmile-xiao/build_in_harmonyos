# pioneers 15.6 适配笔记（HarmonyOS PC / arm64）

## 编译环境
- 构建系统: autotools（automake 1.11 + libtool，发布包自带生成 configure）
- 编译日期: 2026-09-05
- 编译器: clang 15.0.4（/data/service/hnp/bin/clang，native OHOS arm64）
- profile: ohos-aarch64（os=OHOS arch=armv8 compiler=clang-15 libc++ Release）
- 状态: built（本地 conan create + conan-verify 全绿，未上传制品仓）

## 软件与产物
卡坦岛类棋盘游戏。构建产物为 6 个可执行文件（bin_PROGRAMS，均在顶层
Makefile 聚合）：
- `pioneers`（GTK3 图形客户端，含 client/gtk）
- `pioneersai`（无头 AI / 测试玩家，client/ai）
- `pioneers-editor`（GTK3 地图编辑器，editor/gtk）
- `pioneers-server-console`（无头游戏服务器，server）
- `pioneers-server-gtk`（GTK3 图形服务器，server/gtk）
- `pioneers-metaserver`（大厅目录服务，metaserver）

按 R38 声明 commands.json（软件级）；GUI 三件需要图形会话才能真正开窗，
无显示环境仅能测其 `--help` CLI 契约；无头三件可在 OHOS 直接运行。

## 编译步骤（探索 + 配方固化）
依赖：`gtk/3.24.43`、`glib/2.84.0.1`（均为 ohpcd 已发布 shared 预编译
二进制；GTK 全依赖闭包由这俩配方的 requires 自动拉取，见“依赖版本”）。

```bash
# 探索（模式 B）关键命令
sh configure --prefix=$DEFAULT_PREFIX \
  --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu \
  --without-avahi --without-notify --without-sound --disable-help --disable-nls
make -j4 pioneers pioneersai pioneers-editor \
        pioneers-server-console pioneers-server-gtk pioneers-metaserver
make install-binPROGRAMS DESTDIR=$TEST_PREFIX   # staging 验证
```

配方（conanfile.py build()）固化：
1. configure 前对发布包自带 configure 做文本中立化（同 libgsf/avahi 手法）
2. configure 参数：native 三元组 + `--without-avahi --without-notify
   --without-sound --disable-help --disable-nls`
3. `$LIBS` 注入 glib 的 proxy libintl 绝对路径（configure 期 @LIBS@ 替换）
4. 仅 make 六个 bin_PROGRAMS 目标（避开 po/ 翻译与 intltool-merge 数据目标）
5. package() 按 ELF 魔数收集 6 个二进制到 bin/（兼容 .libs wrapper）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `config.guess: unable to guess system type` | 发布包 config.guess(2018) 不识别 HarmonyOS uname | 显式 `--build=aarch64-unknown-linux-gnu --host=...`（native，非交叉） |
| 2 | `itstool not found` | 在线帮助(yelp-tools)需要 itstool | `--disable-help` |
| 3 | `Your intltool is too old / intltool scripts not found` | IT_PROG_INTLTOOL 无条件要求 intltool（perl 脚本 + XML::Parser，OHOS 无法运行） | `--disable-nls` + build() 内中立化 configure 中 6 处 intltool/gettext/perl/XML::Parser 硬错误 |
| 4 | `./confXXXXXX/subs1.awk: Permission denied` | HMFS 拒绝 autoconf AS_TMPDIR `(umask 077 && mktemp -d)` 生成的 2700+setgid 临时目录（E011/E112/E118） | build() 内 `um(ask\|ash) 077 && mktemp -d/mkdir` → 去掉 umask |
| 5 | `undefined symbol: g_libintl_gettext/ngettext`（GUI 链接失败） | glib 包安装 proxy-libintl 的 libintl.h，把 gettext() 宏映射为 g_libintl_*；`<glib/gi18n.h>` 客户代码经它调用，但 glib-2.0.pc 未携带该库 | configure 期 `$LIBS=<glib>/lib/libintl.so`（Makefile @LIBS@ 固化，avahi-ui-tools 先例） |
| 6 | 链接错误 `argument to '-V' is missing` 首次 conan create C compiler 失败 | 第一版配方把 LIBS 用 json.dumps 加引号，configure 把含引号整体当文件名 | LIBS 传裸绝对路径（无引号） |
| 7 | `make check` exit 2（po 目录） | po/Makefile.in.in check 目标用空 `$(MSGMERGE)` 拼 `-m` 命令；上游注册测试为 0 | 记录为平台/NLS 工具缺失，见 reports/test-report.md；配方只构建程序目标不跑 po |

源码修改：**无归档补丁**（patches/ 为空）。所有 OHOS 适配均以
conanfile.py build() 内对“发布包自带 configure”的确定性文本编辑实现，
每个编辑都有锚点断言（缺失即报错），随 conan create 可复现。

## 依赖版本

| 包 | 版本 | 说明 |
|----|------|------|
| gtk | 3.24.43 | 已发布 shared 二进制；其配方强制全链 shared=True |
| glib | 2.84.0.1 | gtk/3.24.43 二进制闭包 pin 此版本；pioneers 自身代码也用它 |
| cairo/cairo-gobject/pango/gdk-pixbuf/atk/fribidi/libepoxy/harfbuzz/... | 传递 | 由 gtk requires 自动拉取（制品仓预编译） |

> ⚠️ 版本决策说明：任务清单里提及 glib/2.88.3 已发布，但 ohpcd 上
> gtk/3.24.43（revision 3ef51bc…）的配方把 glib pin 在 2.84.0.1；若顶层再
> require glib/2.88.3，conan 图直接报
> “Version conflict between glib/2.84.0.1 and glib/2.88.3”，且 override 会
> 迫使 GTK 全链从源码重建（数小时、违背 R36 用预编译）。因此 pioneers
> 直接 require glib/2.84.0.1 与 gtk 闭包对齐，全链复用预编译二进制。

## 验证结果

```bash
conan create archives/p/pioneers/15.6 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
#   → EXIT 0；test_package HMBS_TEST_PACKAGE_RESULT {"discovered":8,"passed":8}
conan-verify pioneers 15.6   # G0-G4/L2/L4/L5 全 PASS（EXIT 0）
pioneers-server-console --version   # "Pioneers version: 15.6"
pioneers-metaserver --version       # "Pioneers version: 15.6, metaserver protocol: 1.3"
pioneersai --version                # "Pioneers version: 15.6"
pioneers --help                     # Usage…（exit 0）
```

### 测试用例（积分赛补全口径，上游 N=0 → 适配后 8 条实断言）

| 分类 | 条数 | 内容 |
|------|------|------|
| 契约冒烟（等价单元/CLI 契约） | 6 | 3 无头程序 `--version` 横幅含 15.6；3 GTK3 程序 GOption `--help` 于 gtk_init 前 exit 0 |
| 集成测试（鸿蒙特有补全） | 2 | server-console 加载上游 `small.game` 进入 "Preparing game" 真实初始化；metaserver 启动存活 |

集成测试由上游自带 `server/small.game`（31 行，随 test_package fixtures/ 携带）驱动，
执行的是游戏初始化的真实代码路径（Preparing game / 地图与规则加载），非仅版本横幅冒烟。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | application 配方（R32 in Linux/OHOS；R33 不裸用 ${CC}；R34 test 实跑二进制；R49 不注入共享前缀） |
| conandata.yml | 官方 SourceForge URL + sha256（R39） |
| test_package/ | test_pioneers.sh + conanfile.py + MANIFEST.yml（R51 上游 0 测试申报） |
| commands.json | 软件级 R38 工具声明（6 个二进制） |
| reports/conan-verify-report.md | 8 道门禁报告 |
| reports/test-report.md | 上游测试清点 + make check 实测 + 消费者 8/8（6 契约 + 2 集成） |

## 注意事项
- GUI 三件（pioneers/pioneers-editor/pioneers-server-gtk）在 CI/无显示环境
  只能验证 GOption `--help`（gtk_init 前退出）；真实开窗需 OHOS PC 图形会话。
- pioneers 运行时额外警告 `Error while loading settings`（GSettings schema
  未随工具包安装）不影响命令行契约与启动路径，完整桌面体验需另行部署
  share/ 数据与 schema。
- 本包只发布 6 个可执行文件（hicmd tool 交付），不携带 share/pioneers
  游戏数据（地图/主题/翻译）。服务端类工具不受影响；GUI 完整运行需数据。
- 探索目录 /storage/Users/currentUser/tmp/builds/pioneers-15.6.{orig,work}
  为本地分析副本，未入 git。
---

**编译结束**: 2026-09-05 12:50
**最终状态**: built
