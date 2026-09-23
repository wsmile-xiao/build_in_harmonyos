# PlutoBook - Paged HTML Rendering Library

## 简介
PlutoBook 是一个分页 HTML 渲染库，将 HTML/CSS/SVG 渲染为 PDF、PNG 或 Cairo 支持的任意输出格式。
文字排版依赖 ICU + HarfBuzz，字体访问依赖 Fontconfig + FreeType，绘制与 PDF/PNG 输出依赖 Cairo，
XML 解析依赖 Expat，可选远程资源加载依赖 libcurl。

## OHOS 适配
- 构建系统：Meson（上游 0.19.0 无 CMakeLists）
- 依赖全部使用 Conan 制品仓包：cairo/1.18.4、harfbuzz/14.3.0、freetype/2.14.3、
  fontconfig/2.18.1.1、expat/2.8.2.1、icu4c/77；可选 curl/8.15.0、libjpeg-turbo/3.2.0、libwebp/1.6.0
- 上游强制 C++20，配方内显式覆盖 cpp_std
- 上游 meson 需要 cairo 的 4 个子特性 .pc（cairo-pdf/png/ft/fc）与 libturbojpeg.pc，
  由配方 generate() 转发生成
- 交付产物：libplutobook.so + html2pdf / html2png 命令行工具

## 功能
- 分页布局与打印级输出（CSS 3 / 部分 CSS 4、HTML5、XHTML、SVG）
- PDF / PNG / Cairo 表面输出
- 国际化文本排版（ICU + HarfBuzz，含阿拉伯语、希伯来语、印地语等）
- Emoji（位图与矢量）渲染

## 依赖关系
```
plutobook/0.19.0 (meson, C++20)
├─ 强制: cairo/1.18.4 → pixman/0.46.4, libpng/1.6.58, freetype/2.14.3, fontconfig/2.18.1.1, zlib/1.3.1.1
├─ 强制: harfbuzz/14.3.0 → freetype/2.14.3
├─ 强制: fontconfig/2.18.1.1 → freetype/2.14.3, expat/2.8.2.1
├─ 强制: freetype/2.14.3 / expat/2.8.2.1 / icu4c/77
└─ 可选: curl/8.15.0（→openssl/3.5.6.1）、libjpeg-turbo/3.2.0、libwebp/1.6.0
```
> 顶层 requires 版本必须与 cairo/1.18.4 链路严格一致，否则 Conan 报 Version conflict。

## 参考资料
- 上游仓库：https://github.com/plutoprint/plutobook
- 上游构建文件：`meson.build`（0.19.0 无 CMakeLists）、`meson_options.txt`
- 适配记录：`0.19.0/notes.md`（含 conan-verify G2 环境说明）、`0.19.0/reports/test-report.md`
- 知识条目：`knowledge/drafts/E543-draft-0695.kv`（OHOS libc++ 缺 std::pmr / C++20 ranges）

## 许可证
MIT
