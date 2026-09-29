# DRAFT-10037: X11 dockapp 上 OHOS 三连（x11.pc prefix=/ 不可重定位 + C++11 UDL + --host triplet）

- 条目主题：X11 客户端/dockapp 适配 OHOS 时 configure 与编译阶段的三个独立陷阱与修法。
- 状态：草稿（待知识库主编审核，拟提升编号 Exxx）
- 关联软件：wmcdplay 1.1。

## ① x11.pc prefix=/ 不可重定位
- 特征：`-I//include`，仍报 `'X11/Xlib.h' file not found`。
- 根因：`libx11/6.4.0` 安装的 `x11.pc` 写死 `prefix=/`，pkg-config 展开无效。
- 修法：真实 include/lib 路径来自 `AutotoolsDeps` 注入的 `cpp_info`；`PkgConfigDeps`
  仅保留给上游 `PKG_CHECK_MODULES` 探测（`checking for x11... yes`）。

## ② C++11 用户自定义字面量
- 特征：`invalid suffix on literal; C++11 requires a space between literal and identifier`。
- 根因：`"...Release "VERSION"\n"`（字面量与宏之间无空格）被词法成 UDL。
- 修法：`"Release " VERSION "\n"`。

## ③ 交叉编译模式未启用
- 特征：configure 在构建机上尝试运行 aarch64 conftest。
- 修法：`AutotoolsToolchain.configure_args.append("--host=aarch64-linux-ohos")`，
  使 configure 进入交叉模式（works-check 只链接不运行）。

## 关联
E467（AutotoolsDeps 导出 LIBS 与 configure 探测）、E284（交叉构建配置头）、E543（老 autotools 交叉三类适配点）。
