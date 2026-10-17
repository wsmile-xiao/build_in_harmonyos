# raqm 0.11.0 适配笔记

## 编译环境
- 构建系统: meson（上游 0.11.0 仅提供 meson.build；autotools 文件自 0.9.x 后已移除）
- 编译日期: 2026-09-16
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: built（conan-verify 通过，W3 本地 CI 通过）

## 源码信息
- URL: https://github.com/HOST-Oman/libraqm/archive/refs/tags/v0.11.0.tar.gz
- SHA256: 2ba3521d3f24e9696185a67a16f1a9643429d6c897d89d83dfb2aad3a398732a
- tag v0.11.0 → commit 08ee1537e63f93bf926498e12b12ed15ee383216
- 格式: tar.gz

## 编译步骤（探索验证）
1. `conan install --requires=harfbuzz/14.3.0 --requires=fribidi/1.0.16 --requires=freetype/2.14.3 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 -g PkgConfigDeps -g VirtualRunEnv --build=missing`
2. `export PKG_CONFIG_PATH=$PWD`（meson 经 pkg-config 找 freetype2/harfbuzz/fribidi 三个 .pc）
3. `export CFLAGS="-I<fribidi包>/include/fribidi"`（头文件子目录注入，见问题表）
4. `meson setup builddir && ninja -C builddir` → 10/10 目标全部编译通过
5. `meson test -C builddir`（LD_LIBRARY_PATH 指向三个依赖包 lib/）→ **51/51 OK**

配方化：MesonToolchain（-Ddocs=false -Dtests=true -Dsheenbidi=false）+ PkgConfigDeps，
build() 内在依赖 libdir 注入 LD_LIBRARY_PATH 后执行 meson.test() 重跑同一套件。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `fatal error: 'fribidi.h' file not found` | fribidi conan 包 cpp_info.includedirs=['include']，但头文件实际装在 include/fribidi/ 子目录（raqm.c `#include <fribidi.h>`） | conanfile.py generate()/build() 注入 CFLAGS/CPPFLAGS `-I<fribidi>/include/fribidi`（meson setup 从环境读取） |
| 2 | 上游测试二进制（raqm-test 等）运行时找不到 libharfbuzz.so/libfribidi.so/libfreetype.so | 测试可执行文件链接 conan 依赖的共享库，设备加载器默认搜索路径不含 conan 包目录 | build() 中 meson.test() 前用 Environment 组装 LD_LIBRARY_PATH（三依赖 libdir）+ MESON_TESTTHREADS=1 |
| 3 | 消费者测试初版 layout 失败返回 false | raqm API 顺序约束：raqm_set_text* 会重置每字符 ftface（_raqm_init_text_info 置 NULL），set_freetype_face 必须在 set_text 之后；且需 FT_Set_Char_Size(face, units_per_EM,0,0,0) | test.c 按上游 tests/raqm-test.c 范式重排：create → set_text_utf8 → set_par_direction → set_freetype_face → layout |

## 源码修改
无补丁。仅配方侧处理 fribidi 头文件路径与测试运行期库搜索路径（见上表 1/2），
上游源码零改动。

## 依赖版本
- freetype/2.14.3（harfbuzz 传递依赖，显式声明——raqm 直接用 FT_Face）
- harfbuzz/14.3.0
- fribidi/1.0.16
三者在制品仓均已发布（conan download --only-recipe 验证，W0 通过）。

## 上游测试（51 目标全跑）
- tests/meson.build 注册 51 个 meson test()：49 个 .test fixture（经 tests/runtest.py
  驱动 raqm-test 铰链，双向文本/游标/连字/多字体等场景）+ grapheme-break（读
  GraphemeBreakTest.txt）+ detected-direction
- 设备实测（OHOS aarch64）：**Ok: 51, Fail: 0, skipped: 0**
- conan create 内 build() 会再次执行同一套件

## 验证结果
- 探索构建: ninja 10/10 + meson test 51/51 OK
- conan-verify: G1-G4 + L2/L4/L5 通过
- test_package: test_raqm 链接 libraqm + 依赖，无字体路径 API 全链路断言
  （version/create/set_text_utf8/set_par_direction/layout 失败路径/get_glyphs 空结果）→ PASS

## 产物
- lib/libraqm.so.0.11.0（+ .so.0 / .so 别名）
- include/raqm.h、include/raqm-version.h
- lib/pkgconfig/raqm.pc

## 注意事项
- meson 查找 freetype2 用 libtool 版本号（24.0.18）；仓内 freetype/2.14.3 的
  .pc Version 为 26.6.20（system_package_version），满足 >= 24.0.18
- sheenbidi 保持默认 false（用 fribidi 路径，与仓内已发布的 fribidi 对齐）
- test_package 不携带字体二进制（PR diff 保持纯文本——GitCode .diff 对大
  二进制文件生成 missing binary patch data，CI checkout-pr 应用失败）；
  字体驱动布局由上游 51 测试承载（源码 tarball 自带 tests/fonts）
---

**编译结束**: 2026-09-16 15:22
**最终状态**: built
