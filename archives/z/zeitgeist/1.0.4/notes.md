# zeitgeist 1.0.4 适配笔记

## 软件信息
- **名称**: zeitgeist
- **版本**: 1.0.4
- **上游**: https://launchpad.net/zeitgeist
- **构建系统**: Autotools + Vala
- **许可证**: LGPL-2.1
- **说明**: 桌面活动事件日志框架，跟踪文件使用、浏览、聊天等

## 依赖情况
- glib/2.84.0.1 ✅
- sqlite/3.53.3 ✅
- json-glib/1.10.6 ✅
- vala/0.56.18 (构建工具 tool_requires) ✅

## 可选依赖（已禁用）
- dee-icu: 禁用 (--with-dee-icu=no)，不影响核心测试
- telepathy-glib: 禁用 (--disable-telepathy)
- valadoc: 禁用 (--disable-docs)
- gobject-introspection: 禁用 (--disable-introspection，ohpcd 未发布)
- datahub: 禁用 (--disable-datahub)

## 补丁
- `0001-relax-rdflib-check.patch`：configure 对 python3-rdflib 是硬性
  AC_MSG_FAILURE（ontologies 解析工具需要），但本体构建不需要——改为
  非致命警告。否则无 rdflib 的环境（CI）configure 直接失败。

## 适配关键点
### config.guess（E007）
显式 `--build=aarch64-unknown-linux-gnu` 绕过 OHOS 识别失败。

### HMDFS config.status（E011）
源码复制到 `/data/storage/el2/base/cache/zeitgeist-src` 再 configure/make
（config.status 在当前目录生成并执行 ./confXXXX/subs1.awk，HMDFS 执行位
被剥）。

### cross.cache
预置 `ac_cv_prog_cc_cross=yes`——CI 沙箱无法运行编译出的测试程序
（'C compiler cannot create executables'），跳过交叉编译检查。

### valac wrapper（仿 xmlbird）
- vala 包自带 valac 的默认 datadir（/usr/share/vala-0.56/vapi）在 OHOS
  不存在 → wrapper 注入 `--vapidir=<vala 包>/share/vala-0.56/vapi`
- valac 运行依赖 vala/glib 动态库 → wrapper 注入 LD_LIBRARY_PATH 把
  vala/lib、vala/lib/vala-0.56、glib/lib 前置
- 系统 valac（/usr/local/bin/valac，静态链接 glib）启动即崩
  'cannot register existing type gchar'——必须用 conan vala 包自带 valac

### pkg-config
- PkgConfigDeps 生成 sqlite.pc（configure 找 sqlite3.pc）→ 复制别名
- glib 的 glib-2.0.pc Requires.private libpcre2-8 → 需把 pcre2 包的
  pkgconfig 目录加入 PKG_CONFIG_PATH（传递依赖，未出现在 dependencies）

## 本地验证（2026-09-06，设备实测）
- configure 通过（以上配置）
- make -j1 通过（libzeitgeist + src 引擎 + examples + doc 全部编译）
- make check：**11 项测试，10 通过，1 失败**

### 测试失败项：log-test
- 根因：设备缺 D-Bus machine-id（/var/lib/dbus/machine-id 或
  /etc/machine-id 不存在），且 /system/etc 只读无法创建
- `Cannot spawn a message bus without a machine-id` — gio/dbus 需要
- 属环境限制，非代码缺陷；CI 环境如有 machine-id 则可通过

## 遗留说明
- python3-rdflib：本体构建不需要（仅 ontologies 解析工具），已补丁放行
