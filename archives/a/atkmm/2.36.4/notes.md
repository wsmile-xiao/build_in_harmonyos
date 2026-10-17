# atkmm 2.36.4 适配笔记

## 基本信息

- **上游**：https://gitlab.gnome.org/GNOME/atkmm（tag 2.36.4）
- **类型**：ATK 无障碍工具包的官方 C++ 绑定（GNOME gtk 链 mm 系）
- **ABI**：atkmm-2.36（pkg-config 名 `atkmm-2.36`，产物 `libatkmm-2.36.so`）
- **构建系统**：meson（>= 0.60.0，install_tag 关键字要求）
- **许可**：LGPL-2.1-or-later

## 依赖（上游 meson.build 实测）

| 依赖 | 上游要求 | 仓内版本 | 满足 |
|---|---|---|---|
| atk | >= 2.33.3 | atk/2.38.0.1 | ✅ |
| glibmm-2.68 | >= 2.68.0 | glibmm/2.68.2（制品仓） | ✅ |
| sigc++-3.0 | （glibmm-2.68 传递） | 随 glibmm | ✅ |

注：pangomm 不是 atkmm 的依赖（两者是平行的 mm 绑定库）。

## 适配要点

1. **maintainer-mode=false**：官方 tarball 是 `meson dist` 产物，生成代码在
   `untracked/` 目录预生成（42 个文件：20 组 .hg/.ccg 对应 .cc/.h + wrap_init.cc），
   不需要 mm-common/gmmproc/m4。
2. **build-documentation=false**：doxygen/dot/xsltproc 在 OHOS worker 缺失。
3. **wrap_mode=nodownload**：禁止 meson 拉取 subprojects wrap（atk.wrap、glibmm-2.68.wrap），
   依赖全部由 Conan PkgConfigDeps 提供。
4. **gmmprocdir 变量注入**：上游 meson.build L145 `glibmm_dep.get_variable('gmmprocdir')`
   ——即使 maintainer-mode=false 也会执行该行（glibmm_dep 变量查询在 maintainer-mode
   分支之外），需要在生成的 glibmm-2.68.pc 追加 `gmmprocdir=${libdir}/glibmm-2.68/proc`
   （pangomm 同款技法）。
5. **meson >= 0.60 要求**：本 worker meson 版本需满足 install_tag 关键字。
6. **.so 签名**：原生 OHOS worker meson install 改写 rpath 后需 binary-sign-tool
   重签（与 glibmm/pangomm 同款 E135 处理）。

## 上游测试情况

atkmm 2.36.4 官方 tarball **无 tests/ 目录**，meson.build 无任何 test() 注册
（configure.ac 也只有 PKG_CHECK_MODULES，无测试声明）——与 pangomm 2.50.1 相同，
GNOME mm 系 tarball 不带 meson 测试。上游注册测试 N=0，如实申报。
消费者验证走 test_package/test.cpp（8 项断言：Atk::init/版本宏/Object/StateSet/Relation/name 访问器）。

## 结果

- conan create：通过（详见 reports/）
- test_package：编译链接运行全通过
