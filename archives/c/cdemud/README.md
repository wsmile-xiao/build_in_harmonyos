# cdemud

CDEmu 套件的 userspace 守护进程（上游发布名 cdemu-daemon，1.1.0 起更名；本包采用
产品名/conanfile name=cdemud）：经 D-Bus（net.sf.cdemu.CDEMUD_Daemon）暴露光驱仿真
接口，把 libmirage 解析出的镜像写入 vhba 内核模块模拟的虚拟光驱。可选 ALSA 音频后端，
内建 null 音频后端。

- 上游: https://cdemu.sourceforge.io/ （SourceForge 项目 cdemu，files 平铺目录）
- 许可: GPL-2.0-or-later（源码头 `version 2 ... or (at your option) any later version`）
- 依赖: glib（>= 2.6）、dbus-1（>= 0.60）、dbus-glib-1（>= 0.61）、libdaemon（>= 0.10）、
  libmirage（>= 1.0.0，已先行独立适配并合入官方 main）；可选 alsa（本次 --disable-alsa 关闭）

## 鸿蒙 PC 适配要点

1. **编译/打包级移植**：cdemud 运行时第一步即 open `/dev/vhba_ctl`（src/cdemud-daemon.c），
   鸿蒙内核无 vhba 模块（/dev 无 vhba_ctl），且设备无 D-Bus 会话/系统总线工具
   （dbus-daemon/dbus-run-session 不存在，dbus-glib 0.114 notes 实测矩阵）→ 守护进程
   在 OHOS 上无法完成初始化。本包交付**可编译、可链接、可打包、可执行 --help** 的
   cdemud；完整功能需 D-Bus + vhba，如实标注为运行时不可用。
2. **--disable-alsa**：alsa-lib 虽在仓，但设备 /dev/snd 为空（无音频节点），关闭 ALSA
   后使用内建 null 音频后端。
3. **E236 + cache 变量**：configure 的全部 PKG_CHECK_MODULES 组（glib/gobject/gmodule/
   dbus/libdaemon/libmirage）经构建私有 la-free 目录 + 预置 `<GROUP>_CFLAGS/_LIBS` 喂入
   （dbus-glib 0.114 先例）；dbus 只出 `dbus.pc` 而 configure 要 `dbus-1`，预置 DBUS_*
   变量后无需再造 dbus-1.pc 别名。制品 libdaemon.la 冻结了构建机路径
   （`dependency_libs=-L<构建机>/usr/local/lib`），libtool 误读会注入
   `-L/usr/local/lib` 截胡 `-lintl`（官方 CI `g_libintl_*` undefined 根因）：
   归档目录写入净化版 libdaemon.la，并把 libdaemon.a 与 glib 自带 libintl.a
   以绝对路径显式追加进 LDFLAGS，链接面不依赖任何机器的 /usr/local 残留。
4. **构建期代码生成**：BUILT_SOURCES 需要 `glib-genmarshal`（glib 包 bin/）与
   `dbus-binding-tool`（dbus-glib 包 bin/），经依赖 bindir 注入 PATH。
5. **平台补丁**：2007 年代 autotools（config.guess echo+exit 形式、config.sub
   linux-ohos 白名单、configure umask 077→022）+ src/main.c `g_type_init()` 卫语句
   （g_type_init 自 glib 2.36 起废弃但 2.88 仍声明且链接可用，卫语句仅为消除
   deprecation warning 的预防性保留；OHOS glib 为 2.88.0）。
6. **依赖先行（E458 依赖先行交付顺序）**：cdemud configure 硬依赖
   `libmirage >= 1.0.0`（.pc）；libmirage/1.0.0 已先行独立适配并合入官方 main，
   本候选仅含 cdemud（下游消费方），L0i 探测 8/8 依赖在制品仓在册。

版本详情见 `1.0.0/notes.md`。
