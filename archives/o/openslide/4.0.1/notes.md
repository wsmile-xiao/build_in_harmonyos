# OpenSlide 4.0.1 适配笔记

## 范围

本配方面向 HarmonyOS PC AArch64，使用上游 OpenSlide 4.0.1 官方 tarball 和 Meson 构建系统。

## 依赖决策

上游 `meson.build` 将 zlib、zstd、libjpeg、libpng、openjpeg、libtiff、glib（glib-2.0/gio-2.0/gobject-2.0）、cairo、libxml2、sqlite3、libdicom 全部作为必需依赖；OHOS 上 sqlite3 不是 Windows 例外，因此也为硬依赖。依赖精确版本见 `conanfile.py`。

zlib/zstd/libjpeg-turbo 版本与 libtiff/4.7.2 配方的精确 requires 对齐（libtiff 要求 zlib/1.3.1.1、zstd/1.5.7、libjpeg-turbo/3.2.0），libpng 选择同样要求 zlib/1.3.1.1 的 1.6.58，glib 选择 2.84.0.2（同样要求 zlib/1.3.1.1），避免依赖图版本冲突；libjpeg-turbo 同时满足 openslide 的 jpeg_mem_src（>= 1.3）探测。

构建尝试中验证（依赖图版本冲突链）：
- libtiff/4.7.2 精确要求 zlib/1.3.1.1；libpng/1.6.58.1/.2 与 glib/2.88.x 精确要求 zlib/1.3.2，不能共存。
- 最终组合：zlib/1.3.1.1 + zstd/1.5.7 + libjpeg-turbo/3.2.0 + libpng/1.6.58 + glib/2.84.0.2 + cairo/1.18.4 + libtiff/4.7.2（后四者 zlib 约束全部一致）。

OpenSlide 4.0.1 没有格式级 Meson 开关，JPEG2000、DICOM、XML、SQLite 等解码器无条件编译，不能通过关闭格式来规避依赖。`test` 与 `doc` 仅构建选项，配方中关闭以避免交叉编译测试工具和 Doxygen 依赖。

## Meson/Conan 处理

- `PkgConfigDeps` 将 Conan 依赖注入生成目录，`MesonToolchain.pkg_config_path` 指向该目录。
- openjpeg/2.5.4 的 Conan recipe 默认包名对应 `openjpeg.pc`，上游查找 `libopenjp2`；配方为该依赖设置 `pkg_config_name=libopenjp2`。
- `wrap_mode=nodownload` 防止构建期间联网获取 subproject。
- 注入 OHOS 工具链中的 llvm-ar/llvm-ranlib，避免 Meson 在 PATH 中按裸名称查找失败。
- 未主动修改上游源码；`patches/` 当前无补丁。

## 测试执行

上游开发者测试套件（`test/` 下 6 个可执行程序：extended / mosaic / parallel /
profile / query / try_open）在 `build()` 中全部真实构建并执行，输入为配方用
`make_synthetic_slide.py` 生成的 256x256 tiled generic-TIFF 幻灯片（OpenSlide 的
generic-tiff vendor 要求 TIFF 为 tiled，见 `src/openslide-vendor-generic-tiff.c`）。
任一个程序退出码非 0 则构建失败。

上游 `test/driver.py` 不在执行范围内：它依赖 cjpeg/djpeg/xdelta3 与外部大体积
幻灯片样例语料库（openslide-testdata），离线 CI 不可获取；6 个测试程序本体与
driver.py 无关，故另行用 stub 工具满足上游开发者套件的探测（仅在 meson setup 时
用于通过 `find_program` 检查）。

消费者 test_package 使用程序现场生成的 tiled TIFF 做库 API 冒烟验证，并真实执行
（退出码非 0 即失败，不再把加载器错误静默降级为通过）。

## 打包关键修复：保留链接器产物的代码签名

HarmonyOS 的 clang 驱动会在链接时给每个 ELF 写入 `.codesign` 段（覆盖文件内容），
动态加载器会校验它。meson 在 `install` 阶段会**就地改写**已安装共享库的 rpath
（未设置 install_rpath 时剥离 build rpath），该就地改写会破坏 `.codesign`，导致
加载器拒绝加载：`Error loading shared library libopenslide.so.1: Permission denied`
（退出码 127）。因此 `package()` 在 `meson install` 之后用构建树中链接器产出的
`src/libopenslide.so.1.0.1` 覆盖安装产物（musl 忽略 DT_RUNPATH，残留的 build rpath
在运行期无害），再做共享库别名物化。

## 来源校验

源码 tarball sha256 已由本地计算和 Homebrew formula 双源核对，值为 `df82f6b264f98d11eeb80d85bbb10c7935fcd69c7abae1d610ce49b9a0437faf`。

本机/CI 网络无法直连 github.com（HTTPS 连接超时）。conandata.yml 提交版本仅写官方 GitHub release 原始 URL（R39 官方源要求），GitHub 镜像 fallback 由 CI 的 mirror fallback 机制自动添加，不在配方中手动添加镜像前缀。本地构建验证期间曾临时使用 ghfast.top / gh-proxy.com / ghproxy.net 三个镜像获取源码（三者 sha256 与官方完全一致），验证后已恢复官方原始 URL。
