# poppler 25.12.0.1 OpenHarmony 适配笔记

> **25.12.0.1 是 25.12.0 的构建方式修复版**（R37 后缀递增）。
> 源码 tarball、39 个补丁、功能开关**全部不变**，只改构建方式与打包收尾。

## 本次修了什么

### ① 产物没有 SONAME，导致下游 DT_NEEDED 烤成相对路径

25.12.0 用 conan 的 `CMakeToolchain` / `CMake(self)` 构建。`os=OHOS` 下 conan 会把
`CMAKE_SYSTEM_NAME` 映射成 cmake 不认识的 `HarmonyOS`（ML-0035），cmake 因而不套用
版本化共享库规则——**poppler 自己明明设了 SOVERSION 也白设**：

```cmake
# CMakeLists.txt:635,657   poppler
set(POPPLER_SOVERSION_NUMBER "155")
set_target_properties(poppler PROPERTIES VERSION 155.0.0 SOVERSION 155)
# cpp/CMakeLists.txt:28    poppler-cpp
set_target_properties(poppler-cpp PROPERTIES VERSION 2.2.0 SOVERSION 2)
```

25.12.0 的实际产物（已发布制品实测）：

```
lib/libpoppler.so         无 SONAME、无版本软链
lib/libpoppler-cpp.so     无 SONAME；DT_NEEDED = ../libpoppler.so   ← 相对路径
```

`DT_NEEDED` 一旦带斜杠，加载器就按**进程当前工作目录**解析，基本不可能命中。

**这不是理论推演——已发布制品实测**（`bin/pdfinfo` 加 `LD_LIBRARY_PATH` 直接跑）：

```
Error loading shared library ../libpoppler.so: (needed by .../p/bin/pdfinfo)
Error relocating .../p/bin/pdfinfo: gatof: symbol not found
Error relocating .../p/bin/pdfinfo: _ZN12GlobalParamsC1ERKNSt4__n112basic_string... symbol not found
```

即 25.12.0 的 **11 个 CLI 工具全部不可用**，`libpoppler-cpp.so` 同理。
注意 `LD_LIBRARY_PATH` 在此救不了场——它只影响**按纯 soname 查找**的情形；
`DT_NEEDED` 里带斜杠时加载器走的是路径解析分支，直接绕过搜索路径。

**修法**：改用本仓已验证的「自发现 SDK `ohos.toolchain` + 裸 cmake」路子
（glfw / libjpeg-turbo / zstd / opencv 同法），绕开 conan_toolchain。

### ② 补上 ELF 代码签名（配合新构建方式的预防性措施）

25.12.0 的 `package()` 只调 `cmake.install()`，**没有任何签名步骤**。

> **据实说明**：25.12.0 的产物实测**带 `.codesign` 段且能被 exec**——上面 `bin/pdfinfo`
> 那次失败发生在符号重定位阶段，是缺陷①造成的，**不是签名问题**。所以本项不是在修一个
> 已复现的故障。

之所以仍要补：25.12.0.1 改走 **SDK `ohos.toolchain`** 路线，而本仓实测该路线产出的 ELF
**自签无效**（dlopen 报 `Permission denied`），与 25.12.0 走的 conan CMakeToolchain +
hnp-clang 直链不同；且 `cmake install` 是复制、不重链，本就会破坏链接器自签。
本包 `bin/` 下有 **11 个 CLI 工具**（pdftotext / pdftoppm / pdfinfo / pdfimages /
pdftohtml / pdftops / pdffonts / pdfattach / pdfdetach / pdfseparate / pdfunite），
按仓内既有约定（glfw / libjpeg-turbo / zstd / opencv 等同法）必须重签。

**修法**：`package()` 末尾调 `_sign_binaries()`，对 `lib/**/*.so*` 与 `bin/` 下的
真实 ELF 逐个 `llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign -selfSign 1`
（跳过软链，避免对同一目标重复签）。

### ③ SDK 缺 `llvm-ranlib`

`ohos.toolchain` 把 `CMAKE_RANLIB` 指向 `<SDK>/llvm/bin/llvm-ranlib`，而该目录下
**只有 `llvm-ar`**。造静态库的规则是 `<AR> qc … && <RANLIB> …`，AR 成功、RANLIB 一步
ENOENT，报错为 `Error running link command: no such file or directory`（不提是哪个程序）。
显式 `-DCMAKE_RANLIB=/data/service/hnp/bin/llvm-ranlib`（该软链指向 `llvm-ar`，
LLVM 工具按 `argv[0]` 改行为）。

### ④ test_package 是空壳，且把运行期失败吞掉了

25.12.0 的 `test.cpp` 只打印头文件里的 `POPPLER_VERSION` 宏，**一个库函数都没调**——
把 `lib/` 整个删掉也照样通过，过不了 R34 与 CI 的 L1e 破坏性反向验证。

更要紧的是 `test()` 用 `try/except` 把运行错误降级成 warning，理由写的是
「OHOS musl 不支持 RPATH/LD_LIBRARY_PATH」——**该说法不成立**（同仓 opencv/ffmpeg 等
配方的 test_package 都以 `env="conanrun"` 正常跑起来）。**正因为运行期失败被吞掉，
上面①②两个缺陷才一直没被发现。**

**修法**：test.cpp 改为真实调用 poppler-cpp API——运行时现造一份合法单页 PDF
（xref 字节偏移动态计算、不写死），经 `document::load_from_file` 与 `load_from_data`
两条入口解析，校验页数/加密状态/页面尺寸，并抽取页面文本核对内容，共 8 条断言。
`test()` 不再 catch，运行失败即判失败。

## 修复前后实测对比（真机）

| 项 | 25.12.0（已发布） | 25.12.0.1 |
|---|---|---|
| `libpoppler.so` SONAME | 无 | `libpoppler.so.155` |
| `libpoppler-cpp.so` SONAME | 无 | `libpoppler-cpp.so.2` |
| 版本软链 | 无 | `libpoppler.so → .so.155 → .so.155.0.0` |
| `libpoppler-cpp` 的 `DT_NEEDED` | `../libpoppler.so`（相对路径） | `libpoppler.so.155`（纯 soname） |
| `bin/pdfinfo -v` | `Error loading shared library` + 符号缺失 | `pdfinfo version 25.12.0` |
| `bin/pdftotext -v` / `pdftoppm -v` | 同上 | 均正常输出版本 |
| test_package | 2 条（仅打印头文件宏） | **8 条真实 API 断言，全过** |

`conan create -pr ohos-native` rc=0，用时 61s。

## 依赖接线

裸 cmake 不吃 CMakeDeps，且交叉 toolchain 在文件里 `set(CMAKE_FIND_ROOT_PATH_MODE_* ONLY)`
会覆盖命令行的 BOTH，`find_package(Freetype/ZLIB)` 搜不到 conan 依赖。
本配方直接预设各 Find 模块的**结果缓存变量**（poppler 用的是 imported target
`Freetype::Freetype` / `ZLIB::ZLIB`，这些 target 正是由下列变量生成的）：

```
-DFREETYPE_LIBRARY=<freetype>/lib/libfreetype.so
-DFREETYPE_INCLUDE_DIR_ft2build=<freetype>/include/freetype2
-DFREETYPE_INCLUDE_DIR_freetype2=<freetype>/include/freetype2
-DZLIB_LIBRARY=<zlib>/lib/libz.a          # 按 R26 是静态，内链
-DZLIB_INCLUDE_DIR=<zlib>/include
```

依赖库文件名按 `.so`→`.a` 顺序自动探测，不硬编码后缀。

## 注意：不要覆盖 C++ 标准

poppler 自己 `set(CMAKE_CXX_STANDARD 23)`（CMakeLists.txt:50），那 39 个补丁正是为补
clang 15 的 C++23 缺口而存在。**本配方刻意不传 `-DCMAKE_CXX_STANDARD`**，覆盖它会让补丁
失去前提。conan profile 里的 `compiler.cppstd=17` 只参与 package_id 计算，不影响实际编译。

## 已知限制

- 不支持 Qt5/Qt6/GLib 绑定、NSS3 签名校验、libcurl 网络流、LCMS 色彩管理、
  DCT/OpenJPEG 解码器、libtiff 输出（与 25.12.0 一致）
- 字体走 `FONT_CONFIGURATION=generic`，不依赖 fontconfig
- 上游 ctest 需单独 git clone 测试数据（源码包不含），未在 CI 中运行

---

<details>
<summary>25.12.0 原始笔记（存档）</summary>

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


</details>
