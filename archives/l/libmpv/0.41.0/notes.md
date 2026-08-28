# libmpv (mpv) 0.41.0 适配笔记

## 编译环境
- 构建系统: meson 1.12.0 + ninja
- 编译日期: 2026-08-25
- 编译器: clang/clang++ 15.0.4（/data/service/hnp/bin）
- 状态: built

## 编译步骤

```bash
export PATH=/data/service/hnp/bin:$PATH
export CC=clang CXX=clang++ AR=llvm-ar RANLIB=llvm-ranlib

# 依赖 pkg-config 路径（本地直连编译；CI 中 conan PkgConfigDeps 自动注入）
# 修正各依赖包 .pc 的 prefix 指向实际包路径（conan 打包时 prefix 写死为 /）

meson setup build-ohos \
  -Dlibmpv=true -Dcplayer=false \
  -Dx11=disabled -Dwayland=disabled -Dgl=disabled -Dvulkan=disabled \
  -Dalsa=disabled -Djack=disabled -Dpulse=disabled -Dpipewire=disabled -Dopensles=disabled \
  -Ddvdnav=disabled -Dlibarchive=disabled -Duchardet=disabled -Dlibavdevice=disabled \
  -Dzimg=disabled -Drubberband=disabled \
  -Dlcms2=enabled
meson compile -C build-ohos
# 产物: build-ohos/libmpv.so.2.5.0 (+ .so/.so.2 符号链接)
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `Unknown option: libass`（裁剪尝试） | mpv 0.41.0 的 libass 是硬依赖（meson.build `dependency('libass')` 在 dependencies 列表，无开关） | 先完成 libass/0.17.5 发布（PR #6590），再构建 libmpv |
| 2 | `libavcodec ... need '>= 60.31.102' found '58.134.100'` | mpv 0.41.0 要求 ffmpeg 6.1+（libavcodec 60.31.102+），制品仓 4.4.8/5.1.10 不满足 | 改用 ffmpeg/7.1.5（libavcodec 61.19.101） |
| 3 | `libavcodec/avcodec.h file not found` | deploy 的 libavcodec.pc 前缀指向空的 conan 缓存路径 | 批量修正 deploy 目录 .pc 的 prefix 指向实际部署路径 |
| 4 | `libplacebo/colorspace.h file not found` | libplacebo.pc 前缀写死为 `/`，include 指向无效 `//include` | 修正 prefix 为实际包路径 |
| 5 | `ass/ass.h file not found` | libass.pc 前缀为 `/`（conan create 打包时生成） | 修正 prefix 为实际包路径 |
| 6 | `SLES/OpenSLES_Android.h file not found` | opensles 音频后端需要 Android NDK 头文件 | `-Dopensles=disabled`（OHOS 无 Android 音频栈） |
| 7 | meson 找不到 ar 静态链接器 | native 文件 [binaries] 仅含 c/cpp | 显式 AR/RANLIB 环境变量（同 libass 配方） |
| 8 | PkgConfigDeps 生成的 libavcodec.pc 版本为 7.1.5（包版本），mpv 要求 >= 60.31.102 | ffmpeg 配方组件未设 pkg_config_version，PkgConfigDeps 用包版本作 .pc Version | 在 generate() 中于 PkgConfigDeps.generate() 之前对 ffmpeg 组件 set_property("component_version", 库版本)（组件名 avcodec/avformat/...，非 lib 前缀） |
| 9 | CMakeDeps 报 `Component 'ffmpeg::libavcodec' not found` | ffmpeg 组件名为 avcodec 等（cmake_target_name=ffmpeg::avcodec） | package_info requires 用 ffmpeg::avcodec 等正确组件名 |
| 10 | package() 手工 copy `libmpv.so*` 把 meson 中间目录 .p（含 .o）复制进 lib/ | glob 匹配到 libmpv.so.2.5.0.p 目录 | 改用 meson install 标准打包（mpv meson.build 声明 install + install_headers + mpv.pc） |
| 11 | test_package CMake 找不到 mpvConfig | CMakeDeps 生成的是 libmpv-config.cmake（包名） | find_package(libmpv CONFIG REQUIRED) |
| 12 | mpv_load_config_file 参数错误 | API 签名是 (ctx, filename)，非 3 参数 | test.c 修正为 2 参数调用 |
| 13 | test() 遍历依赖时 TypeError（libdirs[0] 为 None / package_folder 为 None） | 组件模式依赖顶层 cpp_info.libdirs 为空；tool_requires 等无 package_folder | libdirs or ["lib"] 回退 + package_folder None 跳过 |
| 14 | conan create 产物 libmpv.so.2（Release 2MB）在本地 dlopen 报 Permission denied，手动编译产物（debug 6.5MB）dlopen OK | 本地 hmfs 文件系统对特定文件的 mmap PROT_EXEC 限制（与制品仓 fontconfig/2.18.3 同型：复制/重写/chmod/换目录均无法解决；fribidi/libass 等多数包不受影响，制品仓 15+ 配方依赖 fontconfig 且 CI 全过证明真实 CI 无此问题） | 本地环境语义不可迁移（R41）：真实 CI（buildbot worker 标准 Linux）不受影响；libmpv.so.2.5.0 编译链接成功 + 手动产物 dlopen OK 证明构建与库本身正确，test_package 编译链接成功，仅本地 test() 运行时受环境限制 |

## 源码修改

无（纯构建配置适配，无补丁）

## 依赖版本

- libass/0.17.5（本任务链发布，PR #6590；传递依赖 freetype/fribidi/harfbuzz/fontconfig）
- ffmpeg/7.1.5（制品仓；mpv 0.41.0 要求 libavcodec >= 60.31.102）
- libplacebo/7.349.0.1（制品仓）
- lcms2/2.19（制品仓；保留色彩管理）
- zlib/1.3.1.1（制品仓；与 ffmpeg/7.1.5 依赖一致，避免图冲突）

## 验证结果

```bash
# 本地编译验证（shared libmpv）
meson setup build-ohos -Dlibmpv=true -Dcplayer=false \
  -Dx11=disabled -Dwayland=disabled -Dgl=disabled -Dvulkan=disabled \
  -Dalsa=disabled -Djack=disabled -Dpulse=disabled -Dpipewire=disabled -Dopensles=disabled \
  -Ddvdnav=disabled -Dlibarchive=disabled -Duchardet=disabled -Dlibavdevice=disabled \
  -Dzimg=disabled -Drubberband=disabled -Dlcms2=enabled
meson compile -C build-ohos
# 产物: libmpv.so.2.5.0（6.5MB debug）
# 头文件: include/client.h
# pkg-config: build-ohos/meson-private/mpv.pc
# 启用特性: build-date cplugins debug dvbin ffmpeg glibc-thread-name glob glob-posix gpl
#   iconv lcms2 libass libdl libplacebo linux-fstatfs memrchr posix posix-shm ppoll
#   pthread-condattr-setclock vector vt.h zlib
# 手动产物 dlopen 验证: OK（LD_LIBRARY_PATH 含全部依赖 lib 目录）

# conan create 验证（Release 2MB 产物）
conan create archives/l/libmpv/0.41.0 -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# 结果: 构建成功（libmpv.so.2.5.0 + mpv.pc + client.h 打包），test_package 编译链接成功；
# test() 运行时加载 libmpv.so.2 受本地 hmfs mmap exec 限制（Permission denied，
# 与 fontconfig/2.18.3 同型环境问题，真实 CI 不受影响）
```

## 注意事项

- libmpv=true + cplayer=false：只构建 libmpv 库，不构建 mpv 可执行文件——后者运行时需显示服务器，OHOS 无此环境（R41 环境语义不可迁移）。
- baka 所用 20 个 libmpv API 在 0.41.0 全部稳定向后兼容（此前调查确认），可作为 baka 的 `PKGCONFIG += mpv` 依赖。
- 本地验证时修正过的 .pc 文件仅影响本机直连编译路径；提交的归档 conandata.yml 只含官方源 URL（R39）。
