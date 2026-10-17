# DRAFT-librsvg-2.62.3.1-gdkpixbuf-svg-loader：OHOS gdk-pixbuf 生态缺 SVG loader → librsvg pixbuf-loader 适配发布

> Contributor: pc1-55（librsvg 2.62.3.1 r01） | Status: Draft | Updated: 2026-09-19
> Source: archives/l/librsvg/2.62.3.1（full conan create 本地通过，SVG loader 全链路验证绿）

## 现象

gtk4/4.22.4-r1 上游测试 svg 28+2timeout 项失败：SVG 图标/资源无法解码——
gdk-pixbuf 报"无法识别图片格式"类错误，根因是 gdk-pixbuf 生态缺少 **SVG loader
插件**（librsvg 提供的 `libpixbufloader_svg.so`）。制品仓既有 librsvg/2.62.3
为 `pixbuf-loader=disabled` 构建（无 loader 模块），且其依赖链（pango/1.56.4，
GTK4 生态）与 gtk4 图不匹配。R04 曾判 librsvg/2.62.3.1（依赖 gdk-pixbuf
2.44.6.1）与 gtk4 图（gdk-pixbuf/2.44.6）"版本冲突不可入图"。

## 根因

1. gdk-pixbuf 的 SVG 解码依赖 librsvg 构建的 loader 插件；loader 缺失时任何
   `gdk_pixbuf_new_from_file`/icon 主题 SVG 资源加载均失败。
2. 构建选项 `pixbuf-loader` 默认 disabled（2.62.3 制品仓为 disabled，无 loader）。
3. 启用 loader 需同时满足五件事，缺一不可：
   - meson 构建选项 `pixbuf-loader=enabled`；
   - `gdk-pixbuf-2.0.pc` 提供 `gdk_pixbuf_moduledir` / `gdk_pixbuf_cache_file`
     变量（PkgConfigDeps 生成版缺失；gdk-pixbuf-loader/meson.build 第 14/46/50 行
     `get_variable()` 依赖它们定位 loader 安装目录与 loaders.cache 路径）；
   - 构建期 `gdk-pixbuf-query-loaders` 可执行（meson `find_program()` 优先命中
     native file `[binaries]` 声明，故写入 conan_meson_native.ini）；
   - 安装期 `meson_install.py --queryloaders ... --cache-file ...` 生成
     loaders.cache（DESTDIR 下脚本自动跳过并以 stderr 提示手动生成）；
   - loader ELF 签名（OHOS 拒绝 execve 未签名 ELF）。

## 方案

1. `generate()`：`tc.project_options["pixbuf-loader"] = "enabled"`。
2. `_generate_alias_pcs()`：追加 `gdk_pixbuf_moduledir=${prefix}/lib/gdk-pixbuf-2.0/2.10.0/loaders`
   与 `gdk_pixbuf_cache_file=${prefix}/lib/gdk-pixbuf-2.0/2.10.0/loaders.cache`
   （2.10.0 为 gdk-pixbuf 2.44 的 ABI binary version）。
3. `_inject_gdkpixbuf_query_loaders()`：把 gdk-pixbuf 包
   `bin/gdk-pixbuf-query-loaders` 写进 `conan_meson_native.ini [binaries]`。
4. 安装期 `gdk-pixbuf-loader/meson_install.py` 以 `--queryloaders`/`--cache-file`
   参数生成 loaders.cache（ldd 依赖自动经 LD_LIBRARY_PATH 满足）。
5. `package()`：`llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign
   -selfSign 1` 对 loader .so 签名。

## 验证（本轮真实日志，2026-09-19）

- conan create 全绿（RC=0），`[4/6] Generating gdk-pixbuf-loader/pixbufloader-svg`；
- loader 随包安装：`lib/gdk-pixbuf-2.0/2.10.0/loaders/libpixbufloader_svg.so`
  （7.3MB，已签名）；
- `gdk-pixbuf-query-loaders`（GDK_PIXBUF_MODULEDIR 指向本包 loaders 目录）列出
  `"svg" 6 "gdk-pixbuf" "Scalable Vector Graphics"`；
- loaders.cache 生成且含 `libpixbufloader_svg` 条目；
- 进程级解码：独立 C 程序（仅 gdk-pixbuf 公开 API `gdk_pixbuf_new_from_file`）
  加载 24x24 SVG → `DECODE_OK 24x24 alpha=1`（RC=0）；
- 对照 2.62.3（disabled）无 loader 记录在台账。

## 适用边界

- 适用于"gdk-pixbuf 已安装但无 SVG loader 插件"的 OHOS aarch64 场景（gdk-pixbuf
  2.44 系，loader 模块目录 2.10.0）；跨库可复用（任何依赖 SVG 解码的库：
  gtk4/gtk3 测试环境、vips、imlib2 等 gdk-pixbuf 消费者）。
- 不适用于 gdk-pixbuf 自身缺库/签名类问题（属 E452/E322 域）；若下游改用非
  gdk-pixbuf 的 SVG 解码路径，本方案不适用。
- gdk-pixbuf 2.44.6.1 与 2.44.6 为同源 R37 后缀二进制发布版本（配方逐字节相同，
  ABI/SONAME/loader 模块目录全一致），loader 与任一 2.44.x 运行时兼容；联合图
  冲突仅版本 pin 层面，由消费侧 override/对齐解决。

## 与既有条目关系

- `similar_to`：E255（资源型库 test_package，均涉 gdk-pixbuf/SVG 关键词但非
  loader 缺失）；E090（meson custom_target 执行宿主二进制，构建期触发面交集）；
- `caused_by`：gdk-pixbuf 生态缺失 librsvg SVG loader（上游生态事实）；
- `prerequisite_of`：任何依赖 SVG 解码的下游库测试恢复（gtk4 后续轮）；
- `conflicts_with`：无。
- 七轴查重：exact_duplicate=false / causal_duplicate=false / trigger_overlap=
  部分交集非覆盖 / solution_overlap=无实质重叠 / **combination_novelty=true** /
  **boundary_novelty=true** / test_migration_novelty=false。

## 路径决定

`new_draft`（路径 B 成对草稿，.md/.kv 配对，随 librsvg 三方库归档同 PR 交付）。
