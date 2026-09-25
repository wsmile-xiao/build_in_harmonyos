# tidyhtml

> HTML Tidy HTML 检查与格式化库及 tidy 命令行工具。

## 简介

tidyhtml（上游仓库 tidy-html5）用于读取 HTML、XHTML 与 XML 文档并输出清理后的标记，
可检测并修正常见编码错误，生成与 W3C 兼容、可视等价的文档。产物包括 `libtidy`
库与 `tidy` 命令行工具（含 `tab2space` 辅助工具）。

上游 5.8.0 为偶数次版本号稳定发布，全系 5.8.x 保证 ABI/API 稳定。

## OHOS 适配要点

- 上游顶层 `CMakeLists.txt` 声明 `cmake_minimum_required(VERSION 2.8.12)`，
  CMake 4.x 已移除对低于 3.5 的兼容，需补丁升至 `3.5...3.27`。
- OHOS 下共享库构建需覆盖 `CMAKE_SHARED_LIBRARY_SONAME/RUNTIME/RPATH_LINK`
  标志并启用 `CMAKE_BUILD_RPATH_USE_ORIGIN`，安装后清理 `.codesign`
  段并自签名（与已发布 tidy-html5/5.8.0 同方案）。
- 上游发布包不含测试套件（BLFS 明确标注 This package does not come with
  a test suite），功能验证由 `test_package` 真实调用 libtidy API 完成。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| 无 | - | 上游独立编译，无外部依赖 |

## 功能验证

```bash
tidy --version
```

## 参考

- [官方文档](https://www.html-tidy.org/)
- [源码仓库](https://github.com/htacg/tidy-html5)
