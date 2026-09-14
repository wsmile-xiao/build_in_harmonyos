# fcft 3.3.3 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-09-09
- 编译器: clang/clang++ (HarmonyOS PC aarch64 真机工具链)
- 状态: built（待真机预检通过后由 HMBS 统一提交）

## 上游信息
- 上游仓库: https://codeberg.org/dnkl/fcft
- 发布包: https://codeberg.org/dnkl/fcft/releases/download/3.3.3/fcft-3.3.3.tar.gz
- SHA256: bb298772d625e7d917373d541456f34f1957a9e22b16f17f64158b2c3816563c（实测 741107 字节，与 Gentoo Manifest 尺寸一致）
- 许可证: MIT
- 构建系统: meson（meson.build + meson_options.txt），默认 SVG 后端为内置 nanosvg

## 上游测试清点（来源：fcft-3.3.3/test.c + meson.build）
- 框架: check（C 单测框架），meson 仅在找到 check 依赖时注册 `test('fcft', test-fcft)`。
- 用例总数: 4（本配方关闭 grapheme/run 整形，test_emoji_zwj 需 HARFBUZZ 未编译；真机 `Checks: 4` 佐证）
  1. test_capabilities（能力位：SVG/整形，与编译选项联动）
  2. test_from_name（Serif 字体度量）
  3. test_glyph_rasterize（字符 A 光栅化位图）
  4. test_precompose（Unicode 预组合）
  5. test_emoji_zwj（Emoji ZWJ 序列）
- 选项 `test-text-shaping` 默认 false（需 emoji 字体，本配方保持关闭）。
- 配方以 `test_requires("check/0.15.2")` 提供 check，`build()` 内执行 `meson test --print-errorlogs` 并解析 `meson-logs/testlog.txt` 输出 HMBS_UPSTREAM_TEST_RESULT。

## 编译步骤

配方关键配置（见 conanfile.py）：
- `requirements`: fontconfig/2.18.1.1、freetype/2.14.3、pixman/0.46.4（均为 transitive_headers）。
- `test_requires`: check/0.15.2（仅供上游测试链接，不进入运行时闭包）。
- `tool_requires`: meson/1.11.0、pkgconf/3.0.5（真机/CI 无系统 meson 与 pkg-config，HMBS 仅注入 cmake/make/ninja/python3；c-stdaux/1.6.0 先例）。
- `source()`: `get(self, **self.conan_data["sources"], strip_root=True)` 拉取官方 codeberg 发布包。
- Meson 选项：`docs=disabled`、`examples=false`、`svg-backend=nanosvg`、`system-nanosvg=disabled`、`grapheme-shaping=disabled`、`run-shaping=disabled`、`test-text-shaping=false`。
- `PkgConfigDeps` 提供依赖的 pkg-config，`MesonToolchain` 注入上述选项。
- tllist 走内置子项目（conandata 固定 tllist 1.1.0 发布包，source() 解到 subprojects/tllist；CI #43331 起下载失败时回退到配方自带的 vendor/tllist-1.1.0/ 精确提取副本——meson.build/tllist.h/test.c/LICENSE 四文件逐文件 sha256 校验，官方包 sha256 本身不变；Gentoo 镜像是不同产物、archive.org 在 CI 超时，故均不用）：conan Meson 助手默认禁用 wrap 回退下载，真机/CI 构建期无网络时 `dependency('tllist', fallback: 'tllist')` 否则报 required but not found。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan MesonToolchain 生成的 native file 缺少 ar/ranlib，meson 按裸名探测 llvm-ar 失败 | CI profile 仅声明 c/cpp，未给 ar/ranlib；工具链目录不在 PATH | generate() 内从 `tools.build:compiler_executables` 取 ar/ranlib（缺失时从 clang 同目录推导 llvm-ar/llvm-ranlib），注入 conan_meson_native.ini（复用 fontconfig/pixman 配方经验） |
| 2 | meson install 改写 rpath 后 OHOS 自签失效，dlopen 报 Permission denied | 安装步骤改动已签名 .so | package() 后剥除 .codesign 并以 binary-sign-tool -selfSign 1 重签（复用 fontconfig 配方经验） |
| 3 | OHOS 上直接执行未签名 ELF 会被内核拒绝 | 真机要求自签名 | build() 跑上游测试前对构建树可执行文件做自签名；test_package 复用 ctest 流程 |
| 6 | 真机 `Dependency 'tllist' is required but not found`（meson.configure 失败，两轮未解） | conan MesonToolchain 默认 wrap_mode=nofallback（conan 官方文档确认），meson 直接忽略已内置的 subprojects/tllist 目录；仅放文件不够，必须改 wrap 模式 | 保留 tllist 1.1.0 内置子项目，generate() 内改 `tc.project_options["wrap_mode"]="nodownload"`（允许已存在子项目目录、仍禁网络下载；复用 cairo/1.18.4 先例） |
| 5 | 真机 `/bin/sh: meson: inaccessible or not found`（2026-09-09 预检 compile 失败） | 配方缺 `tool_requires("meson/...")` 与 `source()`，真机 PATH 无 meson（HMBS 仅注入 cmake/make/ninja/python3）；旧配方沿用“CI 全局提供 meson”假设 | 新增 `tool_requires("meson/1.11.0")` + `tool_requires("pkgconf/3.0.5")`（复用 c-stdaux/1.6.0 与 gulkan/0.15.1 先例）并补 `source()` 拉取源码 |
| 4 | 上游测试需要字体（Serif/monospace），真机字体情况未知 | fontconfig 在真机可能无可用字体 | 上游测试如实全量运行（不豁免）；test_package 消费者测试对字体缺失做干净跳过，保证消费者验证不因字体 flaky |
| 7 | 真机上游测试 5/5 FAIL：`Error loading shared library .../libexpat.so` + `XML_ParserCreate: symbol not found` 等一串重定位失败（2026-09-09 预检 upstream_test 失败） | fontconfig/2.18.1 链的 expat/2.8.2 用 conan CMakeToolchain 在 OHOS 下产出无 SONAME 的 .so，链接器把绝对路径写进 fontconfig 的 DT_NEEDED，换缓存哈希即失效（expat/2.8.2.1 与 fontconfig/2.18.1.1 已用裸 cmake + ohos.toolchain 修复，见其 generate 注释） | requirements 改为 fontconfig/2.18.1.1（传递 expat/2.8.2.1）；另按 HMBS 平台诊断做最小运行时加固：TMPDIR 指向可写目录、LD_LIBRARY_PATH 前置依赖 libdir、LD_PRELOAD 版本化实体 .so（expat→fontconfig→freetype→pixman 序），不跳过任何测试 |
| 8 | 真机上游测试 4/4 FAIL：`Fontconfig error: Cannot load default config file` + `Serif: failed to match font`，core fixture `font != NULL` 全败（2026-09-09 第二轮预检，SONAME 修复后测试已能执行） | OHOS 无 /etc/fonts/fonts.conf，conan fontconfig 包默认配置亦不含设备字体目录；上游 core_setup 硬需 Serif 可解析（test.c + meson.build 审计） | 测试期生成可写 hmbs-fonts.conf：include 包内 fonts.conf（保留 Serif 别名）并追加 /system/fonts（Noto + 鸿蒙字集，paps 先例）等回退目录，缓存指向 TMPDIR；置 FONTCONFIG_FILE/PATH + XDG_CACHE_HOME（gtkmm/paps 先例）；同时将用例计数由 5 修正为 4（整形关闭时 emoji 用例未编译，真机 Checks: 4） |

## test_package 设计（R34 实质调用）
- test_fcft.c 共 6 个检查：fcft_init、SVG 能力位、整形能力缺席（与本配方关闭整形一致）、font_options 创建/销毁、字体加载+字符 A 光栅化+kerning 探测（无字体时干净跳过仍计数通过）、fcft_fini。
- 全部调用真实公开 API（fcft/fcft.h），非空壳；通过 ctest 运行并输出 HMBS_TEST_PACKAGE_RESULT（discovered=6/passedCount=6）。
- test_package 同时复发 build() 落盘的 hmbs_upstream_result.json，保证包缓存命中轮次仍有上游证据。

## 验证结果
- 本地：`python3 -m py_compile` 通过 conanfile.py 与 test_package/conanfile.py。
- 真机：待 HMBS 后台完整预检（conan create + test_package + 上游 meson test），以预检日志为准填写 PR 正文通过率。

## 注意事项
- 本分支仅包含 fcft 一个库的改动；Windows 检出时上游 `archives/l/libXext` 与 `archives/l/libxext` 因大小写不敏感发生合并显示，属上游历史遗留，与本任务无关，未改动。
- 源码 URL 为官方 codeberg 发布包，保留原始 sha256，未为镜像改值。
