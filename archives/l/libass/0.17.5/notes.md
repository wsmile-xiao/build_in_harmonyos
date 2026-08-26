# libass 0.17.5 适配笔记

## 编译环境
- 构建系统: meson 1.12.0 + ninja
- 编译日期: 2026-08-25
- 编译器: clang/clang++ 15.0.4（/data/service/hnp/bin）
- 状态: built

## 编译步骤

```bash
export PATH=/data/service/hnp/bin:$PATH
export CC=clang CXX=clang++ AR=llvm-ar RANLIB=llvm-ranlib

# 依赖 .pc 修正（本机 conan 包 prefix 写死为 /，需指向实际包路径）
# CI 中 conan 依赖机制自动注入，无需此步

meson setup build-ohos \
  -Ddefault_library=shared \
  -Dlibunibreak=disabled -Dcoretext=disabled -Ddirectwrite=disabled
meson compile -C build-ohos
# 产物: build-ohos/libass/libass.so.9.4.2 (+ .so/.so.9 符号链接)
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游默认构建 static 库 | meson.build `default_options: default_library=static` | `-Ddefault_library=shared`（mpv 需共享库链接） |
| 2 | `fatal error: 'fribidi.h' file not found` | 本机 conan 包 .pc 的 `prefix=/` 写死，pkg-config 输出 `-I//include/...` 指向系统根 | 修正 .pc 的 prefix/exec_prefix 为实际包路径（本地验证用；CI 的 conan 依赖机制不受影响） |
| 3 | `Dependency "freetype2" not found` | PKG_CONFIG_PATH 未包含 conan 包 pkgconfig 目录 | 组装各依赖包 lib/pkgconfig 到 PKG_CONFIG_PATH |
| 4 | `Package 'expat'/'libxml-2.0' required by 'fontconfig', not found` | fontconfig 传递依赖 expat/libxml2 | 下载 expat/2.8.2.1.1、libxml2/2.15.3 二进制包并加入路径 |
| 5 | `-L//lib -lfreetype` 链接失败（shared） | .pc 中 exec_prefix=/ 残留，libdir 展开为 //lib | 修正 exec_prefix=${prefix} 后重新 meson setup |
| 6 | `At least one of DirectWrite/CoreText/Fontconfig required` | libass 强制字体提供者 | OHOS 选 Fontconfig（fontconfig/2.18.3 已发布），无需 require-system-font-provider=false |

## 源码修改

无（纯构建配置适配，无补丁）

## 依赖版本

- freetype/2.14.3（制品仓）
- fribidi/1.0.16（制品仓）
- harfbuzz/14.2.0（制品仓）
- fontconfig/2.18.1.1（制品仓；传递依赖 expat/libxml2/zlib 自动解析；**不用 2.18.3**——本地验证其 libfontconfig.so.1 无法加载（Permission denied），与 cairo/cairomm 已合入配方注释记录的 2.18.1 二进制损坏先例同源，该例用 2.18.1.1 override 解决）

## 验证结果

```bash
# 本地编译验证（shared）
meson setup build-ohos -Ddefault_library=shared -Dlibunibreak=disabled \
  -Dcoretext=disabled -Ddirectwrite=disabled
meson compile -C build-ohos
# 产物: libass.so.9.4.2（805KB）
# 头文件: libass/ass.h
# pkg-config: build-ohos/meson-private/libass.pc
```

## 注意事项

- libass 是 mpv（libmpv）的字幕渲染硬依赖（mpv meson.build `dependency('libass')` 不可裁剪），必须先于 libmpv 发布。
- `-Dlibunibreak=disabled` 仅影响 U+2011 非断行连字符类字符的换行处理，字幕主渲染流程（ass_render 等）不受影响；libunibreak 未发布到 ohpcd，属可接受裁剪。
- 字体提供者选择 Fontconfig：OHOS 无 DirectWrite（Windows）/CoreText（macOS），fontconfig 是唯一跨平台选项且已发布。
- 本地验证时修正过的 conan 包 .pc 文件仅影响本机直连编译路径；提交的归档 conandata.yml 只含官方源 URL（R39）。
