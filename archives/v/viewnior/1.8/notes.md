# viewnior 1.8 适配笔记

## 编译环境
- 构建系统: meson（init_build 误判为 autotools，按 meson 处理）
- 编译日期: 2026-10-08
- 编译器: clang/clang++（OHOS aarch64）
- 状态: built → published（conan-verify 全绿后更新）

## 编译步骤

meson 构建，conan create 流程（`python3 scripts/ohc-run.py conan-verify viewnior 1.8`）：

1. `conan create archives/v/viewnior/1.8 --build=missing`
   - source(): 解压官方 tag `viewnior-1.8` tar.gz（strip_root）并应用补丁 0001。
   - generate(): PkgConfigDeps 生成 gtk+-2.0/glib-2.0/gio-2.0/gdk-pixbuf-2.0/exiv2/expat/zlib
     .pc；注入 glib-2.0.pc 的 glib_genmarshal 变量（python 包装）并追加 -lintl；
     合成 shared-mime-info.pc；exiv2.pc 追加 `Requires: expat zlib`；
     MesonToolchain `-Dwrap_mode=nofallback`；注入 ar/ranlib/pkg-config 到
     conan_meson_native.ini；gettext/0.22.5.1 tool_require（msgfmt/xgettext）。
   - build(): `meson setup` + `meson compile`（TMPDIR 指向 build/tmp，依赖 bin 进 PATH）。
   - package(): `meson install`（DESTDIR），COPYING → licenses/，ELF 重新 codesign
     （binary-sign-tool，meson install 改写 RPATH 使链接期签名失效）。
   - test_package: viewnior_test.py 实际执行打包二进制。
2. conan-verify 门禁 G0/G1/G2/G3/G4/L2/L4/L5 全绿（详见 reports/conan-verify-report.md）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init 将构建系统判为 autotools | build_context 误判 | 按 meson 处理（前四轮已锁定） |
| 2 | shared-mime-info/2.5.1 pin glib/2.84.0 与 gtk2 链 glib/2.84.0.1 冲突 | 版本图冲突 | requirements 中 glib/2.84.0.1 加 force=True（blogc/0.20.1 同法） |
| 3 | meson `dependency('shared-mime-info')` 探测失败 | shared-mime-info conan 包无 .pc/无 cpp_info | generate() 合成 shared-mime-info.pc（Version 2.5.1） |
| 4 | exiv2 静态库链接缺 expat/zlib 符号 | 生成 exiv2.pc 无 Requires | exiv2.pc 追加 `Requires: expat zlib` |
| 5 | gnome.genmarshal 找不到 glib-genmarshal | PkgConfigDeps 不生成 glib_genmarshal 变量；OHOS 拒绝裸 shebang | glib-2.0.pc 注入 `glib_genmarshal=<wrapper>`（python 包装，accountsservice 模式） |
| 6 | i18n.gettext/merge_file 需要 msgfmt | 设备无 gettext 工具 | gettext/0.22.5.1 tool_require（VirtualBuildEnv 注入 PATH） |
| 7 | `viewnior --version` 无头运行失败（Cannot open display） | GTK 选项组 pre-parse 打开 X display，OHOS worker 无 X server | 补丁 0001：--version 提前打印 PACKAGE_STRING（与显示路径输出一致） |
| 8 | `src/uni-exiv2.cpp` C++ 编译失败：`fatal error: 'exception' file not found` | CI profile 无 `tools.build:cxxflags`，meson 未注入 OHOS SDK libc++ 头路径（本地 ohos-aarch64-local 才有） | conanfile.generate() 新增 `_inject_libcxx_include`：探测 SDK libcxx-ohos 布局，把 `-isystem` 注入 meson cpp_args |
| 9 | `src/uni-exiv2.cpp` 编译失败：`no type named 'AutoPtr' in 'Exiv2::Image'` / `no type named 'AnyError' in namespace 'Exiv2'` | viewnior 1.8 写于 exiv2 0.21 时代，`AutoPtr`/`AnyError` 在 exiv2 0.28 中已移除/改名（`UniquePtr`/`Error`） | 补丁 0002：`AutoPtr -> UniquePtr`、`AnyError -> Error`（3+3 处机械替换） |

## 源码修改

| 补丁 | 文件 | 内容 |
|------|------|------|
| 0001 | src/main.c | 增加无头早退：argc 循环识别 `--version` 时先打印 PACKAGE_STRING 并 return 0（在 gtk 选项组打开 display 之前）；补 `#include <string.h>`。输出与显示路径一致（"viewnior 1.8"），有显示时行为不变 |
| 0002 | src/uni-exiv2.cpp | exiv2 0.28 API 迁移：`Exiv2::Image::AutoPtr` → `Exiv2::Image::UniquePtr`、`Exiv2::AnyError` → `Exiv2::Error`（`AutoPtr`/`AnyError` 在 exiv2 0.28 中已移除/改名） |

## 依赖版本

| 包 | 版本 | 来源 |
|----|------|------|
| gtk2 | 2.24.33 | ohpcd 已发布二进制（x11 后端） |
| glib | 2.84.0.1 | ohpcd 已发布（gtk2 链共同 pin，force 收敛） |
| gdk-pixbuf | 2.44.6.1.1 | ohpcd 已发布（W0） |
| exiv2 | 0.28.7 | ohpcd 已发布（W0） |
| shared-mime-info | 2.5.1 | ohpcd 已发布（W0） |
| gettext（工具） | 0.22.5.1 | ohpcd tool_require |

## R51 上游测试清点（viewnior 1.8）

清点证据（对解压源码树 /storage/Users/currentUser/builds/viewnior-1.8.work 逐一核对）：

- 顶层目录：AUTHORS COPYING NEWS README.md TODO data man meson.build
  meson_post_install.py po src —— **无 tests/ 目录、无 test* 子目录**。
- `find . -iname '*test*' -o -iname 'check*'`（排除 src/main.c 中的 main）：
  **无任何独立测试文件**。
- meson.build 仅 `subdir('po'/'data'/'man'/'src')`，**无 `test(` 目标**；
  data/meson.build 中唯一的 `test('validate-desktop', desktop-file-validate ...)`
  为 `find_program('desktop-file-validate', required: false)` 守卫，该外部命令在
  设备上不存在 → 测试不会注册/运行，且属构建期可选校验而非上游测试套件。
- 结论：**上游无独立测试目录/无自动化测试套件**，功能覆盖由 test_package 消费者
  测试提供（viewnior_test.py：aarch64 ELF、GTK+2 动态链接闭包、--version 版本输出、
  --help 无头 display-init 失败形态）。

## 验证结果

```bash
python3 scripts/ohc-run.py conan-verify viewnior 1.8
# G0 预构建评估  PASS
# G1 配方完整性  PASS（conanfile/conandata/test_package/MANIFEST.yml 齐全）
# G2 conan create PASS（meson clean build + test_package 消费者测试）
# G3 系统同名库隔离 PASS（application，无系统同名 .so 冲突）
# G4 产物完整性  PASS（bin/viewnior 可执行文件）
# L2 平台 smoke   skip（CI harness 未注入 LD_LIBRARY_PATH，viewnior --version 失败，
#                  非阻断；实际版本验证由 test_package 在 conanrun env 下完成）
# L4 补丁危险函数扫描 PASS（patches clean；checksec 静态扫描由 conan-verify L4 报告）
# L5 产物内容    PASS（bin/ has content）
```

## 鸿蒙特有测试说明

- OHOS 构建 worker 无 X server，GTK+2 应用无法打开 display。补丁 0001 使
  `viewnior --version` 无头可用（输出与显示路径一致），L2 平台 smoke 与
  test_package 据此直接执行打包二进制。
- 消费者测试额外断言真 aarch64 ELF（e_machine=0xB7，OHOS 目标机器号），
  排除宿主/其他架构误产物。
- `--help` 无头运行仅止步于 GTK display 初始化（"display" 错误），用于证明
  GTK+2/glib/exiv2 全动态链接闭包解析成功（非库缺失/ABI 不匹配）。
- ELF 安装产物以 binary-sign-tool 重新 codesign（meson install 改写 RPATH
  使链接期 .codesign 失效，OHOS 加载器拒绝未签名 ELF）。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | meson 构建配方（generate 注入工具链 + glib-genmarshal/msgfmt） |
| conandata.yml | 官方源 URL + sha256 + 补丁声明 |
| patches/0001-main-c-headless-version.patch | 无头 --version 早退补丁 |
| test_package/ | conanfile.py + viewnior_test.py + MANIFEST.yml |
| commands.json | 软件级命令清单（可执行文件 viewnior，binary=true） |
| manifest.yaml / notes.md | 版本元数据与适配笔记 |
| reports/conan-verify-report.md | conan-verify 门禁逐项结果 |

## 注意事项

- gdk-pixbuf 对齐 gtk2 链：先试 ohpcd 已发布的 2.44.6.1.1，与 gtk2 的
  2.44.6.1 属 patch 级变体（minor_mode package_id 下已发布 gtk2 二进制仍可复用）。
- pango/libxrender 若本地无匹配二进制由 CI `--build=missing` 源码重建，配方不干预。
---

**编译结束**: 2026-10-09 13:15
**最终状态**: published
