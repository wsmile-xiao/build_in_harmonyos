# nip4 9.1.5 适配笔记

## 编译环境
- 构建系统: meson（>= 0.64，纯 C 应用，GTK4 UI + snip CLI）
- 编译日期: 2026-09-25
- 编译器: clang/clang++（/data/service/hnp/bin，OHOS armv8 工具链）
- 状态: built

## 编译步骤

1. `conan create` 用 CI 官方 profile `ci/conan/profiles/ohos-aarch64`（cppstd=17/libc++/os.version=6.0），
   与 ohpcd 发布二进制匹配，整图命中预编译制品（vips/gtk4/glib 等均不重建）。
2. configure 期需要 flex/bison（`lex.l`/`parse.y` → `lex.c`/`parse.c`，工具链自带）；
   代码生成走 gnome.genmarshal / gnome.compile_resources / gnome.mkenums。
3. meson configure → build → 上游 `meson test`（全部由 snip CLI 驱动）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| R1 | `glib-compile-resources: Operation not permitted`（ninja FAILED code=126） | ohpcd 发布的 glib/2.84.0.1.1 shared 包 bin/ 下 ELF 工具链接期 `.codesign` 已过期，OHOS 内核 exec 拒绝 | generate() 中移植 gtk4 R85/R86：`llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign -selfSign 1` 重签 glib 包全部 ELF 工具 |
| R2 | 重签后 `Error loading shared library libgio-2.0.so.0` | glib 工具无 RPATH，exec 时找不到 glib 自身 shared 库 | `LD_LIBRARY_PATH` 前置 glib 包 lib 目录（`_resign_glib_bin_tools`） |
| R3 | PkgConfigDeps 生成的 glib-2.0.pc/gio-2.0.pc 缺工具变量，meson gnome 模块报 "Could not get pkg-config variable" | Conan PkgConfigDeps 不导出工具路径变量 | `_fix_glib_pcs` 注入 glib_mkenums/glib_genmarshal/glib_compile_resources 等（gtkmm 同款） |
| R4 | meson 按裸名探测 ar/ranlib/pkg-config 失败（clang 工具链不在 PATH） | MesonToolchain 只映射 c/cpp 编译器条目 | `_inject_meson_binaries` 把 ar/ranlib/pkg-config 按绝对路径钉进 native/cross 文件（gtkmm 同款） |
| R5 | 全树源码构建（首次） | 本机默认 profile cppstd=gnu14/libstdc++11 与 ohpcd 制品 cppstd17/libc++ 不匹配 | 改用 CI 官方 profile `ohos-aarch64` 重建，全依赖命中二进制 |
| R6 | test_package 阶段 snip 全部表达式输出空串（CI #61562：13/17 FAIL，4 个 PASS 全是字节级检查、从不 exec snip） | **meson install 剥离构建期 rpath**：把 `.dynstr` 里 RUNPATH 字符串整段填 `X` 并删除 DT_RUNPATH 条目（readelf 可见 RUNPATH 消失、内容 hash 改变）；被改写过的 ELF 在 OHOS 上被内核 execve 直接拒（EPERM），**与 LD_LIBRARY_PATH 无关**（本地注入全量 conanrun LD_LIBRARY_PATH 仍 EPERM，报错发生在动态加载器运行之前） | package() 中 `Meson(self).install()` 后用 build 树未改写的原始 PIE（RUNPATH 仍指向依赖库路径）覆盖安装产物 bin/snip、bin/nip4；本地完整重放 run_tests.sh 17/17 通过（含真实 JPEG/PNG 落盘与魔数检查） |

## 源码修改

3 个补丁（`conandata.yml` `patches` 按 0001→0002→0003 顺序应用，均只动测试数据/脚本，不动产品代码）：

| # | 文件 | 内容 | 目的 |
|---|------|------|------|
| 0001 | test/test_cli.sh | shebang `/bin/bash` → `/bin/sh` | OHOS 沙箱无 bash；脚本体本身是 POSIX-only |
| 0002 | test/workspaces/*.ws | 上游开发者硬编码路径（/home/john/GIT/nip4、$HOME/GIT/nip4、/home/john/vips）→ `$VIPSHOME` 相对引用 | 测试数据在 Conan 构建树下可解析 |
| 0003 | test/workspaces/test_tasks.ws | A2/Pathname value `$VIPSHOME/...` → `../test/workspaces/images/...`（相对 meson test 的 cwd=构建目录） | Pathname 行原样传给 vips、不展开变量，0002 的 `$VIPSHOME` 式对 Pathname 无效；改相对路径后真实 meson test 2/2 OK |

补丁生成/验证方法：`patch -F0`（该环境无 `--fuzz` 选项）按 0001→0002→0003 顺序应用，diff 基于前序补丁应用后的文件状态生成（conan patch_ng 严格行号、时间戳 1970-01-01 陷阱）。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| vips | 8.18.4.1 | 需 >= 8.18（vips_thread_execute） |
| gtk4 | 4.22.4 | 需 >= 4.14 |
| gsl | 2.8 | 必需 |
| libxml2 | 2.15.3.1 | libxml-2.0 必需 |
| glib2 | 2.88.0 | vips 链 glib-2.0 provider |
| glib | 2.84.0.1.1 (shared=True) | gtk4 链 provider，已签名工具变体（gtkmm R8） |
| zlib | 1.3.1.1 (override) | 图统一到 PIC 变体（vips CI #44364 先例） |

## 验证结果

```bash
conan create --profile:build=... --profile:host=ci/conan/profiles/ohos-aarch64 . --build=missing
# 依赖全部命中二进制；nip4 自身编译 + 上游 meson test
# meson test：10 should-pass .ws ×2（含 VIPS_NOVECTOR 变体）+ 1 should-fail + 8 snip .def + test_cli.sh
# 全部由 snip CLI 驱动，无 GUI 依赖
```

实测（2026-09-25，meson test 从构建目录起进程，cwd=构建树 b/build-release/）：

| 上游测试 | 结果 | 说明 |
|---------|------|------|
| test_tasks.ws | **2/2 OK**（0003 补丁后） | Pathname value 改 `../test/workspaces/images/...` 相对构建目录；0002 的 `$VIPSHOME` 式对 Pathname 无效（原样传 vips、不展开） |
| test_colour.ws | FAIL | 根因：`vips_icc_import`/gainmap 符号与字段缺失（ohpcd vips 未编译 ICC/gainmap 支持），数据文件 sRGB.icm 本身存在；**不在 0003 范围**，非测试数据问题 |
| test_magick.ws | 环境受限 | 依赖外部 ImageMagick `magick` CLI，OHOS 非交互环境无此工具 |
| 其余 should-pass | PASS | filter/histogram/image/math/matrix/region/widgets 等 |
| should-fail（test_fail.ws） | 如预期 | 断言路径设计即失败用例 |
| snip .def 8 项 + test_cli.sh | PASS | 表达式求值（0001 补丁后 POSIX sh） |

test_package 冒烟：`run_tests.sh` 17 断言（snip -e 表达式 9 + Image_file→JPEG/PNG 保存与魔数 4 + ELF 字节级检查 4）。修复 R6（package() 保留 build 树原始 PIE 后）本地完整重放 **17/17 通过**，并在脚本内保留 snip stderr 落盘（`$WORK/expr.stderr`）供失败诊断。

## 注意事项

- **双 GLib 图**：vips 链 → glib2/2.88.0，gtk4 链 → glib/2.84.0.1.1，两个 provider 并存是 gtkmm/4.0.0 同构的既有结构，override 组照抄 gtkmm，勿擅自合并。
- **R85/R86 重签是必需的**：glib 工具签名是 ohpcd 包出厂状态问题，非 nip4 代码问题；不加会在任何消费 gnome.compile_resources 的包上复现（gtk4/gtkmm 已内置同款修复）。
- **OHOS execve 拒绝"被改写过的 ELF"（EPERM）**：meson install 剥离 rpath（.dynstr 填 X + 删 DT_RUNPATH）即属此类改写，安装态二进制 exec 即败、stdout 全空；修复必须保留 build 树原始 PIE（R6）。此坑与 R1 的 `.codesign` 过期同属 OHOS exec 校验，普通 Linux 上 meson 剥离 rpath 无副作用，勿在非 OHOS 平台误判为测试脚本问题。
- 交叉构建（build=Linux/host=OHOS）时构建机不能 exec aarch64 二进制，上游测试跳过并如实记录；native OHOS 环境直接跑全部测试。
- NLS 是可选软依赖（intl required:false），缺失时 ENABLE_NLS 关闭，不阻塞。
- 上游默认 c_std=c2x（C23），源码实际未用 C23-only 特性；若未来上游使用 C23 语法需降 c_std=c17。
- **known failures（预期非回归）**：meson test 中 test_colour.ws 因 ohpcd vips 未编译 ICC/gainmap（`vips_icc_import` 符号/字段缺失）失败；test_magick.ws 因 OHOS 非交互环境无外部 ImageMagick `magick` CLI 受限——两者均为环境/制品能力边界，非 nip4 代码问题，勿为"全绿"伪造依赖或绕过真实功能。test_tasks.ws 已由 0003 补丁修复（2/2 OK）。

---

**编译结束**: 2026-09-25
**最终状态**: built
