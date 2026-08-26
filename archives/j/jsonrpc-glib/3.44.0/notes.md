# jsonrpc-glib 3.44.0 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-08-25
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. **依赖安装（conan）**：
   - json-glib/1.6.6: 通过 conan install 安装（传递依赖 glib/2.84.0, pcre2/10.40, libffi/3.4.4）

2. **主软件编译**：
   ```bash
   meson setup builddir --prefix=$HOME/usr/local \
     --native-file=conan_meson_native.ini \
     -Dwith_introspection=false \
     -Dwith_vapi=false \
     -Denable_tests=false \
     -Denable_gtk_doc=false
   ninja -C builddir
   ninja -C builddir install
   ```

3. **Conan 配方验证**：
   ```bash
   python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify jsonrpc-glib 3.44.0
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson找不到clang | conan_meson_native.ini未通过--native-file传入 | 使用--native-file=conan_meson_native.ini |
| 2 | meson找不到llvm-ar | native file缺少ar/ranlib路径 | _inject_meson_archive_tools()注入 |
| 3 | gnome.genmarshal失败 | glib-2.0.pc缺少glib_genmarshal变量 | _create_glib_pkg_config_aliases()注入变量 |
| 4 | gio-2.0.pc缺失 | glib 2.84.0 flat cpp_info无独立组件 | 创建gio-2.0.pc别名(复制glib-2.0.pc并改名) |
| 5 | CMakeDeps不传播glib头文件 | E216: Conan 2.29 CMakeDeps组件传播失效 | test_package改用PkgConfigDeps+Meson |
| 6 | test.c include路径错误 | headers在include/jsonrpc-glib-1.0/下 | #include <jsonrpc-glib.h> |
| 7 | CI L0d stub_test_method | test()方法缺少self.run() | 改用self.run()直接运行测试二进制 |

## 依赖链

1. libffi/3.4.4 (conan 预编译包)
2. pcre2/10.40 (conan 预编译包)
3. glib/2.84.0 (conan 预编译包, 含 gio/gobject/gmodule/gthread)
4. json-glib/1.6.6 (conan 预编译包)
5. jsonrpc-glib 3.44.0 (meson 编译)

## 源码修改

无补丁文件（meson配置禁用可选功能，无源码修改）

## 验证结果

- conan create: PASS (G1-G4 + L2/L4/L5 全通过)
- test_package: meson + PkgConfigDeps, self.run() 直接运行测试二进制
- 测试内容: jsonrpc_server_new() + jsonrpc_server_get_type() 验证

## 关键设计决策

### 1. PkgConfigDeps 替代 CMakeDeps (test_package)
- **问题**: glib 2.84.0 conan recipe 使用 flat cpp_info（无组件），CMakeDeps 不传播
  INTERFACE_INCLUDE_DIRECTORIES 到下游消费者（E216）
- **方案**: test_package 使用 PkgConfigDeps + Meson，通过 .pc 文件的 Requires 字段
  正确传递传递依赖的头文件路径

### 2. glib_genmarshal 变量注入
- **问题**: glib 2.84.0 conan recipe 生成的 glib-2.0.pc 不含 glib_genmarshal 变量
- **方案**: _create_glib_pkg_config_aliases() 方法从 prefix 解析 glib-genmarshal 路径
  并注入到 .pc 文件

### 3. gio-2.0.pc 别名创建
- **问题**: glib 2.84.0 conan recipe 不使用组件，PkgConfigDeps 只生成 glib-2.0.pc
- **方案**: 从 glib-2.0.pc 复制创建 gio-2.0.pc, gobject-2.0.pc 等别名文件

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（meson + PkgConfigDeps） |
| conandata.yml | 源码 URL + SHA256 |
| test_package/ | meson + PkgConfigDeps 测试 |
| manifest.yaml | 编译元数据 |
| notes.md | 适配笔记 |
---

**编译结束**: 2026-08-25 00:40
**最终状态**: built
