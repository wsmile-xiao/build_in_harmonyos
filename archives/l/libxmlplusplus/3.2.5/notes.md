# libxmlplusplus 3.2.5 适配笔记（libxml++ 3.0 API 线）

## 编译环境
- 构建系统: Meson（MesonToolchain + PkgConfigDeps + meson test）
- 编译日期: 2026-09-16
- 编译器: clang 15.0.4 (OHOS SDK, aarch64-linux-ohos)
- 平台: HarmonyOS PC aarch64, musl libc
- 状态: published（conan-verify G0-G4/L2/L4/L5 全 PASS）

## 角色
libxml++ 3.2.5 是 libxml2 的 C++ 封装（NEW 3.0 API 线，pc 名 libxml++-3.0），
独立三方库适配（知识库扩展路径）。

## 版本裁决
- 3.2.x 是 NEW-API 线（pc libxml++-3.0），与 2.x 旧线（libxml++-2.6）不兼容
- 仓库已有 libxmlpp/2.42.3（2.x 线，供 synfig）与 libxml++/5.4.0（5.x 线）归档；
  本任务 3.2.5 独立适配 3.x 线
- 官方最新 3.2.x = 3.2.5（GNOME download.gnome.org/sources/libxml++/3.2/）

## 依赖关系
- **glibmm/2.66.9**（glibmm-2.4 ABI 线）：3.2.5 的 meson.build 探测
  `dependency('glibmm-2.4', '>= 2.32.0')`，只能用 glibmm 2.66.x
  （glibmm 2.68+ 提供 glibmm-2.68.pc，需 sigc++-3.0，不匹配）
- **libxml2/2.15.3**（ohpcd 配方，pkg_config_name "libxml-2.0"）：meson
  `dependency('libxml-2.0', '>= 2.7.7')` 经 PkgConfigDeps 生成的 pc 解析

## 编译步骤
1. 下载 GNOME 官方 tarball 并核验 SHA-256（0c9b381b…）
2. conanfile.build(): MesonToolchain + PkgConfigDeps + meson setup/compile/test
3. 产物: libxml++-3.0.so(.1.0.0) + libxml++-3.0.pc

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载失败 | OHOS /tmp 不可写（E002），urllib 写入失败 | 设置 TMPDIR/TMP/TEMP=$HOME/tmp，预下载 tarball 注入 EXPECTED_SHA256 |
| 2 | meson 找不到 llvm-ar/ranlib | MesonToolchain 只映射 c/cpp 编译器，探测定裸名 | _inject_meson_archiver 从编译器目录推导写入 native file [binaries] |
| 3 | cpp_std 覆盖 | profile cppstd=17 覆盖项目默认 c++11 | tc.cpp_std = "c++11" 显式回退 |
| 4 | meson test exit 127 | libglib 的 g_libintl_* gettext 符号需依赖 libdir | LD_LIBRARY_PATH 注入全部依赖包 lib 目录 |
| 5 | 3.x API 差异 | 2.x get_child_text() 在 3.x 更名为 get_first_child_text() | 专项/消费者测试按 3.x API 编写 |

## 源码修改
无补丁（patches: {}）；未修改上游源码。

## 依赖版本
- glibmm/2.66.9（glibmm-2.4.pc / libglibmm-2.4.so）
- libxml2/2.15.3（libxml-2.0.pc）
- 传递：glib/2.84.0.1、libsigc/2.10.8、gio-2.0 等（conan 依赖链）

## 验证结果
- conan-verify: G0/G1/G2/G3/G4 + L2/L4/L5 全部 PASS（可标 published）
- 上游测试（meson test，build() 内执行）：4/4 OK（istream_ioparser +
  3 个 saxparser_*），日志 archives/…/reports/conan-create.log
- 探索构建 meson test 20/20（4 独立测试 + 16 examples 示例程序）
- test_package 消费者：libxml++ 3.0 consumer OK（parse_memory + parse_file）
- HarmonyOS 专项测试（UTF-8 中文解析/属性/序列化往返）：PASS，
  日志 reports/ohos-encoding-test-run.log（SHA-256 af2bfc7c…）

## 注意事项
- libxml++ 3.x 无 Document::parse_file 静态工厂（5.x 才有），消费者用
  DomParser::parse_file/parse_memory + get_document + get_root_node
- 非交叉构建时 meson test 必须注入依赖 libdir（否则 g_libintl_* 符号解析失败）
---

**编译结束**: 2026-09-16 01:17
**最终状态**: published
