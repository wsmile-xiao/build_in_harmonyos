# libsoup3 3.6.5-r1 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-08-15
- 编译器: clang/clang++（/data/service/hnp/bin，llvm 工具链）
- 状态: published

## 背景

libsoup3 是 gupnp/gupnp-tools 的前置依赖，也是 gssdp conan-verify 的阻塞项
（gssdp/1.6.6 conanfile requires libsoup3/3.6.5-r1）。归档原配方是模板占位符
（meson_layout 已移除、requirements 空、cpp_info.libs 错误），本次重写为真实
配方并 conan create 到本地缓存。

## 编译步骤

```bash
# 下载源码（官方 GNOME 源，USTC 镜像 404 不可用）
curl -fL -o libsoup-3.6.5.tar.xz \
  https://download.gnome.org/sources/libsoup/3.6/libsoup-3.6.5.tar.xz
sha256sum libsoup-3.6.5.tar.xz   # 6891765aac3e949017945c3eaebd8cc8216df772456dc9f460976fbdb7ada234

# conan create（必须 export PKG_CONFIG_PATH，libsoup 的 libpsl/nghttp2 硬依赖经
# /usr/local pkg-config 解析；conan-verify G2 不自动注入）
export PKG_CONFIG_PATH=/storage/Users/currentUser/usr/local/lib/pkgconfig
conan create archives/l/libsoup3/3.6.5-r1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 模板配方用已移除的 `meson_layout()` | conan 2.29.1 移除 meson_layout | 手动 layout(): folders.build='builddir'、folders.generators='builddir/generators' |
| 2 | `meson.compile()` AttributeError | conan 2.29 Meson 助手无 compile() | build() 改用 meson.build()（glib2 范本） |
| 3 | glib2 静态/共享双副本风险 | glib2 缓存默认 shared=False | default_options={'glib2/*:shared': True} 强制共享（触发共享 glib2 重建约 20-40 分钟） |
| 4 | AR=llvm-ar 等环境变量坏 | PATH 无 llvm-ar | generate() 里 os.environ.pop + shutil.which 定位真实 GNU 工具（复刻 glib2 配方） |
| 5 | test_package 找不到 libsoup-3.0 目标 | CMakeDeps 的 cmake_file_name/target_name 默认=conan 包名 | package_info() 显式 set_property('cmake_file_name'/'cmake_target_name','libsoup-3.0') |
| 6 | 运行时加载共享库失败 | OHOS 加载器忽略 DT_RPATH/LD_LIBRARY_PATH 默认值；libsoup 依赖 libpsl/sqlite3/libnghttp2 是 /usr/local 系统库 | test() 显式 export LD_LIBRARY_PATH 含 /usr/local/lib |
| 7 | glib2 传递依赖在 CMakeDeps 中空数据 | conan 2.29 对传递依赖行为 | libsoup3 package_info() 里把 glib2 的 include/lib dirs 与库名并入自身 cpp_info |

## 源码修改

- 无源码补丁（libsoup 3.6.5 无 OHOS 特有修改；无 host_system=='linux' 判定、无 sockaddr_storage）

## 依赖版本

- glib2/2.88.0（共享 .so，静态 .a 已隐藏）
- 系统库（/usr/local，非 conan 包）：libpsl 0.23.2、libnghttp2、sqlite3、libidn2、libunistring

## 验证结果

```bash
conan create ... --build=missing   # 成功，test_package L1 通过
# RUN: export LD_LIBRARY_PATH='...:/usr/local/lib'; bash -c './test_libsoup3'
# test libsoup3 3.6.5-r1: OK (host=example.com, session+message ok)
conan list "libsoup3/*"            # libsoup3/3.6.5-r1@ohpcd/stable 在缓存
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | 真实 meson 配方（shared、PkgConfigDeps、工具链修复、CMakeDeps 命名） |
| conandata.yml | 官方 URL + sha256 |
| test_package/ | 真实 libsoup3 API 测试（SoupMessage/SoupSession/GUri 断言）+ MANIFEST.yml |

## 注意事项

- libsoup3 下游（gssdp/gupnp/gupnp-tools）配方必须强制 `"glib2/*:shared": True`
- conan-verify/finish 运行时需 export PKG_CONFIG_PATH（G2 不自动注入）
- 运行 test 二进制时需 export LD_LIBRARY_PATH 含 /usr/local/lib（libpsl/sqlite3/nghttp2 系统库）
- 编译结束。
