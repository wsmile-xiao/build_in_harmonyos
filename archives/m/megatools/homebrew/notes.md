# megatools homebrew 适配笔记

## 编译环境

- 构建系统：Meson
- 编译日期：2026-07-15
- 编译器：Conan profile 指定的 clang
- 状态：built

## 源码信息

- 版本：1.11.1.20230212（Homebrew 对应上游版本）
- 官方源码 URL：`https://xff.cz/megatools/builds/megatools-1.11.1.20230212.tar.gz`
- 备用缓存 URL：`https://distfiles.macports.org/megatools/megatools-1.11.1.20230212.tar.gz`
- SHA256：`ecfa2ee4b277c601ebae648287311030aa4ca73ea61ee730bc66bef24ef19a34`

## 依赖

| 依赖 | Conan 引用 | 说明 |
|------|-----------|------|
| glib | glib/2.84.0 | 提供 gio-2.0 / glib-2.0 / gmodule-2.0 等 pkg-config 模块（静态 .a + .pc），子模块 .pc 在 glib 包 lib/pkgconfig 下 |
| zlib | zlib/1.3.1.1 | gio-2.0.pc 的 Requires.private 传递依赖（静态 .a + zlib.pc） |
| openssl | openssl/3.5.6.1 | 加密支持（静态 .a + openssl.pc）；对齐 curl/8.15.0 依赖版本（FD_SET 可移植性修复） |
| curl | curl/8.15.0 (shared=False) | megatools meson.build 硬依赖 dependency('libcurl')；curl 配方支持 shared=False 生成 libcurl.a，满足 OHOS 静态链接要求 |
| libffi | glib/2.84.0 传递 | glib Conan 包已传递拉入 libffi/3.4.4 |
| pcre2 | glib/2.84.0 传递 | glib Conan 包已传递拉入 pcre2/10.40 |
| libintl | Worker 系统预编译包 | glib 静态库有 gettext 符号未定义引用（U bind_textdomain*/dcgettext 等），需外部 -lintl，ohpcd 无 gettext/libintl Conan 包，需 Worker 预装静态 libintl.a，通过 native file 的 pkg_config_path 第二项指向 ~/usr/local/lib/pkgconfig 发现 |

glib-networking 仅为运行时依赖（megatools 使用 libcurl 做网络传输），构建期不需要，故省略。

## 编译步骤

1. 使用官方发布 tarball 源码，校验 SHA256。
2. Meson 配置选项：
   - `-Dman=false`：鸿蒙 PC 构建机无 docbook/xsltproc，关闭 man 页生成
   - `-Dsymlinks=true`：启用 megatools 子命令符号链接（megals/megadl/megaput 等）
3. 依赖经 PkgConfigDeps 生成 .pc 文件，Meson 通过 pkg-config 发现 gio-2.0/libcurl/openssl。
4. 构建 `megatools` 可执行文件及子命令符号链接。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Meson configure 报找不到 ar/ranlib | Conan MesonToolchain 仅映射 c/cpp 编译器路径，不映射 ar/ranlib；clang 工具链在 /data/service/hnp/bin 不在 PATH 上 | 从编译器路径推导 llvm-ar/llvm-ranlib 全路径，注入 conan_meson_native.ini [binaries] 段 |
| 2 | man 页生成失败 | 构建机无 docbook/xsltproc | `-Dman=false` 关闭 man 页生成 |
| 3 | glib-networking 缺失 | glib-networking 仅为运行时依赖，megatools 使用 libcurl 做网络传输 | 构建期省略；GLib/libcurl 使用 Worker 系统预编译包，OpenSSL 使用 Conan 制品 |
| 4 | 旧源码域名无法解析 | megatools.megous.com 已迁移，CI Worker DNS 无法解析旧域名 | 主地址改为上游新域名 xff.cz，增加相同 SHA256 的 MacPorts distfiles 缓存作为 fallback |
| 5 | CI #3348 编译失败：`Dependency "gio-2.0" not found` | `_inject_meson_native_file` 的 pkg_config_path 注入逻辑有 bug：仅修改已存在的 `pkg_config_path = ` 行，但 MesonToolchain 生成的 native file 不含此行，导致注入不生效；Meson 不读环境变量 PKG_CONFIG_PATH，只读 native file | 重写注入逻辑：在 native file 的 `[properties]` 段下新增 `pkg_config_path`（若段不存在则创建），同时移除无效的 `Environment().save_script()` 环境变量注入（生成的脚本不会被 Conan 自动 source） |
| 6 | CI #17095 仍失败 `Dependency "gio-2.0" not found`（configure 期） | 配方只声明 `openssl/3.5.6`，gio-2.0 完全依赖 Worker 系统预装的 glib；CI 干净 Worker 上无 `~/usr/local/lib/pkgconfig/gio-2.0.pc`，meson configure 阶段找不到依赖；上一轮 #5 修的是 native file 注入逻辑，但注入的路径下根本没有 gio-2.0.pc | 把 glib/2.84.0 改为 Conan 依赖（ohpcd 有静态包），PkgConfigDeps 把 gio-2.0.pc 生成到 generators_folder（native file pkg_config_path 首项），Meson 在 configure 期即可发现；同时把 zlib/1.3.1.1 也 Conan 化消除 -lz 的系统依赖；libcurl/libintl 因 ohpcd 无静态 Conan 包仍走系统预装（配方注释说明） |
| 7 | CI #2323 失败 `Dependency "libcurl" not found`（configure 期） | megatools meson.build 硬依赖 `dependency('libcurl')`，无禁用选项；ohpcd 的 curl/8.15.0、libcurl/8.5.0 仅发布动态 libcurl.so（OHOS musl 上非系统 .so 不加载），干净 CI Worker 上也无系统 libcurl.a/libcurl.pc，meson configure 期 pkg-config 找不到 libcurl | 把 curl/8.15.0 改为 Conan 依赖（`self.requires("curl/8.15.0")`），用 `default_options={"curl/*:shared": False}` 强制静态构建生成 libcurl.a；PkgConfigDeps 把 libcurl.pc 生成到 generators_folder，Meson configure 期 pkg-config 即可发现。openssl 对齐 curl 依赖的 3.5.6.1 避免图冲突 |
| 8 | conan create configure 期 `Dependency "gio-2.0" not found`（curl 已落盘后复现） | PkgConfigDeps 只为直接 requires 的包生成汇总 .pc（glib-2.0.pc），但 glib 的子模块 gio-2.0/gmodule-2.0/gobject-2.0 只存在于 glib 包自身的 `lib/pkgconfig` 下；native file pkg_config_path 首项（generators_folder）无 gio-2.0.pc，第二项（~/usr/local/lib/pkgconfig）CI 干净 Worker 上也不存在 | 在 `_inject_meson_native_file` 里遍历 `self.dependencies.host.values()`，把每个 Conan 依赖包的 `lib/pkgconfig`（若存在）追加到 native file 的 `pkg_config_path`，Meson 即可发现 glib 包下的 gio-2.0.pc 等子模块 |

## 测试说明

上游测试套件需要从 mega.co.nz 下载文件，CI 环境无外网访问能力，无法运行。

test_package 采用 --version 烟雾测试：

- `megatools --version`：验证可执行文件启动并输出版本信息
- `megatools --help`：验证帮助输出可用
- 验证子命令符号链接（megals/megadl）存在

## 知识积累

- Meson 构建的 C 项目在鸿蒙 PC 上的 ar/ranlib 注入模式：从 `tools.build:compiler_executables` 的 c/cpp 路径推导同目录 llvm-ar/llvm-ranlib，写入 conan_meson_native.ini
- megatools 是单可执行文件多子命令架构（类似 git），通过 argv[0] 或首参数分发子命令；`-Dsymlinks=true` 创建 megals/megadl 等符号链接
- **Meson 不读环境变量 PKG_CONFIG_PATH**，只读 native file 中 `[properties]` 段下的 `pkg_config_path`。Conan 的 `Environment().vars(scope="build").save_script("xxx")` 生成的自定义脚本不会被 Meson helper 自动 source，注入系统 pkgconfig 路径必须直接写入 conan_meson_native.ini
- **能 Conan 化就不要走 Worker 系统预装**：meson configure 期找不到依赖是 CI 失败的常见根因。gio-2.0 这类由 glib 提供的 pkg-config 模块，若 ohpcd 制品仓有静态 Conan 包（glib/2.84.0 含静态 .a + .pc），应直接 `self.requires` 声明，让 PkgConfigDeps 把 .pc 生成到 generators_folder——native file pkg_config_path 首项即此文件夹，Meson 优先在此发现，CI 干净 Worker 上无需预装 glib。上一轮只修 native file 注入逻辑但路径下无 .pc 文件，注入空路径无意义
- **ohpcd 制品仓的 curl/libcurl 仅动态 .so**：curl/8.15.0、libcurl/8.5.0 两个包都只发布 libcurl.so 无 libcurl.a，无法满足 OHOS 静态链接要求（非系统 .so 在 musl 上不加载）。但 curl 配方支持 `shared=False`，从源码构建可生成 libcurl.a。meson.build 依赖 libcurl 的包应 `self.requires("curl/8.15.0")` + `default_options={"curl/*:shared": False}`，让 PkgConfigDeps 把 libcurl.pc 生成到 generators_folder，Meson configure 期 pkg-config 即可发现
- **PkgConfigDeps 只生成直接 requires 的汇总 .pc**：glib 的子模块 gio-2.0/gmodule-2.0/gobject-2.0 的 .pc 文件只存在于 glib 包自身的 `lib/pkgconfig` 下，PkgConfigDeps 不会把它们复制到 generators_folder。配方需在 `_inject_meson_native_file` 里遍历 `self.dependencies.host.values()`，把每个 Conan 依赖包的 `lib/pkgconfig`（若存在）追加到 native file 的 `pkg_config_path`，Meson 才能发现这些子模块 .pc
- **glib 静态库的 gettext 缺口**：libglib-2.0.a 含 `U bind_textdomain_codeset`/`U dcgettext` 等未定义引用，需外部 -lintl；ohpcd 无 gettext/libintl Conan 包，只能走 Worker 系统预装的 libintl.a。配方依赖 glib 静态包时需意识到此传递缺口
- Worker 系统预编译包通过 `install.sh` 安装 glib 2.88.0，提供 gio-2.0.pc，路径在 `~/usr/local/lib/pkgconfig`
