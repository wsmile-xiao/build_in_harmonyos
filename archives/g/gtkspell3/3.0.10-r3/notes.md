# gtkspell3 3.0.10-r3 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-03
- 编译器: clang 15.0.4 (OHOS SDK llvm)
- 状态: built（本地 W3 验证通过，未实际上传制品仓；finish 的 published 仅为本地流程参数）

> ⚠️ R40 深度适配完整性标注：本库为 GTK3 图形栈组件（拼写检查 addon），
> 需人工确认适配完整性。本次验证覆盖 GObject 类型注册/对象构造/error domain/
> enchant 语言列表等无渲染 API；渲染路径（GtkTextView 高亮/右键菜单）在
> headless 环境无法完整验证，补丁均为实质 shell 级适配（无空 stub）。

## 编译步骤

1. `init-build`（源码来自 Debian 官方镜像池，waterlan 官网已下线）
2. 语言预检：detected=c（c↔cpp 兼容族，通过）
3. 探索编译：
   ```
   ./configure --prefix=$DEFAULT_PREFIX --disable-nls
   make -j1
   make install DESTDIR=$TEST_PREFIX
   make check   # 上游无测试目标
   ```
4. conan-init 生成配方 → 完善 conanfile.py/conandata.yml/test_package
5. conan-verify 8 道门禁全通过（G2 conan create PASS）
6. finish 收尾（W3 本地 CI 通过）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 无法识别 HarmonyOS | config.guess 2018 版无 OHOS 分支 | 补丁 0001/0002：config.guess 加 HarmonyOS 识别、config.sub 加 ohos-linux 三元组（E007） |
| 2 | intltool 检查失败（XML::Parser） | XML::Parser 是 XS 模块，HMDFS dlopen 无法加载 | 补丁 0003：configure 跳过 XML::Parser 检查（同 intltool 0.51.0 归档） |
| 3 | config.status: subs1.awk Permission denied | HMDFS 上 mktemp 077 权限不兼容 | 补丁 0003：ac_pwd 回退 $PWD、umask 077→022、ac_tmp 固定可写目录（同 goffice 归档） |
| 4 | lld 链接失败 `-l:ld-musl-aarch64.so.1` | glib pc 文件含 `-l:filename` 语法，ld.lld 无法解析 | 探索期本地替换为绝对路径（goffice 同款处理）；conan 环境由 PkgConfigDeps 生成干净 pc |
| 5 | 链接 `undefined symbol: g_libintl_dgettext` | gtkspell 源码无条件调用 dgettext，glib 头文件映射为 g_libintl_dgettext | shared 构建（与 gtk/enchant 栈一致），generate() 给 glib-2.0.pc 追加 -lintl（同 gtk/3.24.43 配方） |
| 6 | test_package 编译 hb.h 找不到 | gtk/enchant 无组件扁平配方，CMakeDeps 无法传递 harfbuzz 头文件 | test_package 改 PkgConfig 风格（PkgConfigDeps + pkg_check_modules，同 gtkdatabox 先例） |
| 7 | conan-verify 报 `cpp_info.requires` 组件不存在 | gtk/enchant 均为无组件扁平包，不能用组件引用 | 移除 cpp_info.requires，依赖传递由 requirements() transitive 标志处理 |

## 源码修改

| 补丁 | 文件 | 修改内容 |
|------|------|----------|
| 0001-build-config.guess.patch | build/config.guess | 增加 HarmonyOS 系统识别分支，输出 aarch64-unknown-linux-ohos |
| 0002-build-config.sub.patch | build/config.sub | maybe_os/ohos-linux 分支/OS 列表三处增加 ohos 三元组 |
| 0003-configure.patch | configure | 跳过 intltool XML::Parser 检查；ac_pwd 回退；umask 077→022；ac_tmp 固定目录 |

## 依赖版本

- gtk/3.24.43（shared）
- enchant/2.8.2
- glib/2.84.0.1（gtk 传递依赖）
- pcre2/ffi/expat 等（glib 传递依赖）

## 验证结果

```bash
# conan-verify 8 道门禁全通过
python3 scripts/ohc-run.py conan-verify gtkspell3 3.0.10-r3
# → G1 配方完整性 PASS / G2 conan create PASS / G3 系统同名库隔离 PASS / G4 产物完整性 PASS

# W3 本地 CI
python3 scripts/ohc-run.py finish gtkspell3 3.0.10-r3 published
# → setup.sh 通过 + build_and_test.sh 通过
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（autotools + PkgConfigDeps，shared 构建） |
| conandata.yml | 源码声明 + 3 个补丁 |
| patches/ | 3 个 OHOS 适配补丁 |
| test_package/ | PkgConfig 风格真实 API 冒烟测试（4 断言） |

## 注意事项

- 上游官网 waterlan.home.xs4all.nl 已下线，源码采用 Debian 官方镜像池（权威镜像源）
- 上游无任何正式测试（make check 空目标），按测试红线补充自研断言测试
- NLS 禁用（--disable-nls）规避 intltool 运行时依赖
- 该库为 GPL-2.0 许可

---

**编译结束**: 2026-09-03
**最终状态**: built
