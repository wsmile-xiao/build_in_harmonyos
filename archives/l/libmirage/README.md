# libmirage

CDEmu 套件的镜像解析后端库：把各类光盘镜像格式（CD/DVD：iso/cue/toc/mds/nrg/ccd/b6t/cdi）
解析为统一的 disc/session/track/sector 对象模型，供 cdemud（cdemu-daemon）消费。
解析器（parsers/）与片段后端（fragments/：binary、null、sndfile 音频）以运行时模块
形式从 `libdir/libmirage/` 加载。

- 上游: https://cdemu.sourceforge.io/ （SourceForge 项目 cdemu，files 平铺目录）
- 许可: GPL-2.0-or-later（源码头 `version 2 ... or (at your option) any later version`）
- 依赖: glib（glib-2.0/gobject-2.0/gmodule-2.0 >= 2.6）、sndfile >= 1.0.0

## 鸿蒙 PC 适配要点

1. **默认静态构建**：glib/2.88.0 OHOS 二进制只有静态库；shared 构建会把 glib 吞进
   libmirage.so 形成第二份 GType 运行时（dbus-glib 0.114 实测 PC=0 SIGSEGV 先例）。
   配方 `shared` 默认 False，且 OHOS 上 glib 缺 `.so` 时请求 shared 会显式报错。
2. **E236**：依赖 `.la` 元数据不可迁移；配方经构建私有 la-free 目录 + `GLIB_/GOBJECT_/
   GMODULE_/SNDFILE_` cache 变量喂 configure（PKG_CHECK_MODULES 检测到预置变量即跳过
   pkg-config），并在 package 阶段删除产物 `.la`。
3. **平台补丁**：2007 年代 autotools — config.guess OHOS 三元组（echo+exit 旧形式，
   libdaemon 0.14 先例）、config.sub linux-ohos 白名单、configure umask 077→022（HMDFS）。
4. **运行时模块现状**：OHOS 上 glib 仅静态制品，parsers/fragments 模块以静态档
   （`lib/libmirage/*.a`）形态打包；运行时 dlopen 加载在 OHOS 上不可用。本移植为
   **编译/打包级**：镜像解析的运行时功能需要可加载模块 + vhba 设备，在鸿蒙上不可达。
5. **交付顺序（E458/R36 依赖先行）**：cdemud 1.0.0 的 configure 硬依赖
   `libmirage >= 1.0.0`（.pc 检测）且本包此前无任何配方。按制品仓依赖先行规则与
   W2 单软件原子性（JC6），本包以独立 PR 先行交付；cdemud/1.0.0 作为消费方在本包
   合入发布后另行适配。

版本详情见 `1.0.0/notes.md`。
