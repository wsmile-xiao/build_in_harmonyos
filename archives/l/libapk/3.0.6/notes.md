# libapk 3.0.6 适配笔记

## 编译环境
- 构建系统: meson (>=0.64) + ninja
- 编译日期: 2026-09-19
- 编译器: clang/clang++
- 状态: built（待真机预检回填证据后由 HMBS 统一提交）
- 许可证: GPL-2.0-only

## 软件简介
libapk 是 Alpine 包管理器 apk-tools 的核心库（版本比较、blob、包数据库、依赖求解、签名校验、仓库解析），随附 `apk` 命令行。上游 apk-tools 3.0.6 顶层 meson 同时构建 `libapk.so.3.0.0` 与 `apk` 可执行文件。

## 编译步骤
1. `get()` 下载 `https://gitlab.alpinelinux.org/alpine/apk-tools/-/archive/v3.0.6/apk-tools-v3.0.6.tar.gz`（sha256 见 conandata.yml）。
2. `generate()` 用 `PkgConfigDeps` 暴露 openssl/zlib/zstd，给 `MesonToolchain` 传 `-Ddocs=disabled -Dhelp=disabled -Dlua=disabled -Dpython=disabled -Dtests=disabled -Dzstd=enabled --wrap-mode=nodownload`，并从 C 编译器同目录推导 llvm-ar/llvm-ranlib 注入 `conan_meson_native.ini`。
3. `meson.configure()` + `meson.build()` 编译安装。
4. `build()` 随后编译 `build_folder/upstream/upstream_probe`（头文件用源码 `src/`，链接刚构建出的 libapk），跑上游 `test/unit/version.data` 全量行用例 + blob 向量用例，输出 `HMBS_UPSTREAM_TEST_RESULT` 并落盘 `upstream_test_result.json`。
5. `package()` 执行 `meson.install()`，对 `.so` 剥 `.codesign` 后自签，把证据文件拷入 `res/`。

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson 尝试联网下载 wrap 子项目 | 默认 wrap_mode 允许下载 | 传 `--wrap-mode=nodownload`，依赖全部走 Conan PkgConfigDeps |
| 2 | docs/help/lua/python 打不开 | 需要 scdoc/lua/python 绑定，OHOS 包构建不需要 | `-Ddocs=disabled -Dhelp=disabled -Dlua=disabled -Dpython=disabled` |
| 3 | cmocka 单元测试无法以 Conan 依赖引入 | cmocka/2.0.2 在制品仓仅 built 未 published，R36/PF4 禁止引用未发布依赖 | `-Dtests=disabled`，改用真实 libapk 跑上游 `version.data` 的可比 harness（同数据文件、同库 API），缺口在 PR 补充说明如实声明 |
| 4 | shell/solver 用例依赖目标机 shell 与 apk 运行环境 | OHOS 真机 shell/路径与 Alpine CI 差异大，易引入环境性失败 | 首轮不跑 shell/solver，只跑确定性的 version/blob 库内用例；如真机要求补跑再迭代 |
| 5 | meson 报 Unknown linker llvm-ar | MesonToolchain 的 native file 缺 ar/ranlib，meson 按裸名探测 | 从 `tools.build:compiler_executables` 的 C 编译器同目录推导全路径并注入 native file |
| 6 | 安装后的 .so 在 OHOS 上 dlopen 失败 | meson install 改写 rpath 破坏链接器自签 | package() 后剥 `.codesign` 并 `binary-sign-tool -selfSign 1` 重签 |
| 7 | 真机预检在 zlib/1.3.1 的 cmake.configure 失败（Platform/HarmonyOS unknown + CMAKE_C_COMPILER 中断） | 引用原生 zlib/1.3.1 会解析到 conancenter CMake 配方，不支持 OHOS；仓库约定下游引用 OHOS 适配的 zlib/1.3.1.1（Makefile -fPIC 静态，见其 manifest 与 abuild/libpng/cairo先例） | requirements 改指 `zlib/1.3.1.1`，manifest/notes 同步 |
| 8 | 真机预检在 zstd/1.5.6 的 cmake.configure 失败（Platform/HarmonyOS unknown + C/CXX/ASM 三编译器检查中断，line 71 build/cmake） | 原生 zstd/1.5.6 解析到 conancenter CMake 配方 | requirements 改指 `zstd/1.5.7`（该假设后被证伪，见 #9） |
| 9 | 改指 zstd/1.5.7 后真机仍在同一位置失败（conancenter recipe revision b68ca8e3，CMakeLists.txt:36 project 处 C/CXX/ASM 中断，line 71 cmake.configure） | 版本碰撞：conancenter 上同时存在 1.5.6 与 1.5.7，预检按该远端配方解析；凡与 conancenter 同号的版本都会被遮蔽，与 OHOS 适配状态无关 | 改用 OHOS 后缀版本 `zstd/1.5.7.1`（conancenter 无此版本，不会被遮蔽；其仓内配方直调 ohos.toolchain.cmake，zarchive/0.1.2、firebuild、openrct2、nxp-mfgtools 均已引用），manifest/notes 同步 |
| 10 | 真机 `source()` 下载官方归档报 `Error 418`（Conan 重试两次后失败，`conan create` 中断于 source 阶段） | 初判为 Conan 默认 UA 被 goaway 反爬墙拦截 | 首轮加浏览器 UA 经 urllib 兜底；**真机复检同样 418，证实与 UA 无关，该路线已放弃**（见 #11） |
| 11 | 同上（`conan get` 与浏览器 UA 兜底在真机均 `HTTP Error 418: I'm a teapot`） | 同一主机同一 HTTP 归档端点对真机网络整体不可用，换 UA 不能绕过；GitHub 官方镜像（alpinelinux/apk-tools，[MIRROR]）是不同主机，可经 git 协议取同一 tag（v3.0.6，上游记录提交 7e92634a） | `_fetch_archive` 改为新策略：`get(retry=0)` 首选官方原址，失败即 `git clone --depth 1 --branch v3.0.6` 官方镜像，校验 HEAD 前缀与 `test/unit/version.data` 非空后拷入源目录（去 `.git`）；conandata 仍保留官方单 URL + 原 sha256。**真机已验证通过**（`mirror HEAD: 7e92634afe99db29e00037e6a134104ad9720b68`，source 阶段成功） |
| 12 | 真机 `meson.configure()` 报 `Unknown compiler(s): [['/data/service/hnp/bin/clang']]`（该路径 ENOENT） | MesonToolchain 把配置的绝对编译器路径锁进 native file，而真机实际工具链不在该路径（PATH 上的才是可用实例）；此前只修了 ar/ranlib，未重写 c/cpp | `generate()` 后 `_fix_meson_native` 把 c/cpp 重写为 `--version` 探针验证过的可执行文件（PATH 优先、配置路径仅兜底），ar/ranlib 继续从验证后的编译器同目录推导；`_cc()` 收敛为同一探针 |
| 13 | 真机 `meson.configure()` 报 `Dependency lookup for libzstd with method 'pkg-config' failed: Pkg-config for machine host machine not found`（meson-log，同轮 source 已通、编译器已修，属新失败域） | 真机无系统 pkg-config（HMBS 仅注入 cmake/make/ninja/python3），且 pkgconf/3.0.5 刻意只装 `pkgconf` 不带 `pkg-config` 别名；配方此前无 build-requirement，meson 按裸名探测必然失败，与编译器路径无关 | 新增 `build_requirements: pkgconf/3.0.5`；`generate()/build()` 经 `_ensure_pkg_config_shim` 建 `hmbs-shims/pkg-config -> pkgconf` 软链（cassbeam 同款，symlink 优先、copyfile 兜底），前置 PATH 并导出 `PKG_CONFIG`/`PKG_CONFIG_PATH`；`_fix_meson_native` 同步向 native file 注入 `pkgconfig` 条目。**真机已验证通过**（meson 配置成功，构建推进到 `[27/77]` 编译阶段） |
| 14 | 真机 `meson.build()` 在 `[27/77] src/io.c` 失败：`fgetpwent`/`fgetgrent` 未声明（implicit declaration + `-Wint-conversion` 硬错误，clang 直接中断，ninja 停止） | 上游 `src/io.c` 仅在 `__GLIBC__/__UCLIBC__` 下用可重入 `_r` 变体，其余非 Apple 平台直调 `fgetpwent()/fgetgrent()` 这两个 GNU 扩展；OHOS libc 无此二函数（头文件无声明、链接亦无），与编译器路径/pkg-config 无关，属新失败域 | `source()` 后 `_patch_io_fgetent_fallback` 做源码适配（ext4fuse 同款 build-time 编辑，无补丁文件）：在 `idcache_load_users/groups` 前注入 `hmbs_fgetpwent/grent_fallback`（逐行解析嵌套 `etc/passwd\|group` 文本 `name:x:id:...`，EOF 返回 NULL，原语义），仅重定向 `#elif !defined(__APPLE__)` 分支的两处调用；glibc/uClibc（`_r`）与 macOS（`getpwent/getgrent`）分支不动，同类 id 缓存照常填充，无跳过 |
| 15 | 真机 `source()` 偶发失败：`git clone https://github.com/...` 65 秒连接超时（前三轮同链路均一次成功并通过 HEAD 校验，属瞬时网络抖动，非配方逻辑错误） | 单次 clone 无重试，瞬时建连失败即中断整个 `conan create` | `_fetch_via_git_mirror` 改为可靠性增强（新路线，非换源）：双远端（GitHub 官方镜像优先、GitLab 官方仓库 git 协议兜底）× 每远端 3 次重试（退避 15/30 秒），HEAD 前缀 `7e92634a` 与 `version.data` 非空校验保持不变；conandata 仍为官方单 URL + 原 sha256（GitHub/GitLab 归档非逐字节相同，无等效 tarball 镜像，不引入 url 列表） |

## 源码修改
无补丁文件（patches_applied 为空）。源码适配在 `source()` 后以 build-time 编辑完成（ext4fuse 同款做法，不进 patches/）：
- `src/io.c`：注入 `hmbs_fgetpwent/grent_fallback`（逐行解析嵌套 `etc/passwd|group`，仅填充 `pw_name/pw_uid`、`gr_name/gr_gid`），仅重定向非 Apple 非 glibc/uClibc 分支的两处调用；glibc/uClibc（`_r`）与 macOS 分支不动。

## 依赖版本
- openssl/3.5.8.1（published）
- zlib/1.3.1.1（OHOS 适配 -fPIC 静态配方；下游按仓库约定引用，不用原生 1.3.1）
- zstd/1.5.7.1（OHOS 后缀版本，conancenter 无此号故不会被遮蔽；仓内配方直调 ohos.toolchain.cmake，zarchive/firebuild/openrct2/nxp-mfgtools 均已引用）

## 验证结果
待 HMBS 真机预检回填：`conan create`（含 meson 构建 + 上游 version/blob harness + test_package 4 用例）。预检日志中的 `HMBS_UPSTREAM_TEST_RESULT` 与 `HMBS_TEST_PACKAGE_RESULT` 为通过率唯一依据。

## 交付物
| 文件 | 说明 |
|------|------|
| lib/libapk.so(.3.0.0) 或 libapk.a | 核心库（shared 选项切换） |
| include/apk/*.h | 公共头（apk_version.h/apk_blob.h 等） |
| lib/pkgconfig/apk.pc | pkg-config 描述 |
| bin/apk | 随附命令行 |
| res/upstream_test_result.json | 上游 harness 证据（供 test_package 原样重发） |

## 注意事项
- 本机 Windows 只做配方编写，不运行 conan；一切编译与测试结论以真机预检日志为准。
- 上游 `test/unit` 的 cmocka 用例与 `test/user|test/solver` 的 shell 用例首轮未运行，已在 PR 补充说明声明，不写 100%。
