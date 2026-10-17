# E324 — poppler-qt5 缺失时用 poppler-cpp shim 兼容

## 场景

上游 GUI 应用（diffpdf 等 PDF 工具）需要 poppler 的 **Qt5 绑定**
（`find_package(Poppler COMPONENTS Qt5)` + `#include <poppler-qt5.h>`），
但制品仓 poppler 包全线 `ENABLE_QT5=OFF / ENABLE_QT6=OFF`（Qt 绑定会把
poppler 耦合到特定 Qt 大版本），也没有独立 poppler-qt5 包。

## 解法

写 **poppler-qt5 兼容 shim**（两个文件随补丁进源码树），在 poppler-cpp
前端（制品仓 poppler 包自带 `libpoppler-cpp.so` + `poppler/cpp/*.h`）之上
重实现应用实际用到的 API——典型 PDF GUI 应用只碰
`Poppler::Document / Page / TextBox` 的一小撮方法。

## diffpdf 2.1.3.1 实测 API 映射

| poppler-qt5 API | poppler-cpp 对应 |
|---|---|
| `Document::load(file)` | `document::load_from_file()` |
| `Document::isLocked()` | `is_locked()` |
| `Document::numPages()` | `pages()` |
| `Document::page(i)` | `create_page(i)` |
| `Document::infoKeys()/info(k)` | `info_keys()/info_key(k)` |
| `Document::date(k)` | `info_date_t(k)` + `QDateTime::fromSecsSinceEpoch` |
| `Document::setRenderHint()` | 存 Document 成员，渲染时 `page_renderer::set_render_hints` 应用 |
| `Page::pageSize()` | `page_rect(crop_box)` 的宽高 |
| `Page::renderToImage(xres,yres,x,y,w,h)` | `page_renderer::render_page()` + `image::format_argb32` → `QImage::Format_ARGB32`（native endian，aarch64 LE 匹配），copy() 脱离 poppler 缓冲 |
| `Page::textList()` | `page::text_list()`（`vector<text_box>` → 堆分配 `TextBox*`，所有权随 Page） |
| `TextBox::text()` | `text_box::text().to_utf8()` |
| `TextBox::boundingBox()` | `bbox()` |
| `TextBox::charBoundingBox(i)` | `char_bbox(i)` |

## 三个坑

1. **枚举位置**：poppler-cpp 的 `crop_box`/`rotate_0` 等枚举在 `poppler`
   全局命名空间，**不是** `poppler::page::crop_box`（编译报 no member）。
2. **ustring 转换**：`ustring::to_utf8()` 返回 `poppler::byte_array`
   （`std::vector<char>`），不是 `std::string`。
3. **include 根**：shim 用 `#include <poppler/cpp/poppler-document.h>`，
   传 `-I include` 与 `-I include/poppler` 两个根（poppler 包 cpp_info
   includedirs 即这两个）。

## 验证口径

上游源文件零修改 + `conan create`（编译/链接/test_package）全过即证 shim
API 面覆盖应用实际调用。GUI 冒烟走 `--help`（QApplication 初始化即
Qt 加载链路验证，R40 链路级口径）。

参考实现：`archives/d/diffpdf/2.1.3.1/patches/0001-add-cmakelists-for-ohos-poppler-cpp-build.patch`
