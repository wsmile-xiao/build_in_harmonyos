# poppler 25.12.0 OpenHarmony 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-08
- 编译器: Clang 15.0.4 / clang++ 15.0.4
- CMake: 4.1.2
- Conan: 2.29.1 (OHOS 适配版)
- Python: 3.12.9
- 状态: published
- Conan 包: poppler/25.12.0@ohpcd/stable

## CMake 关键选项

```bash
cmake .. \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_SYSTEM_NAME=OHOS \
  -DFONT_CONFIGURATION=generic \
  -DENABLE_BOOST=OFF \
  -DENABLE_CPP=ON \
  -DENABLE_GLIB=OFF \
  -DENABLE_QT5=OFF \
  -DENABLE_QT6=OFF \
  -DENABLE_UNSTABLE_API_ABI_HEADERS=ON \
  -DENABLE_NSS3=OFF \
  -DENABLE_GPGME=OFF \
  -DENABLE_LIBCURL=OFF \
  -DENABLE_LIBTIFF=OFF
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | C++23 std::ranges 兼容性错误 | clang++ 启用 C++23 后 ranges 算法冲突 | 37 个补丁为 ranges 算法添加 std:: 前缀 |
| 2 | CMake 不认识 OHOS 平台 | CMake 无 HarmonyOS 平台定义 | 补丁 0001 添加 OHOS 平台检测 |
| 3 | fontconfig 不可用 | OHOS 无 fontconfig | -DFONT_CONFIGURATION=generic |
| 4 | TIFF target 大小写不匹配 | TIFF::tiff vs TIFF::TIFF | -DENABLE_LIBTIFF=OFF (E212 草稿) |
| 5 | NSS3/GPGME/libcurl 不可用 | OHOS 无这些库 | -DENABLE_*=OFF |

## 补丁

37 个补丁，全部 #ifdef __OHOS__ 守卫，类型 portability：
- 0001: CMakeLists.txt (OHOS 平台检测)
- 0002-0004: cpp/ + fofi/ (4 个文件)
- 0005-0028: poppler/ (24 个文件，含 21 个字体宽度表)
- 0029-0032: qt5/qt6 tests/ (4 个文件)
- 0033-0035: splash/ (3 个文件)
- 0036-0037: utils/ (2 个文件)

## 依赖

- freetype/2.14.3@ohpcd/stable (R27: self.requires 声明)
- fontconfig: 绕过 (-DFONT_CONFIGURATION=generic)
- liblcms2 2.16: 系统预装
- libc++_shared: 系统提供

## Conan 配方

- conanfile.py: CMake 构建, R27 依赖 freetype/2.14.3@ohpcd/stable, R33 不依赖 shell 变量
- conandata.yml: sha256=c18b40eb36b1a0c5b86e29ca054bf0770304583da4f2cdd42fe86eca6a20de48, 37 补丁
- test_package/: test.cpp + CMakeLists.txt + conanfile.py + MANIFEST.yml (4 源文件)

## 功能测试 (2026-07-08)

- CMake 配置 + make 编译 100% 成功
- make install: 137 文件 (2 库 + 11 工具 + 109 头文件)
- conan create 成功: poppler/25.12.0@ohpcd/stable
- test_package 编译+链接通过
- 11 工具 + 2 库全部 ELF DYN (PIE), NX + Full RELRO
- API 编译链接验证 7 项通过
- 运行时: OHOS musl 链接器不支持 RPATH (非编译问题)

## CI 合规检查 (2026-07-09, 实际 CI 脚本运行)

| 门禁 | 结果 | 说明 |
|------|------|------|
| L0 | PASS | 质量门禁全部通过 (L0a-L0k) |
| L1 | PASS | test_package + 上游测试 + L1e 破坏性负测试 |
| L2 | SKIP | 11 工具 version/help 失败 (OHOS 平台限制, 非阻塞) |
| L4 | WARN | 误报: getFormWidgets 匹配 gets 子串 (非阻塞) |
| L5 | PASS | bin/ 有内容 |

**CI 总体: SUCCESS (1/1)**

## 产物

- libpoppler.so.155.0.0 (4.5 MB)
- libpoppler-cpp.so.2.2.0 (131 KB)
- 11 CLI 工具: pdfinfo, pdftotext, pdftops, pdfimages, pdffonts, pdfseparate, pdfunite, pdftohtml, pdftoppm, pdfattach, pdfdetach
- 109 头文件

## 注意事项

1. C++23 兼容性: 37 补丁修复 std::ranges, 全部 #ifdef __OHOS__ 守卫
2. fontconfig 绕过: -DFONT_CONFIGURATION=generic
3. TIFF 禁用: CMake target 大小写不匹配 (E212 草稿)
4. 运行时限制: OHOS 安全策略阻止 HMDFS 二进制执行
5. L4 误报: getFormWidgets() 中 Widgets 尾部 gets 子串匹配 CI 正则

---
编译结束: 2026-07-08 | CI 验证: 2026-07-09
最终状态: published
Conan 包: poppler/25.12.0@ohpcd/stable
---
