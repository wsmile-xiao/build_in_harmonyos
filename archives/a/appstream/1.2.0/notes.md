# appstream 1.2.0 适配笔记（R02 依赖恢复续跑）

## 编译环境
- 构建系统: meson（meson>=0.62，c_std=gnu17）
- 编译日期: 2026-09-19
- 编译器: clang/clang++ 15.0.4（OHOS aarch64）
- 状态: built（conan-verify 通过；R05 复验后保持 built，未做远端制品上传）

## 背景
R01（appstream-1.2.0-r01-pc2-19）已完成 bootstrap/source/adaptation 门禁，因 meson 必需依赖
xmlb(libxmlb>=0.3.14) 未在 ohpcd 发布而 dependency_block 停止。R02 时 libxmlb/0.3.19 已发布
（pkg-config 名 xmlb，conan download 实测有二进制包），本任务为依赖恢复后的续跑：从依赖核验
到 PR 交付全流程。

## 编译步骤
1. conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
   （配方：archives/a/appstream/1.2.0/conanfile.py，MesonToolchain）
2. 官方源 https://github.com/ximion/appstream/archive/refs/tags/v1.2.0.tar.gz
   SHA-256=02f723cb1afa372d434896e138503163a44ad49e4a813d0d30713fc38ccb8d0c

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | zstd 版本冲突（libxmlb 链 1.5.7.1 vs 原配方 1.5.6） | libxmlb/0.3.19 requires zstd/1.5.7.1 | 配方 zstd 提升到 1.5.7.1（ohpcd 有二进制） |
| 2 | meson 探测 `llvm-ar --version` 失败 | OHOS worker 导出 AR/AS/STRIP/NM/RANLIB 为 llvm-* 裸名且不在 PATH（posix_spawn 不搜索 PATH） | generate() 剔除坏 env 并按绝对路径固定 ar/as/strip/nm/ranlib（libxmlb 先例） |
| 3 | meson 找不到 glib-2.0/gobject/gio/gmodule/gio-unix | 配方缺 PkgConfigDeps generator 且 glib .pc 以 prefix=/ 安装、Requires(.private) 带静态内嵌依赖 | 补 generators=PkgConfigDeps + glib pc-fix（复制 glib 包真实 .pc、重写 prefix、剥离 proxy-libintl/libpcre2-8/zlib/libffi），修正副本置 PKG_CONFIG_PATH 最前 |
| 4 | `include_directories(['/usr/include'])` 在 meson 配置期报目录不存在 | OHOS 构建机无 /usr/include；stemmer 头由 Conan 依赖提供 | patches/0001：移除硬编码 /usr/include，has_header 经 extra_cflags -I 探测成功时留空 include_dirs |
| 5 | `i18n.itstool_join` 要求 itstool 程序（OHOS 无） | data/meson.build 无条件生成翻译版 metainfo | patches/0002：find_program('itstool', required:false) 不可得时回退未翻译 metainfo，as-validate_metainfo.cli 仍运行 |
| 6 | 缺 bash-completion 依赖（pkg-config 无此包） | contrib/meson.build 无条件 dependency('bash-completion') | project_options bash-completion=false（命令补全非运行必需） |
| 7 | `Meson` 无 `compile()` 方法 | Conan 2.29 Meson helper API | meson.build()（libxmlb 同款） |
| 8 | glib-compile-resources 从缓存路径 exec 报 Error loading shared library / Operation not permitted | HMDFS 上已签名二进制从缓存路径运行受限，LD_LIBRARY_PATH 未聚合 | 为 glib-compile-resources/glib-mkenums 生成 wrapper 脚本（export LD_LIBRARY_PATH=glib_pkg/lib 再 exec 原二进制），tc.binaries 映射到 wrapper（meson find_program 期即替换，ninja 不再走 PATH） |
| 9 | as-category.c 等 `gettext` 未声明（-Werror=implicit-function-declaration） | OHOS sysroot 的 libintl.h 空 stub 无 gettext 声明；glib 包内 proxy libintl.h 才映射到 g_libintl_* | 从同 glib 包副本复制 proxy libintl.h 到构建 include 目录并前置 -I（at-spi2-core 先例） |
| 10 | 测试目标编译缺 libfyaml.h | appstream_dep 不透传 fyaml include（上游假设系统默认路径有头） | 全局 extra_cflags -I 指向 libfyaml 包（与 stemmer 同款方案） |
| 11 | CMakeDeps consumer 找不到 appstream.h | 头文件安装在 include/appstream/，默认 includedirs=["include"] 不覆盖 | package_info 显式 includedirs=["include/appstream"] |
| 12 | test_package 链接报 fy_*/sb_* 未定义（libfyaml/libstemmer） | PkgConfigDeps 对根级 cpp_info.requires 生成 .pc Requires 不完整 | 组件式 package_info（libxmlb 同款：components["appstream"] + lib.requires 全量传递依赖），appstream.pc Requires 链完整 |
| 13 | `package_type='application'` 使 CMakeDeps 不生成库目标 include/libs | application 包类型按可执行处理 | package_type='library' + options{shared,fPIC}（appstreamcli CLI 由 commands.json 声明，R38） |
| 14 | W3 L0d 门禁 stub_test_method | test_package test() 只调 cmake.test() 无 self.run() | test() 补充 self.run(消费者二进制, env=conanrun) |

## 依赖版本
- glib/2.88.3、libcurl/8.5.0、libxml2/2.15.3.1、libfyaml/0.9.6、libstemmer/3.1.1、
  zstd/1.5.7.1、libxmlb/0.3.19（ohpcd 制品仓）

## 验证结果
- conan create：构建通过，test_package 真实 API 消费者测试 1/1 通过
- 上游测试双口径：source_declared_total=14 / configured_executable_total=8；
  执行 8 项，通过 4、失败 4（2 项 /tmp erofs 只读硬编码路径平台阻塞、2 项 ohpcd
  libcurl 无 SSL 导致 https URL 格式误判为依赖能力缺口），全量 4/14 (28.6%)，
  可执行集合 4/8 (50%)；明细见 reports/evidence/r02-upstream-test-ledger.md
- 鸿蒙专项测试 harmonyos-test/harmonyos_appstream_test：编译运行 10 项断言全 PASS
- conan-verify：G1-G5 全 PASS

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（meson、组件式 package_info、glib pc-fix、glib 工具 wrapper） |
| conandata.yml | 官方源 + SHA-256 + 2 补丁 |
| patches/0001-stemmer-include-dir.patch | 移除硬编码 /usr/include |
| patches/0002-itstool-optional.patch | itstool_join 可选回退 |
| test_package/ | L1 消费者验证（真实 API 调用） |
| harmonyos-test/ | 鸿蒙专项测试（真实可执行用例） |
| commands.json | CLI 声明（appstreamcli，R38/L0k） |

## 注意事项
- 构建机 github.com 直连超时，本地构建曾临时以本地 tarball 完成；提交前已恢复官方 HTTPS URL 并核验 SHA-256
- /tmp 为 erofs 只读，上游硬编码 /tmp 路径的测试（test_utils_untar / FileMonitorDir）为真实平台阻塞
- ohpcd libcurl/8.5.0 无 SSL（curl_url_set 对 https 返回 CURLUE_BAD_SCHEME），https URL 格式校验误报，属依赖能力缺口

### 对话 #1（R02，2026-09-19）
任务：appstream-1.2.0-r02-pc2-19（依赖恢复续跑，libxmlb/0.3.19 已发布）。
R01 依赖阻塞（xmlb/libxmlb>=0.3.14 未发布）已解除，本任务完成：依赖核验、meson 构建全修复
（工具路径/glib pc-fix/stemmer itstool 补丁/glib 工具 wrapper/gettext 声明/libfyaml include）、
test_package 真实 API 消费者验证、鸿蒙专项测试、上游测试双口径台账（4/8 通过，2 项 /tmp erofs
平台阻塞 + 2 项 libcurl 无 SSL 依赖缺口）、conan-verify、finish W2/W3 门禁。知识候选随任务 #8 查重。
---

**编译结束**: 2026-09-25 15:35
**最终状态**: built
