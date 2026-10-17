# template-glib 3.36.2 适配笔记（GLM-29，2026-09-15）

## 基本信息
- 任务：13462，worktree `~/qzy/GLM-29-template-glib-3.36.2`，分支 `feat/template-glib-3.36.2`
- 上游：https://gitlab.gnome.org/GNOME/template-glib tag 3.36.2（C，meson，LGPL-2.1+）
- 源码包：https://download.gnome.org/sources/template-glib/3.36/template-glib-3.36.2.tar.xz
  sha256=0020f3a401888ce763b3a17508c2f58e91972a483a0c547afdb7ccbe25619948（与官方 sha256sum 文件交叉一致；本机/设备到 download.gnome.org 均不可达，经南大镜像 mirror.nju.edu.cn 取字节核对哈希，CI worker 直连官方 URL——adwaita-fonts 先例）

## 依赖（W0 均已发布到 ohpcd）
| 依赖 | 版本 | 说明 |
|---|---|---|
| glib2 | 2.88.0 | GI/1.78.1 自身 requires glib2/2.88.0；必须对齐，配 glib/2.84.0.1 会 zlib 版本冲突 |
| gobject-introspection | 1.78.1 | template-glib 运行时用 GIRepository；**1.78.1.1 无 OHOS 二进制** |

## 关键适配决策
1. **introspection=disabled + gobject-introspection 包并存**：src/meson.build 无条件 dependency('gobject-introspection-1.0')（链接 libgirepository），由 GI 包满足；-Dintrospection=disabled 只关 g-ir-scanner/gir/vapi 生成（generate_vapi 嵌套在 generate_gir 内一并跳过）。
2. **glib2 .pc 兼容层（at-spi2-core 先例）**：PkgConfigDeps 只生成聚合 glib-2.0.pc。generate() 内补：glib_mkenums/glib_genmarshal 变量（gnome.mkenums 经 pkg-config 变量定位工具）、-I"${prefix}/include"（proxy-libintl 的 libintl.h）、gobject-2.0/gio-2.0/gmodule-2.0 薄包装 .pc（meson dependency('gio-2.0') 按单模块名解析）。
3. **MesonToolchain 工具修复（at-spi2-core 先例）**：弹出 AR/AS/STRIP/NM/RANLIB（CI 导出 llvm-* 裸名 meson 找不到），用 shutil.which 绝对路径锁入。
4. **flex/bison/sed/msgfmt**：构建期代码生成（tmpl-expr-parser.y/tmpl-expr-scanner.l 经 bison/flex/sed 管线）+ po/i18n；设备与 CI 的 /data/service/hnp/bin 均有。
5. **静态交付**（shared=False 默认）：非系统同名库，R26 无冲突；requires 带 transitive_headers+transitive_libs（消费者要拿 glib/GI 头与库）。

## 测试四维账本
| 维度 | 数值 | 说明 |
|---|---|---|
| 上游静态 N_static | 2 | tests/test-expr.c、tests/test-template.c 各注册 1 个 g_test 用例（grep g_test_add_func），meson test 驱动 |
| 实际执行 | 2 | meson test 分别运行两个可执行 |
| 通过 | 1 | /Tmpl/Template/test1（test-template）PASS |
| 平台限制跳过（test_skipped） | 1 | /Tmpl/Expr/test1（test-expr）：GIRepository 运行时 require('GLib') 需 GLib-2.0.typelib；glib2/2.88.0 构建 introspection=disabled、GI 包与 /system 系统镜像 find '*.typelib' 均为空，生成需 g-ir-scanner 全量 introspection 构建（OHOS 无工具链）。证据：`not ok /Tmpl/Expr/test1 - assertion failed (error == NULL): Typelib file for namespace 'GLib' (any version) not found (g-irepository-error-quark, 0)`（meson-logs/testlog.txt） |
| 消费者测试 N_consumer | 1 | test_package/test_tmpl.c：tmpl_template_parse_string("Hello {{name}}!") + tmpl_scope_set_string + tmpl_template_expand_string 断言输出 "Hello HarmonyOS!"；真实编译/链接/运行（语法 {{}}，scope 是 boxed 类型用 tmpl_scope_unref） |

适配后合计 3（上游 2 + 消费者 1）≥ N_static 2。

## 踩坑记录（按轮）
1. conandata.yml 版本嵌套 + `get(**self.conan_data["sources"])` → TypeError：本仓惯例 sources 平铺不嵌版本。
2. GI 1.78.1.1 无 OHOS 二进制 → 触发 python/3.12.9 源码构建 → 设备 HMDFS getcwd 挂（working directory cannot be determined）：改用有二进制的 1.78.1。
3. glib/2.84.0.1 + GI 同图 → zlib/1.3.1 vs zlib/1.3.1.1 Version conflict：对齐 glib2/2.88.0（pygobject 先例）。
4. test_package CMakeLists 缺 cmake_minimum_required（CI 的 CMake 4.1 硬要求）。
5. meson 静态产物名是 libtemplate_glib-1.0.a（带 apiversion 后缀），cpp_info.libs 必须写 template_glib-1.0，CMakeDeps 找得到。
6. 消费者测试模板语法是 {{expr}} 而非 ${expr}（${} 被当字面量）；TmplScope 是 boxed 类型，释放用 tmpl_scope_unref，用 g_object_unref 会段锁。

## 状态
- conan-verify：G0/G1/G2/G3/G4/L2/L4/L5 全 PASS（第 9 轮）
- 状态：built
---

**编译结束**: 2026-09-15 01:59
**最终状态**: built
