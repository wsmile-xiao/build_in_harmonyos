# vte 0.74.2 适配笔记

## 编译环境
- 构建系统: meson (≥0.60)
- 编译日期: 2026-09-03
- 编译器: clang/clang++ (OHOS aarch64)
- 状态: published

## 上游信息
- 软件: vte (GNOME 终端模拟器库)
- 版本: 0.74.2
- 上游源: https://download.gnome.org/sources/vte/0.74/vte-0.74.2.tar.xz
- sha256: a535fb2a98fea8a2449cd1a02cccf5190131dddff52e715afdace3feb536eae7
- 主页: https://gitlab.gnome.org/GNOME/vte
- API/soname: vte-2.91 (下游 aghermann 1.1.2 通过 PKG_CHECK_MODULES([VTE],[vte-2.91]) 引用)
- 许可证: LGPL-3.0-or-later, GPL-3.0-or-later

## 编译步骤

1. **下载源码**: 从 GNOME 官方源下载 vte-0.74.2.tar.xz 并校验 sha256
2. **meson 配置**: 禁用所有可选依赖（icu/libsystemd/gnutls/fribidi/gtk4/gir/vapi/glade/a11y），因为这些依赖未发布到 ohpcd 制品仓或非必要
3. **ninja 编译**: libvte-2.91.so + vte-2.91 二进制
4. **meson test**: 上游测试套件（11 个测试套件，inline 在 src/meson.build）
5. **conan create**: 完整 conan create 流程（build + test_package）

## 上游测试通过率: 100%

上游测试命令: `meson test`

### 测试套件结果 (11/11 OK)

| # | 测试套件 | 状态 | 耗时 |
|---|---------|------|------|
| 1 | vte:modes | OK | - |
| 2 | vte:parser | OK | - |
| 3 | vte:pastify | OK | - |
| 4 | vte:reaper | OK | - |
| 5 | vte:refptr | OK | - |
| 6 | vte:stream | OK | - |
| 7 | vte:tabstops | OK | - |
| 8 | vte:vtetypes | OK | - |
| 9 | vte:doc | OK | 0.71s |
| 10 | vte:utf8 | OK | 0.13s |
| 11 | vte:vte-urlencode-cwd | OK | 1.08s |

### 测试用例明细

- **vte:pastify**: 151 个测试用例 (ok 1 /vte/pastify/string/1 ... ok 151 /vte/pastify/string/151)
- **vte:reaper**: test-reaper (子进程回收测试)
- **vte:refptr**: 1 个测试用例 (ok 1 /vte/glib/refptr)
- **vte:stream**: vtestream-file tests passed
- **vte:tabstops**: 7 个测试用例 (default/get-set/clear/reset/resize/previous/next)
- **vte:vtetypes**: c++ 类型测试 (grid coords/halfcoords/span, color rgb, view coords, util restore-errno)
- **vte:utf8**: 2 个测试用例 (decoder/decode, decoder/replacement)
- **vte:doc**: check-doc-syntax.sh (文档语法检查)
- **vte:vte-urlencode-cwd**: test-vte-urlencode-cwd.sh (URL 编码测试)

### 证据

conan create 日志 (`.ci_logs/vte-create-bg.log`) 中完整记录了 `meson test` 输出，所有 11 个测试套件均显示 `OK`，无 FAIL/ERROR。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | b_ndebug 断言失败 | vte meson.build assert(b_ndebug=='false') | MesonToolchain tc.b_ndebug="false" |
| 2 | gio-2.0 pkg-config 变量缺失 | PkgConfigDeps 不生成 glib_compile_resources 等变量 | _inject_glib_tool_variables() 注入工具路径 |
| 3 | libpcre2-8 未找到 | PkgConfigDeps 生成 pcre2.pc，vte 查找 libpcre2-8 | _fix_pcre2_pc() 创建别名 .pc |
| 4 | undefined symbol g_libintl_bindtextdomain | glib-2.0.pc 缺 -lintl | _fix_glib_intl_link() 添加 -lintl |
| 5 | vte/vte.h 未找到 (test_package) | package_info includedirs 未设 include/vte-2.91 | cpp_info.includedirs.append("include/vte-2.91") |
| 6 | W_EXITCODE 未定义 | musl libc 不提供此宏 | patches/0001-Define-W_EXITCODE-for-OHOS-platform.patch |

## 源码修改

- **patches/0001-Define-W_EXITCODE-for-OHOS-platform.patch**: 在 meson.build 顶部添加 W_EXITCODE 宏定义（musl libc 不提供），用于 reaper 测试

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| cairo | 1.18.4 | ohpcd |
| pango | 1.50.14.1.1 | ohpcd |
| glib | 2.84.0.1 | ohpcd |
| pcre2 | 10.45 | ohpcd |
| zlib | 1.3.1.1 | ohpcd |
| gtk | 3.24.43 | ohpcd |

## 验证结果

```bash
# conan create 成功 (libvte-2.91.so + vte-2.91 二进制)
conan create archives/v/vte/0.74.2/conanfile.py --name=vte --version=0.74.2 \
    -pr=ci/conan/profiles/ohos-aarch64 -pr:b=default --build=missing

# meson test 11/11 OK (上游测试 100% 通过)
# 证据: .ci_logs/vte-create-bg.log
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | meson 配方 (含 gio-2.0 工具变量注入/libintl 链接修复/pcre2 别名/includedirs) |
| conandata.yml | 官方源 + sha256 + patch 声明 |
| test_package/ | 实质调用 vte API 的 smoke 测试 (R34) |
| patches/0001-Define-W_EXITCODE-for-OHOS-platform.patch | W_EXITCODE 宏定义补丁 |
| manifest.yaml | 版本级元数据 (status=published) |
| reports/ | conan-verify 报告 + conan create 日志 |
| .ci-result.json | finish step 5/10 写入 (exit_code=0 + 日志 SHA256) |

## 注意事项

1. vte 0.74.2 的可选依赖 (icu/libsystemd/gnutls/fribidi/gtk4/gir/vapi/glade/a11y) 全部禁用，因为这些依赖未发布到 ohpcd 制品仓或非必要
2. GNOME tarball 不含 tests/ 目录，但 vte 的单元测试 inline 在 src/meson.build 中，通过 `meson test` 运行
3. Conan 的 PkgConfigDeps 不生成 glib 工具变量 (glib_compile_resources 等)，需要在 generate() 中手动注入
4. glib-2.0.pc 缺 -lintl，需要手动修补以解决 undefined symbol g_libintl_bindtextdomain
5. 下游 aghermann 1.1.2 通过 PKG_CHECK_MODULES([VTE],[vte-2.91]) 引用此包
---

**编译结束**: 2026-09-03 12:49
**最终状态**: published
