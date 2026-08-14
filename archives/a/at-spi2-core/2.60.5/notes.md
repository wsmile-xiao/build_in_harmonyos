# at-spi2-core 2.60.5 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-08-13
- 编译器: clang/clang++ 15（/data/service/hnp/bin，aarch64-linux-ohos）
- 状态: built（conan-verify G0-G4 全 PASS；未 upload）

## 编译步骤

```bash
# conan 配方构建（探索编译 + conan create）
python3 scripts/ohc-run.py conan-verify at-spi2-core 2.60.5
# 依赖：glib2/2.88.0（pcre2/10.45、zlib/1.3.1、libffi subproject）、
#       dbus/1.14.10（expat/2.8.2）、libxml2/2.15.3.1（私有，仅 meson configure）
```

探索编译已单独通过：meson 交叉编译 281 个 target 全过，install 到
TEST_PREFIX 成功；meson test 5/9 通过，4 个失败为 OHOS 无 dbus-daemon
会话总线所致（dbind/droute/memory/atk-test 依赖可用总线），属平台限制。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CI worker 导出 llvm-ar/as/strip/nm/ranlib 裸名，PATH 找不到 | env 污染 | generate() 弹出 AR/AS/STRIP/NM/RANLIB，用绝对路径 ar/as/strip/nm/ranlib 锁进 MesonToolchain |
| 2 | dgettext/libintl undeclared（编译报错） | OHOS sysroot 无 gettext，libintl.h stub 无声明 | glib2 的 proxy-libintl 提供代理头，补写 glib-2.0.pc 增加 `-I"${prefix}/include"`（Cflags）与 glib_genmarshal/glib_mkenums 等变量 |
| 3 | dbus 包不提供 dbus-1.pc；glib2 缺 gobject/gio/gmodule 单模块 .pc | 已发布包只带聚合 .pc | generate() 补写 dbus-1.pc（Requires: expat）与 gobject-2.0/gio-2.0/gmodule-2.0 薄包装 .pc |
| 4 | zlib/1.3.1 为非-PIC 静态库 | 链进共享库报 R_AARCH64 relocation | default_library=static（shared=False）整体静态交付（R26），atk/atspi 非系统同名库无冲突 |
| 5 | test_package 编译 'glib.h' file not found | 静态库包 Conan 2 traits 优化：transitive dep 的 require.headers=False，CMakeDeps 生成 glib2/dbus 的 INCLUDE_DIRS 为空 | requirements() 对 glib2/dbus 显式 `transitive_headers=True`，让 include 目录传播到下游 |
| 6 | test_package 冒烟 `at-spi-bus-launcher --version` abort | 该二进制不支持 --version（非法参数 g_error/SIGABRT），且 OHOS 无 gsettings-desktop-schemas（get_schema 即 abort）、无 dbus-daemon，无法真实运行 | test() 改用 readelf 产物级验证（可执行 aarch64 ELF）；at-spi2-registryd --help 仍真实运行 |
| 7 | at-spi2-registryd / at-spi-bus-launcher 不在 conanrun PATH | 静态库包 require.run=False，VirtualRunEnv 不把 cpp_info.bindirs 加入 PATH | package_info 用 runenv_info.prepend_path("PATH", .../bin)（模式同 a52dec） |
| 8 | 无 X11 / systemd / gobject-introspection / gtk-doc | OHOS 桌面组件缺失 | project_options: x11=disabled, use_systemd=false, introspection=disabled, docs=false, gtk2_atk_adaptor=false, dbus_glib=disabled |
| 9 | meson 把 OHOS 检测为 harmonyos 而非 linux | E090 已知模式 | 探索编译 281 target 全过、conan create 通过，无实际编译影响，未加补丁 |

## 源码修改

无补丁（patches/ 为空）。所有适配均在 conanfile.py 的 generate()/
package_info() 内完成。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| glib2 | 2.88.0 | 提供 gobject/gio/gmodule + proxy-libintl |
| dbus | 1.14.10 | dbus-1 客户端库 |
| libxml2 | 2.15.3.1 | 仅 meson configure 用（visible=False） |
| pcre2 | 10.45 | glib 传递依赖 |
| zlib | 1.3.1 | glib 传递依赖（非-PIC 静态） |

## 验证结果

```bash
python3 scripts/ohc-run.py conan-verify at-spi2-core 2.60.5
# G0 预构建评估 PASS / G1 配方完整性 PASS / G2 conan create PASS /
# G3 系统同名库隔离 PASS / G4 产物完整性 PASS
# conan create 真实通过：
#   at-spi2-core/2.60.5@ohpcd/stable: Created package revision ...
#   test: 'atk role API + atspi linkage verified (role=button)'
#   test: 'at-spi2-registryd --help' 正常输出 GOption 帮助
#   test: 'at-spi-bus-launcher ELF OK'（产物级验证）
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | 配方（meson；components: atk/atspi/bridge） |
| conandata.yml | 官方 GNOME 源 + sha256 |
| test_package/ | CMakeDeps 消费者测试（test_atk.c + MANIFEST.yml） |
| manifest.yaml | 归档元数据 |

## 注意事项

- **无 dbus-daemon**：ohpcd 未发布 dbus 守护进程包；at-spi 总线依赖
  session bus，OHOS 上 at-spi2-registryd 可 --help 启动，但完整总线服务
  需 dbus-daemon（平台限制，后续可补）。
- **无 X11/systemd/gi**：x11、systemd、gobject-introspection 均禁用。
- **at-spi-bus-launcher 不可运行**：OHOS 缺 gsettings-desktop-schemas
  （get_schema 即 abort）且无 dbus-daemon，只能做产物级验证。
- **静态交付**：zlib 非-PIC，default_library=static；atk/atspi 非系统同名
  库，静态交付无 R26 冲突。
- **静态库 headers 传播**：本配方组件 requires 需要下游拿到 glib/dbus
  头文件，必须保留 transitive_headers=True；若去掉，消费方 CMakeDeps 的
  INCLUDE_DIRS 会变空（'glib.h' not found）。
---

**编译结束**: 2026-08-13 19:02
**最终状态**: built
