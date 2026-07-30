# FreeImage 3.18.0 适配笔记

## 编译环境
- 构建系统: makefile（Makefile.gnu）
- 编译日期: 2026-06-24
- 编译器: clang/clang++ 15.0
- 架构: aarch64
- 状态: published
- 功能测试: ✅ 通过（20/20）

## 编译步骤

```bash
# 1. 加载编译上下文
source .build-context-freeimage-3.18.0

# 2. 使用 Makefile.gnu 构建
cd $BUILD_SRC_DIR
make -f Makefile.gnu -j1

# 3. 安装到暂存区（DESTDIR 模式）
make -f Makefile.gnu install DESTDIR=$TEST_PREFIX PREFIX=$DEFAULT_PREFIX

# 4. 预编译包制作
python3 $SKILL_ROOT/scripts/ohc-run.py package freeimage 3.18.0

# 5. 安装到本地（模拟用户部署）
make -f Makefile.gnu install PREFIX=$DEFAULT_PREFIX
```

## 遇到的问题与解决方案

| 序号 | 问题描述 | 根本原因 | 解决方案 |
|------|---------|---------|---------|
| 1 | 缺少 `install` 命令 | 鸿蒙系统没有 GNU `install` 工具 | 在 Makefile.gnu 中用 `mkdir -p`/`cp`/`chmod` 替代 |
| 2 | PNG ARM NEON 未定义符号 | 内嵌 libPNG 在 aarch64 上自动启用 NEON 优化，但未包含 arm/ 实现目录 | 在 CFLAGS 中添加 `-DPNG_ARM_NEON_OPT=0` 禁用 NEON 优化 |
| 3 | install -o root -g root 失败 | 鸿蒙系统无 root 用户 | 移除安装目标中的用户和组归属参数 |
| 4 | ln -sf 在 HMDFS 上失败 | HMDFS 不支持覆盖式创建符号链接 | 改用 `rm -f && ln -s` 模式创建符号链接 |

## 源码修改

### Makefile.gnu（已追踪，生成补丁 0001-Makefile.gnu.patch）

修改内容：
1. 新增 `PREFIX ?= /usr` 变量，支持可配置安装前缀
2. 将 `INCDIR`/`INSTALLDIR` 改为 `$(DESTDIR)$(PREFIX)/...` 路径模式（兼容 DESTDIR 模式）
3. 将 `install` 命令替换为 `mkdir -p`/`cp`/`chmod`（鸿蒙系统无 `install` 命令）
4. 移除 `-o root -g root` 用户归属参数
5. 将 `ln -sf` 改为 `rm -f && ln -s` 以兼容 HMDFS 文件系统
6. 在 CFLAGS 中添加 `-DPNG_ARM_NEON_OPT=0`（禁用内嵌 libPNG 的 ARM NEON 优化）

## 依赖版本

FreeImage 3.18.0 内嵌所有依赖，无需外部库：
- libJPEG 9a
- libPNG 1.6.24
- libTIFF 4.0.6
- zlib 1.2.8
- OpenJPEG 2.1.0
- OpenEXR 2.2.0
- LibRaw 0.17.2
- LibWebP 0.5.0
- LibJXR 1.0

## 功能验证结果（✅ 全部通过）

在鸿蒙设备上实际运行功能测试程序，覆盖 20 项核心 API 测试：

| 测试类别 | 测试项目 | 结果 |
|---------|---------|------|
| 基础功能 | 库初始化与版本查询 | ✅ |
| 基础功能 | 图像创建与像素绘制 | ✅ |
| 格式读写 | BMP 保存/加载 | ✅ |
| 格式读写 | PNG 保存/加载 | ✅ |
| 格式读写 | JPEG 保存/加载 | ✅ |
| 格式读写 | TIFF 保存/加载 | ✅ |
| 图像处理 | 色彩深度转换（24→32/8 位） | ✅ |
| 图像处理 | 图像缩放（双三次重采样） | ✅ |
| 图像处理 | 图像旋转 90° | ✅ |
| 图像处理 | 水平翻转 | ✅ |
| 图像处理 | 伽马校正 | ✅ |
| 其他 | 调色板操作、多格式批量保存 | ✅ |

**动态链接测试**: 编译成功，运行时正确加载 libfreeimage-3.18.0.so
**静态链接**: 上游已知问题（b44ExpLogTable main 符号冲突），建议使用动态库

测试程序源码: `reports/freeimage_func_test.c`

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| freeimage-3.18.0-ohos-aarch64.tar.gz | 33.8 MB | 预编译包（含动态库 + 静态库 + 头文件） |
| freeimage-3.18.0-ohos-aarch64-debug.tar.gz | 1.2 MB | 调试符号包 |
| 0001-Makefile.gnu.patch | ~1KB | 鸿蒙平台适配补丁 |
| freeimage_func_test.c | ~6KB | 功能测试程序源码 |

## 注意事项

- PNG ARM NEON 优化已禁用（-DPNG_ARM_NEON_OPT=0），回退为 C 实现，安全可靠
- 内嵌库（LibJXR、LibWebP）的编译告警为上游源码原有问题，非致命
- 静态库包含构建工具的 main 函数（b44ExpLogTable），静态链接时需加 `-Wl,--allow-multiple-definition`
- 建议优先使用动态库（libfreeimage-3.18.0.so）
---

**编译结束**: 2026-06-24 12:06
**功能测试**: 2026-06-24 14:55（20/20 通过）
**最终状态**: published

---

# Conan 配方（2026-07-30 新增，与上方预编译包并存）

上方是 **ARCHIVE-SPEC 预编译包**那条线（`make install` + `PREFIX/DESTDIR` + `0001-Makefile.gnu.patch`）。
本节是**同一版本的 conan 配方**（`conanfile.py` + `conandata.yml` + `test_package/`），
两者共存于本目录、互不改动对方产物。

## 与上方笔记的关系

- **确认**了上方「问题 2」：`-DPNG_ARM_NEON_OPT=0` 必需。conan 路径独立复现同一现象，
  且补充了它在**消费侧**的表现：`libfreeimage.so` 自身能链出来（链 .so 默认容忍未定义符号），
  但消费方**直接链接**时 `ld.lld: error: undefined reference due to
  --no-allow-shlib-undefined: png_init_filter_functions_neon`。
  → 纯 dlopen 探针可能漏掉这个缺陷，**直接链接**才暴露。
- **绕开**了上方「问题 1/3/4」（无 `install` 命令、`-o root -g root`、`ln -sf` 在 HMDFS 上失败）：
  conan 配方**不调用上游 `make install`**，改在 `package()` 里手工 `copy` + `os.symlink`，
  故这三条对 conan 路径不适用。**因此 `conandata.yml` 里没有 `patches:` 条目** ——
  `patches/0001-Makefile.gnu.patch` 属预编译包那条线，conan 配方未应用它（不是漏了）。
- **沿用**上方发现：静态库含 `b44ExpLogTable` 的 `main` 符号。本配方同时装 `libfreeimage.a`，
  消费方若静态链接需 `-Wl,--allow-multiple-definition`；`cpp_info.libs = ["freeimage"]`
  默认解析到 `libfreeimage.so`，推荐动态链接。

## conan 路径特有的 5 条适配

1. **`CFLAGS`/`CXXFLAGS` 走环境变量，不能走 make 命令行赋值**
   GNU make 的命令行赋值会压掉 makefile 内同名变量的**一切**赋值（含 `+=`），
   而 `Makefile.gnu:25/29` 正是用 `CFLAGS += $(INCLUDE)` 追加那 20 余项 `-ISource/...`。
   实测传命令行 `CFLAGS` → INCLUDE 整段被废 → 531 个源文件全报
   `fatal error: 'FreeImage.h' file not found`。走 env 则 `?=` 跳过、`+=` 照常追加。

2. **显式 `-std=c++17`**
   profile 声明 `compiler.cppstd=17`，但本配方直接驱动 make、无 toolchain generator 注入 `-std=`，
   clang 15 会退到默认 gnu++14（设备实测 `__cplusplus=201402`）——与 package_id 声明不符，故显式补上。
   补上后 2018 年的老代码触发 3 处 C++17 已移除构造，用**旗标**解决、**零源码补丁**：

   | 构造 | 命中 | 解法 |
   |---|---|---|
   | `register`（55 个文件） | 各自带 codec | `-Wno-register` |
   | `throw(...)` 动态异常规范 | `OpenEXR/Imath/{ImathVec,ImathMatrix}.h` | `-Wno-dynamic-exception-spec` |
   | `std::auto_ptr`（3 个文件） | `LibRawLite/libraw/libraw_datastream.h`、`LibRawLite/src/libraw_datastream.cpp`、`FreeImage/MultiPage.cpp` | `-D_LIBCPP_ENABLE_CXX17_REMOVED_AUTO_PTR` |

3. **`AR` 直接给 hnp 的 `llvm-ar`，不要走 `conf.get("tools.gnu:ar")`**
   `tools.gnu:ar` **不是** Conan 注册过的 conf（2.29.1 实测），`conf.get` 对未注册键直接抛
   `ConanException: ... does not exist in configuration list`，连 default 都不返回。

4. **SONAME 链需手工补齐**
   产物名 `libfreeimage-3.18.0.so`，SONAME 是 `libfreeimage.so.3`（`Makefile.gnu:38/40`），
   两者都不是 `-lfreeimage` 找的 `libfreeimage.so`。`package()` 补齐
   `libfreeimage.so → libfreeimage.so.3 → libfreeimage-3.18.0.so`（用 `os.remove` + `os.symlink`，
   同上方「问题 4」的 HMDFS 规避思路）。

5. **共享库显式重签**
   上游共享库链接行带 `-s`（`Makefile.gnu:70`）—— 链接期 strip 会把链接器自签的 `.codesign` 段一并剥掉。
   `package()` 里 `llvm-objcopy --remove-section .codesign` → `binary-sign-tool sign -selfSign 1`
   → `display-sign` 复验。

> 注：`LIBRARIES` 本配方显式给 `-lc++`。设备实测 `-lstdc++` 与 `-lc++` **都能链接成功**
> （clang 把前者当别名），故这**不是**必需修正，只是让 libc++ 工具链下的意图更明确；
> 上方预编译包保留上游 `-lstdc++` 同样正确。

## 新发现的一条已知限制：JPEG-XR 编码不可用

上方那轮 20 项功能测试覆盖 BMP/PNG/JPEG/TIFF 四种格式；本轮 test_package 把覆盖面扩到
**8 个自带 codec**，因此发现：

**JPEG-XR（LibJXR）编码在 aarch64 上不可用。** 实测矩阵 24/32/8 bpp × 61x37 / 64x32 /
128x128 / 256x256 × `JXR_DEFAULT` / `JXR_LOSSLESS` × 有无可写 `TMPDIR` —— **全部**
`FreeImage_Save` 失败，报 LibJXR 兜底错误 `Invalid instruction - please contact the FreeImage
team`（`PluginJXR.cpp:164` 的 `default:` 分支，对应 `WMP_errFail` / `WMP_errNotInitialized`）。
插件注册正常且自报 `SupportsWriting=1`，故属自带 LibJXR 的移植缺陷，非配置问题；未继续下钻 jxrlib 内部。
test_package 对 JXR 只断言插件注册与读取能力。

**范围限定：只有编码不可用，解码是好的。** 上游 TestAPI 套件里的 `testMemIO("exif.jxr")`
（真实读入一个带 EXIF 的 .jxr）在本包上通过，故 JXR **读取路径可用**。

## 两条**入参**约束（不是平台缺陷，但用库/写测试会撞）

- **JPEG2000 最小边 ≥ 64**：OpenJPEG 默认 6 层分辨率，小于此报
  `Error: Number of resolutions is too high in comparison to the size of tiles`。
  实测 61x37 / 64x32 编码失败，64x64 起正常（默认参数下往返偏差 0）。
- **JPEG 有损程度依图案**：高频棋盘图经 `JPEG_QUALITYSUPERB | JPEG_SUBSAMPLING_444` 偏差 25，
  平滑渐变仅偏差 3。属编码器固有行为，写测试要用平滑图 + 合理容差。

## 另两条本轮发现

### `-DNDEBUG` 必须自己补（settings.build_type=Release 的语义）

上游 `Makefile.gnu` 只给 `-O3`、**不带 `-DNDEBUG`**，而本 recipe 直接驱动 make、
没有 toolchain generator 替我们加 → 不补就会构出「带 assert 的 Release」。
实测后果：跑上游 TestAPI 套件读 `exif.jxr` 时触发
`Assertion failed: FALSE (Source/FreeImage/PluginJXR.cpp: ReadPropVariant: 493)` 直接 abort。
那行是 switch 的 `default:` 分支（上游注释 "This case is not handled"，某种 JXR EXIF 变体
类型上游未处理），属**平台无关**的上游既有缺口，Release 下 assert 本应编译掉。
补 `-DNDEBUG` 后上游套件退出码 0。

### 上游自带测试套件已接入 `build()`

`TestAPI/`（13 个 `.cpp`，`MainTestSuite.cpp` 驱动 38 次断言调用）。上游
`TestAPI/Makefile` 写死 `g++ -I../Dist/ *.cpp ../Dist/libfreeimage.a`，OHOS 上要三处调整，
故照其编译行用 clang++ 复现而非直接 `make`：① `g++` → `clang++`；② 补同 `CXXFLAGS` 的
C++17 逃生旗标；③ 加 `-Wl,--allow-multiple-definition`（静态库含构建工具 `b44ExpLogTable`
的 `main`，静态链接会撞符号——即上方预编译包一节已记录的上游既有问题）。
**未改上游任何一行测试代码**，仅改编译命令。真机结果：退出码 0，38 次调用全过。

## conan 路径真机验证

设备 HarmonyOS PC 2in1，Conan 2.29.1，`conan create . -pr:h ohos -pr:b ohos_build --build='freeimage/*'`
（profile settings 与 CI 的 `ohos-aarch64` 逐项一致：`os=OHOS/6.0`、`armv8`、`clang 15`、
`libc++`、`cppstd=17`、`Release` → package_id 相同）：

- `conan create` **rc=0**，编译约 4 分钟（远低于 CI 45 分钟硬超时）
- **上游 TestAPI 套件在 build() 内编译并运行，退出码 0**（38 次断言调用全过）
- test_package **13 条断言全过**（补上游未覆盖的编解码往返）：BMP / PNG(LibPNG+ZLib) / TIFF(LibTIFF4) / WebP(LibWebP)
  无损逐像素全等；JPEG(LibJPEG) / JP2 与 J2K(LibOpenJPEG) 带容差；OpenEXR 走 `FIT_RGBF`
  浮点无损往返；LibJXR / LibRawLite 断言插件注册与读取；另验版本号、插件数、
  TIFF+Deflate 压缩路径、文件格式嗅探
- 产物审计：`libfreeimage-3.18.0.so` 6.75 MB + `libfreeimage.a` 11.99 MB + `FreeImage.h`；
  软链 `.so` / `.so.3` 齐备；SONAME `libfreeimage.so.3`；
  DT_NEEDED 仅 `libc++_shared.so` + `libc.so`（自包含）；
  `.codesign` 段在，`display-sign` → `code signature is self-sign`；导出 598 个 FUNC
