# corepdf 1.0 适配笔记

## 编译环境
- 构建系统: cmake (原项目使用qmake，因OpenHarmony环境qmake不生成Makefile而改用cmake)
- 编译日期: 2026-09-03
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码到downloads目录
2. init-build 初始化构建上下文
3. 将WebEngine依赖替换为poppler-cpp（主要源码适配）
4. 创建CMakeLists.txt（替代qmake）
5. cmake配置和编译:
   ```
   mkdir build && cd build
   cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release
   make -j1
   ```
6. make install DESTDIR=$TEST_PREFIX (staging)
7. ELF签名: ohc-run.py sign-elf
8. make install (本地验证)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Qt WebEngine不可用 | OpenHarmony未包含WebEngine模块 | 替换为poppler-cpp进行原生PDF渲染 |
| 2 | qmake无法生成Makefile | OpenHarmony环境的qmake配置问题 | 创建CMakeLists.txt替代qmake |
| 3 | poppler-qt6不可用 | poppler 25.12.0.2构建时ENABLE_QT6=OFF | 改用poppler-cpp C++绑定 |
| 4 | poppler-cpp page::render返回image非QImage | API差异 | 手动转换poppler::image到QImage |
| 5 | CMake无法找到poppler库 | Environment设CMAKE_PREFIX_PATH无效 | 使用CMakeDeps生成find_package配置 |

## 源码修改

- 0001-0007: 将WebEngine替换为poppler-cpp的完整适配补丁（分7个文件）
  主要修改文件:
  - CMakeLists.txt: 新增cmake构建配置，使用CMakeDeps + find_package(poppler)
  - ccorepdf.pro: 修复depends名称(pdfviewer→corepdf)
  - corepdf/corepdf.cpp: 移除WebEngine依赖的initialized信号连接
  - corepdf/corepdf.pro: 添加poppler-cpp链接
  - corepdf/main.cpp: 添加命令行参数解析
  - qpdflib/qpdflib.pro: 替换WebEngine为poppler-cpp
  - qpdflib/qpdfwidget.h/cpp: 使用poppler-cpp重写PDF渲染

## 依赖版本

- Qt6: 6.11.1 (qtbase conan package)
- poppler-cpp: 25.12.0.2
- clang: 15.0.4

## 验证结果

```bash
# 二进制签名后可执行（Qt platform plugin错误为无头环境正常现象）
LD_LIBRARY_PATH=/storage/Users/currentUser/usr/local/lib corepdf --help
# Output: Usage information displayed correctly
```

## 交付物

| 文件 | 说明 |
|------|------|
| corepdf (72KB) | 主二进制可执行文件 |
| libqpdf.a | 静态库（内嵌poppler渲染） |

## 注意事项

1. corepdf运行需要LD_LIBRARY_PATH包含poppler和Qt6库路径
2. 原WebEngine/PDF.js资源文件(qpdflib/pdfview/)不再使用但保留在源码中
---

**编译结束**: 2026-09-03
**最终状态**: built

## 修复记录 (2026-09-18, 第二轮 CI 修复)

1. **W2 原子性违规**: 移除误提交到本分支的 sysfsutils/2.1.0 文件
   (conandata.yml + test_package/, commit 1906b828d) — CI JC6 报
   "涉及 2 个软件包"。sysfsutils 补全应在独立分支/PR 进行。
2. **补丁修复**: 0003/0005/0006 三个补丁存在格式损坏
   (hunk 行数错误、空行标记误用为上下文、上下文行内嵌破折号、
   删除行多余反斜杠), 导致 apply_conandata_patches 失败。
   0006 同时按 poppler 25.12.0.2 真实 API 重写:
   - page::render() 不存在 → page_renderer::render_page()
   - page::search_for_text() 不存在 → page::search() 循环计数
   - poppler::page::rotation_enum → 全局 poppler::rotation_enum
   - toc 迭代 → toc::root() + toc_item::children_begin/end
   - 补充 #include <poppler-page-renderer.h> / <poppler-toc.h>
3. 本地复验: conan create (ohos-aarch64) 全绿, test_package 执行
   `QT_QPA_PLATFORM=offscreen corepdf --help` 输出 usage 并 exit 0。

**编译结束**: 2026-09-18
**最终状态**: built
