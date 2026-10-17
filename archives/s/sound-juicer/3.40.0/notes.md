# sound-juicer 3.40.0 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-09-17
- 编译器: clang/clang++ (OHOS aarch64)
- 状态: built（conan create + test_package 全部通过）

## 编译步骤

使用 Conan 驱动构建（模式 A/B 混合）：
1. `ohc-run.py init-build sound-juicer 3.40.0` — 下载 GNOME 官方源码包
2. `ohc-run.py conan-init sound-juicer 3.40.0` — 生成 conanfile.py + conandata.yml + test_package/
3. `conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing` — 本地完整验证
4. `ohc-run.py finish sound-juicer 3.40.0 built` — 归档收尾
5. `ohc-run.py submit sound-juicer 3.40.0` — 提交 PR

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CI 失败: `Version conflict: Conflict between zlib/1.3.1.1 and zlib/1.3.1 in the graph. Conflict originates from glib/2.84.0.1` | gtk/3.24.43 依赖 glib/2.84.0.1（zlib/1.3.1.1），gstreamer/1.28.3 依赖 glib2/2.88.0（zlib/1.3.1）——两个 glib 配方同图导致 zlib 版本冲突 | requirements() 中 `self.requires("zlib/1.3.1.1", force=True)` 对齐 zlib；PkgConfigDeps 将规范名 glib-2.0.pc 给 glib 包，整个应用只链接一份共享 glib |
| 2 | 补丁 0007/0008/0010 在 conan 的 patch_ng 下解析/应用失败 | 旧补丁用无时间戳的 `diff -ruN a/x b/x` 新文件格式，patch_ng 不识别为新文件；多文件补丁集还会静默失败 | 全部补丁重新生成为 git 风格（新文件用 `--- /dev/null`），并用 patch_ng strip=0 全量验证 |
| 3 | 0007 创建 stub-ohos.c 在仓库根目录而非 libjuicer/ | 旧补丁路径错误（从未真正通过本地构建验证） | 重建为 libjuicer/stub-ohos.c，与 0001 的源文件列表一致 |
| 4 | meson configure: `Unknown linker(s): llvm-ar...` | CI 环境导出 llvm-* 工具名但不在 PATH | generate() 中按 glib2/gstreamer/gtk 配方同款方式以绝对路径固定 ar/as/strip/nm/ranlib |
| 5 | meson configure: `Dependency "gstreamer-1.0" not found` | conan gstreamer 包生成 gstreamer.pc（无 -1.0 后缀） | generate() 在 generators 目录写 gstreamer-1.0.pc 重定向（Requires: gstreamer） |
| 6 | meson configure: `Could not get pkg-config variable ... gio-2.0` | meson gnome 模块通过 gio-2.0.pc 的 glib_compile_schemas 变量查找工具，conan 生成的 pc 缺该变量 | generate() 向 gio-2.0.pc 追加 glib_compile_schemas/glib_compile_resources 变量指向签名后的工具副本 |
| 7 | glib/gtk 构建工具（glib-compile-schemas 等）执行报 operation not permitted | OHOS 拦截未签名 ELF 执行 | 参照 gtk/3.24.43 配方：把工具复制到 build_folder/conan-native-tools 并用 binary-sign-tool 自签 |
| 8 | 链接失败: undefined `g_libintl_*` | glib 用 proxy-libintl 构建，glib/gi18n.h 将 gettext() 映射为 g_libintl_* | 参照 gtk 配方向 glib-2.0.pc 的 Libs 追加 -lintl |
| 9 | gdesktop-enums.h 找不到 | conan gsettings-desktop-schemas 包的 pc Cflags 指向 include/gsettings-desktop-schemas/（支持裸 include），上游 sj-metadata-getter.c 用带前缀路径 | 0003 补丁在 HAVE_STUB_DEPS 下改用裸 include（真包依赖，非 stub） |
| 10 | gstreamer-pbutils-1.0 / gstreamer-plugins-base-1.0 不存在 | gst-plugins-base 未发布到制品仓 | meson 中改为 optional + stubs/gst/pbutils/*.h + stub-ohos.c 提供 encoding-profile API 桩（全部返回 NULL，应用走"profile 不可用"路径） |
| 11 | data/meson.build 的 i18n.merge_file 需要 msgfmt | OHOS 工具链无 gettext | 0008 补丁改为 install_data 直接安装（.in 文件无构建期占位符） |
| 12 | test_package 曾为空壳（旧提交 test_main.c 只 printf，被 AI 检视判 R34 违规） | — | 重写 test.sh：定位二进制→验证 ELF→binary-sign-tool 签名副本→真实运行 --help→断言输出含 Usage/Help Options |
| 13 | 旧 0003 补丁改动 g_regex_new 正则 | 实测原正则在 glib 2.84 正常工作（MATCH pos=10 disc=2），"修复"是幻觉 | 撤销该改动，保留上游正则 |

## 依赖策略（不裁剪原则）

- **真依赖**（制品仓已发布）: glib/2.84.0.1、gstreamer/1.28.3、gtk/3.24.43、gsettings-desktop-schemas/49.1、iso-codes/4.20.1
- **桩实现**（制品仓未发布，无法获取）: libbrasero（光盘刻录/驱动监测）、libmusicbrainz5（元数据查询）、libdiscid（光盘 ID，仅被已桩化的 musicbrainz5 后端使用）、libcanberra-gtk3（音效，制品仓仅有核心版无 gtk 变体）、totem-disc、gst-plugins-base/pbutils（编码 profile）
- **上游测试清点**: 上游 tests/test-browse.c（meson test）需要 CD 驱动 + gstreamer 插件 + gst-check 库（gstreamer 包未提供 libgstcheck），CI 环境不可运行 → tests/ 子目录跳过（0004），test_package 冒烟测试替代

## 验证结果

conan create（本地 OHOS 设备，与 CI 同款环境）：
- 27/27 编译目标通过（libjuicer 静态库 + sound-juicer 可执行文件）
- meson install + gnome.post_install（glib-compile-schemas / gtk-update-icon-cache 签名后执行）通过
- test_package 真实执行：
  - PASS: sound-juicer binary found
  - PASS: valid ELF binary
  - PASS: 签名副本运行 `--help` 输出 GApplication 用法文本（Usage / Help Options / Application Options）
- 应用运行时行为：GApplication/GTK/GStreamer 选项组全部注册，单一共享 glib 世界无符号冲突

## 注意事项

- 应用在 OHOS 上为"可启动但抓取功能受限"状态：CD 抓取需要 gst-plugins-base 的 encodebin/编码器插件（未发布）及 CD 驱动（brasero 桩）
- 单一 glib 世界依赖 PkgConfigDeps 的 pc 名消歧行为（glib 组件获得规范名，glib2 的 pc 不生成）——升级 conan 版本时需复验
- CI 环境需保证 /data/service/hnp/bin 在 PATH（profile [buildenv] 已配置）以找到 clang/binutils/binary-sign-tool/meson/ninja

---

**编译结束**: 2026-09-17
**最终状态**: built
