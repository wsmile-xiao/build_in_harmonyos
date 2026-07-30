# opencv 4.12.0 编译笔记（HarmonyOS PC · conan / cmake）

## 定位

OpenCV 4.12.0 计算机视觉库，产出 15 个动态 `libopencv_*.so`，供 conan 工程
`find_package(OpenCV)` 消费，或部署到 `~/usr/local` 供裸程序链接。

**上游完全没有鸿蒙支持**：`platforms/` 下只有 android/apple/ios/js/linux/wince/winrt，
全树 grep 不到任何 `OHOS`/`HarmonyOS` 分支。本配方**不改一行上游源码**（`patches: {}`），
适配全部靠 SDK 的 `ohos.toolchain.cmake` + 构建参数完成。

## 依赖策略

制品仓已有的一律走 conan，缺的用 OpenCV 自带 `3rdparty/` 静态编入：

| 能力 | 来源 | 版本 |
|---|---|---|
| zlib | conan（静态，R26） | 1.3.1.1 |
| JPEG | conan | libjpeg-turbo/3.2.0 |
| PNG | conan | libpng/1.6.58 |
| WebP | conan | libwebp/1.6.0 |
| JPEG 2000 | conan | openjpeg/2.5.4 |
| 线性代数加速 | conan（头文件库） | eigen/3.4.0 |
| **视频读写** | conan | **ffmpeg/7.1.5** |
| TIFF | 自带 3rdparty 静态编入 | 4.6.0（制品仓暂无 libtiff） |
| protobuf（dnn 用） | 自带 3rdparty 静态编入 | 3.19.1（制品仓暂无） |
| ADE（gapi 用） | conandata 声明、下载后喂进 OpenCV 下载缓存 | 0.1.2e |
| OpenEXR / Jasper / AVIF / JPEG XL | **关闭** | 制品仓无，且非必需 |

依赖图无版本冲突：ffmpeg/7.1.5 与 libpng/1.6.58 都依赖 zlib/1.3.1.1，与本配方一致。

## 关键适配（四个真实缺陷，都不是「照套路配」能避开的）

### ① SDK 缺 `llvm-ranlib`，导致所有静态库归档失败

`ohos.toolchain.cmake` 把 `CMAKE_RANLIB` 指向 `<SDK>/llvm/bin/llvm-ranlib`，
但**该 SDK 的 `llvm/bin/` 下只有 `llvm-ar`，根本没有 `llvm-ranlib`**。

cmake 造静态库的规则是 `<AR> qc <lib> <objs> && <RANLIB> <lib>`，于是 AR 成功、RANLIB 一步
ENOENT，现象是「`.o` 全编得动、一造 `.a` 就挂」，报错文本还完全不提是哪个程序找不到：

```
Error running link command: no such file or directory
make[2]: *** [3rdparty/quirc/CMakeFiles/quirc.dir/build.make:133: 3rdparty/lib/libquirc.a] Error 2
```

`libquirc.a` / `liblibtiff.a` / `liblibprotobuf.a` 全挂在这。
**修法**：显式 `-DCMAKE_RANLIB=/data/service/hnp/bin/llvm-ranlib`——hnp 下那个是指向 `llvm-ar`
的软链（LLVM 工具按 `argv[0]` 改行为），文件真实存在。

### ② OpenCV 在交叉编译时会**自己禁掉 pkg-config**

顶层 `CMakeLists.txt:704`：

```cmake
if(CMAKE_CROSSCOMPILING AND NOT DEFINED ENV{PKG_CONFIG_LIBDIR}
    AND NOT DEFINED ENV{PKG_CONFIG_SYSROOT_DIR} AND NOT OPENCV_ENABLE_PKG_CONFIG)
  # 根本不调 find_package(PkgConfig)
```

只给 `PKG_CONFIG_PATH` **不满足任何一条豁免**，于是 `ocv_check_modules(FFMPEG …)` 一次都不跑，
FFMPEG 直接判 NO。**修法**：给 `PKG_CONFIG_LIBDIR`（而非只给 `PKG_CONFIG_PATH`）+
`-DOPENCV_ENABLE_PKG_CONFIG=ON`。用 `PKG_CONFIG_LIBDIR` 还有个额外好处：它**替换**默认搜索
路径（`PKG_CONFIG_PATH` 只是前置），把 pkg-config 锁死在 conan 生成目录内，杜绝捞到设备
`~/usr/local` 下的同名 `.pc`。

### ③ conan 生成的 `.pc` 版本号会让 OpenCV 判定 ffmpeg 过旧

解禁 pkg-config 后出现自相矛盾的摘要——四个库全 YES、总判仍 NO：

```
--     FFMPEG:                      NO
--       avcodec:                   YES (7.1.5)
--       avformat:                  YES (7.1.5)
--       avutil:                    YES (7.1.5)
--       swscale:                   YES (7.1.5)
```

真因：conan 的 `PkgConfigDeps` 给每个 `.pc` 写的 `Version` 是 **conan 包版本 `7.1.5`**，
而 `detect_ffmpeg.cmake` 比的是 libav* 的 **ABI 版本**下限（libavcodec ≥ 54.35.0、
libavutil ≥ 52.3.0 …）。`7.1.5 VERSION_LESS 54.35.0` 成立 → `HAVE_FFMPEG` 被重新置 FALSE。

**修法**：用 ffmpeg 包**自带**的 `.pc` 覆盖 conan 生成的同名文件（自带的 `Version` 是真实 ABI
版本），只把 `prefix=` 一行改指本机实际包目录。修复后摘要变为 `FFMPEG: YES` /
`avcodec: YES (61.19.101)`。
顺带解决另一个噪声：自带 `.pc` 把编解码库放在 `Libs.private`，非静态模式下 pkg-config 不展开，
`ocv_check_modules` 便不再对 `openh264`/`vpx`/`opus` 逐个 `find_library` 而刷
`can't find library` 警告。

### ④ G-API 依赖的 ADE 拉不到就**静默跳过整个模块**

`modules/gapi/CMakeLists.txt`：`if(NOT TARGET ade) → ocv_module_disable(gapi)`。
ADE 由配置期的 `ocv_download` 从 github 拉取，拉不动时 gapi
**既不出现在 `To be built` 也不出现在 `Disabled` 里**，极易被忽略。

**修法**：在 `conandata.yml` 声明 ade（带 sha256，CI 对 github.com 有镜像 fallback），
`source()` 里下载后放进 OpenCV 自己的下载缓存
`<源码>/.cache/ade/<md5>-v0.1.2e.zip`（路径约定见 `cmake/OpenCVDownload.cmake:190`，
ID 会转小写）。`filename`/`md5` 必须与 `DownloadADE.cmake` 里写死的一致，否则命不中。

### ⑤ JPEG 2000 的编码器只支持写文件，不支持 `imencode`

openjpeg 接得好好的（摘要 `Found system OpenJPEG: openjp2 (2.5.4)`、
`JPEG 2000: OpenJPEG (ver 2.5.4)`，`grfmt_jpeg2000_openjpeg.cpp` 也编进去了），但
`cv::imencode(".jp2", …)` 必然失败：

```
grfmt_jpeg2000_openjpeg.cpp:790: error: (-213:The function/feature is not implemented)
OpenJPEG2000: Can not create stream in function 'write'
```

原因是 OpenCV 该编码器用 `opj_stream_create_default_file_stream()` 建流——**只接受文件路径**；
走 `imencode` 的内存缓冲时文件名为空，建流直接失败。**这是上游实现限制，与鸿蒙适配无关**
（同版本 OpenCV 在任何平台都如此）。

因此 test_package 对 JP2 改用 `imwrite`→`imread` 的**文件往返**验证。消费方若要 JPEG 2000，
同样只能用 `imwrite`/`imread`，不能用 `imencode`/`imdecode`。

### 另：依赖走 find_package 的接线

交叉 toolchain 在文件里 `set(CMAKE_FIND_ROOT_PATH_MODE_{LIBRARY,INCLUDE} ONLY)`，会**覆盖**
命令行的 `-D…=BOTH`，`find_package(ZLIB/JPEG/PNG/…)` 搜不到 conan 依赖。
本配方直接预设各 Find 模块的**结果缓存变量**（`ZLIB_LIBRARY`/`JPEG_INCLUDE_DIR`/
`PNG_PNG_INCLUDE_DIR`/`WEBP_LIBRARY`/`OpenJPEG_DIR` …）绕过搜索。

可行的前提是：OpenCV 的 `ocv_clear_internal_cache_vars` **只清 `TYPE=INTERNAL` 的缓存项**，
而命令行 `-D` 建的是 `UNINITIALIZED`，不会被清掉。

依赖库文件名按 `.so`→`.a` 顺序自动探测（`_dep_lib()`），不硬编码后缀——制品仓里 zlib 按 R26
是静态、libjpeg/png/webp 是动态，写死会随依赖形态变化而断。

## 已知限制

- **highgui 为 headless**：目标平台无 X11/GTK/Qt/Wayland，`WITH_GTK/QT/WAYLAND/OPENGL=OFF`，
  `cv::imshow` 等开窗 API 不可用（R40 允许的合法「仅构建」形态）。图像/视频读写与全部算法
  模块不受影响。
- **未编入**：CUDA/VTK/IPP(x86 专有)/Halide/OpenVINO/GStreamer/V4L/摄像头 SDK 系
  （目标平台不存在或不适用）、OpenEXR/Jasper/AVIF/JPEG XL（制品仓无对应 conan 包）、
  LAPACK（制品仓无；core 自带实现足够）、TBB/OpenMP（并行走 pthreads）。
- **不产语言绑定**：Python/Java/JS 绑定与 tests/perf_tests/apps/samples 全部关闭。
- `WITH_FFMPEG=ON` 后产物**不再自包含**：`libopencv_videoio.so` 会 `DT_NEEDED` ffmpeg 的
  `libav*`，消费方须部署整个依赖图（`usr_local` deployer 会自动展开）。

## 验证

test_package **直接编译链接**（非 dlopen）OpenCV 公共头与 `libopencv_*.so`，做 14 项真实功能
调用，每个接进来的依赖都有对应的功能证据：

- imgproc：GaussianBlur / cvtColor，校验像素确实被改变
- imgcodecs：PNG / JPEG / WebP / TIFF / JP2 各做 encode→decode 往返并比对像素差
  —— 逐个坐实 libpng / libjpeg-turbo / libwebp / 自带 libtiff / openjpeg
- videoio：`VideoWriter` 写出 MJPG/AVI 再 `VideoCapture` 读回并核对帧尺寸 —— 坐实 ffmpeg 后端
- dnn：`blobFromImage` 产出 NCHW blob（该模块链接 vendored protobuf）
- features2d：ORB `detectAndCompute`；calib3d：`findHomography` 反解已知变换并校验矩阵元素
- gapi：`GComputation` 编译并执行一条 blur 图

编解码器缺失时 OpenCV 抛 `cv::Exception` 而非返回 false，测试逐段捕获，避免一个格式没编进去
就中断整轮、丢掉其余断言。

## 状态

built（真机 `conan create -pr ohos-native` + test_package 全绿）
