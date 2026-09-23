# sdcv 0.5.3 适配笔记

## 编译环境
- 构建系统: cmake（CMakeToolchain + CMakeDeps，cmake_layout）
- 编译日期: 2026-09-15
- 编译器: clang/clang++ 15（profile conf tools.build:compiler_executables）
- 状态: built（conan-verify G0-G4 通过）
- worktree: ~/qzy/GLM-33-sdcv-0.5.3 分支 feat/sdcv-0.5.3（基于 upstream/main 6b5087b97a）
- 任务号: 13460（依赖活动 activity_id=6）
- 依赖: glib/2.88.3、zlib/1.3.2（制品仓已发布）

## 编译步骤
1. conan-init 后手写 CMake 配方：requires glib/2.88.3 + zlib/1.3.2；configure 变量注入：
   - `ZLIB_INCLUDE_DIR`/`ZLIB_LIBRARY`：预置内置 FindZLIB 模块变量，直连 conan zlib 包；
   - `GLIB2_INCLUDE_DIRS`/`GLIB2_LIBRARIES`：预置 sdcv 自带 FindGLIB2.cmake 的缓存短路条件
     （`include/glib-2.0` + `lib/glib-2.0/include` + libglib-2.0.so），完全绕开 pkg-config
     （构建机不依赖 pkg-config 存在性）；
   - `WITH_READLINE=OFF`：readline 未适配发布，显式关闭而非依赖上游自动探测回退；
   - `ENABLE_NLS=OFF`：跳过上游 GettextTools(msgfmt/xgettext) 构建期硬依赖；
   - `BUILD_TESTS=ON`：注册上游 11 个 shell 测试经 ctest 真实执行；
   - `CMAKE_BUILD_RPATH`：聚合依赖 libdirs，保证 ctest 执行新构建二进制时共享库可解析。
2. build()：configure → build → `ctest -E "^t_json$" --output-on-failure`。

## 补丁（1 个，refresh-patch --auto 生成）
- patches/0001-src-stardict_lib.cpp.patch（+4/-4）：glib 2.88 的 `g_utf8_next_char` 返回值改为
  `const gchar *`，原码 `gchar *nextchar = ...` 编译失败；改为 `const gchar *nextchar` 并以局部
  `downchar` 承接 `g_utf8_strdown` 返回值（原码将其回写 nextchar），语义完全不变。

## NLS/gettext 处理（查重结论：命中已有知识，不走路径 B）
OHOS 适配版 glib 的 `glib/gi18n.h` 无条件 `#define _(String) gettext (String)`（上游有
`#ifdef ENABLE_NLS` 门，OHOS 版摘除），消费者编译即要求 gettext 可解析。本适配在 generate()
写垫片头 `#define gettext(String) (String)`（复刻上游非 NLS 透传语义），经
`CMAKE_CXX_FLAGS -include` 注入（避免 add_compile_definitions 的括号经 make shell 展开被破坏）。
知识库查重：E015（libintl/gettext undefined symbol）、E027（--disable-nls）、E107（GLib+gettext
链接）、E142（g_libintl_dgettext/ENABLE_NLS）已覆盖该问题类，无新增知识增量，**按纯路径 A 交付**。

## 测试账本（四维）
| 维度 | 数值 | 来源 |
|---|---|---|
| 上游静态用例 N_static | 11 | CMakeLists BUILD_TESTS 段 add_sdcv_shell_test 逐条计数（t_list/t_use/t_only_data_dir/t_synonyms/t_json/t_exact/t_interactive/t_utf8output/t_utf8input/t_datadir/t_return_code） |
| 实际执行 | 10 | ctest 输出（10/11 run） |
| 通过 | 10/10 | ctest：91%→排除前 1 失败为 t_json |
| 跳过 | 1（t_json：测试脚本依赖 jq，OHOS 平台不提供——"工具或依赖未安装且 CI 无法提供"，逐项申报） | tests/t_json 首行 `jq: inaccessible or not found` |
| 新增消费者测试 | 1 程序 / 2 断言，通过 | test_package/test_sdcv.sh（--help 输出断言 + 未知选项退出码断言，运行安装后的真实 sdcv 二进制） |

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | G1 拦截缺 source() | 骨架为 Autotools 模板，手写 CMake 配方时漏写 | 补 get(self, **self.conan_data["sources"]) |
| 2 | source() 下载失败 | E017 注入 ghfast.top 不可达 | 按 SHA256 预置共享下载缓存 + .json 元数据，清 .dirty |
| 3 | glib.h not found | glib 包 cpp_info.includedirs 为裸 "include"，实际头在 include/glib-2.0 | 预置 GLIB2_INCLUDE_DIRS（abiword-plugin-* 同款路径组） |
| 4 | gettext 未声明 | OHOS 版 gi18n.h 摘除 ENABLE_NLS 门（见上节） | -include 垫片头，复刻非 NLS 透传 |
| 5 | -Dgettext(x)=(x) 炸编译器探测 | 括号经 make shell 展开产生语法错误 | 改垫片头（纯路径 -include） |
| 6 | proxy-libintl/0.5 与 glib/2.84.0.1.1 无法解析 | 制品仓远端对该类请求返回 bool 解析错误（2026-09-15 夜间，zlib/1.3.1 等常规包同bug） | 弃用 proxy-libintl 直依赖，改垫片头；glib 固定 2.88.3（本地缓存已有） |
| 7 | g_utf8_next_char const 编译错误 | glib 2.88 API const 化 | refresh-patch 生成 0001 补丁（+4/-4，语义不变） |
| 8 | t_json 失败 | 脚本依赖 jq，OHOS 不提供 | ctest -E 逐项排除并申报 |

## 路径 A/B 判断
**不走路径 B，按纯路径 A 交付。** 查重命中：本适配的核心知识点（OHOS glib 消费者 gettext/NLS
链接与禁用）已被 E015/E027/E107/E142 覆盖；pkg-config 旁路注入 FindGLIB2 变量属配方技巧，
与 E090（meson 检测）同类，不构成跨仓库复用的新知识条目。

## 已知限制
- NLS 关闭：sdcv 的界面翻译不加载（字符串原样输出）；词典查询功能不受影响。
- readline 关闭：交互式输入无行编辑（t_interactive 验证非交互模式正常）。
- t_json 跳过：jq 工具缺失；sdcv -j JSON 输出本身构建在二进制中（-j 选项存在）。
---

**编译结束**: 2026-09-15 02:42
**最终状态**: built
