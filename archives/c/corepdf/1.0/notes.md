# corepdf 1.0 适配笔记

## 编译环境
- 构建系统: cmake (原项目使用qmake，因OpenHarmony环境qmake不生成Makefile而改用cmake)
- 编译日期: 2026-05-29
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 下载源码到downloads目录
2. init-build 初始化构建上下文
3. 将WebEngine依赖替换为poppler-qt6（主要源码适配）
4. 创建CMakeLists.txt（替代qmake）
5. cmake配置和编译:
   ```
   mkdir build && cd build
   cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release
   make -j1
   ```
6. make install DESTDIR=$TEST_PREFIX (staging)
7. 修复RPATH: patchelf --set-rpath 和 --replace-needed
8. ELF签名: ohc-run.py sign-elf
9. make install (本地验证)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Qt WebEngine不可用 | OpenHarmony未包含WebEngine模块 | 替换为poppler-qt6进行原生PDF渲染 |
| 2 | qmake无法生成Makefile | OpenHarmony环境的qmake配置问题 | 创建CMakeLists.txt替代qmake |
| 3 | poppler Document::load返回unique_ptr | poppler 23.12.0 API变更 | 使用.release()转换为原始指针 |
| 4 | libpoppler-qt6.so NEEDED路径错误 | 编译时NEEDED为../../libpoppler.so | patchelf --replace-needed修复 |
| 5 | Qt platform plugin缺失 | 无头环境无显示器 | 正常运行环境问题，不影响编译 |

## 源码修改

- 0001-poppler-qt6-adaptation.patch: 将WebEngine替换为poppler-qt6的完整适配补丁
  主要修改文件:
  - CMakeLists.txt: 新增cmake构建配置
  - ccorepdf.pro: 修复depends名称(pdfviewer→corepdf)
  - corepdf/corepdf.cpp: 移除WebEngine依赖的initialized信号连接
  - corepdf/corepdf.pro: 添加poppler-qt6链接
  - corepdf/main.cpp: 添加命令行参数解析
  - qpdflib/qpdflib.pro: 替换WebEngine为poppler-qt6
  - qpdflib/qpdfwidget.h/cpp: 使用poppler-qt6重写PDF渲染

## 依赖版本

- Qt6: 6.11.1
- poppler-qt6: 23.12.0
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

1. corepdf运行需要LD_LIBRARY_PATH包含poppler-qt6和Qt6库路径
2. poppler-qt6.so的NEEDED路径需要patchelf修复后才能正确加载
3. 原WebEngine/PDF.js资源文件(qpdflib/pdfview/)不再使用但保留在源码中
---

**编译结束**: 2026-05-29 11:21
**最终状态**: built
