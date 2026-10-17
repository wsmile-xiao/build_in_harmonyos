# upower-glib 0.99.20 适配笔记

## 编译环境
- 构建系统: meson（upower 0.99.20 使用 meson，非 autotools）
- 编译日期: 2026-09-19
- 编译器: clang 15.0.4（OHOS SDK）/ llvm-ar / ld.lld
- 目标: os=OHOS arch=armv8（aarch64-linux-ohos），shared=True
- 状态: built（本地 conan create + W3 本地 CI 通过；CI release 上传成功后更新为 published）

## 编译步骤

1. `ohc-run.py init-build upower-glib 0.99.20 --url=<官方 gitlab archive URL>`：下载官方
   v0.99.20 tarball，SHA-256 `6b11baeb4e9273def260ca86f2ed482ab4e56e8f4e999b2632d6ba0ea2bccd9a`
2. `lang-preflight`：task=cpp，detected=c（源文件 39 个，c:36 + python:3，主体 92%），兼容族通过
3. 编写 conanfile.py（meson 配方，依赖 glib/2.88.3）：
   - `generate()`: PkgConfigDeps + MesonToolchain；禁用 man/gtk-doc/introspection/idevice/
     udevrulesdir/udevhwdbdir/systemdsystemunitdir（OHOS 无 udev/systemd）
   - glib pc-fix：PkgConfigDeps 不生成 gio-unix-2.0.pc，meson 硬依赖；复制 glib 包
     lib/pkgconfig 全部 .pc 到 `glib-pc-fix/`，重写 prefix、剥离 proxy-libintl/zlib/
     libpcre2-8 私有 Requires、清空 Requires.private，gio-2.0.pc 注入 gdbus_codegen 变量，
     并 prepend 到 pkg_config_path（glib-networking 2.90.0 同款）
   - `package()`: meson install 后执行 OHOS ELF 签名（binary-sign-tool -selfSign 1），
     对包内全部 ELF（libupower-glib.so.3.1.0、bin/upower、bin/upowerd）签名，
     libupower-glib.so 链接别名校验指向签名 SONAME（glib 同款 PACKAGE_CODESIGN 流程）
4. `conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing`：通过，
   test_package 消费者测试（test_upower-glib + test_ohos 鸿蒙专项）真实运行通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson configure 报 `gio-unix-2.0 not found` | PkgConfigDeps 不生成 gio-unix-2.0.pc（glib 包内自带但未声明） | 复制 glib 包 pkgconfig 到 pc-fix 目录并 prepend pkg_config_path（见上） |
| 2 | configure 报 `Package proxy-libintl was not found` | glib 安装 .pc 带 proxy-libintl/zlib/libpcre2-8 私有 Requires，PkgConfigDeps 不生成传递依赖 .pc | pc-fix 剥离虚假 Requires + Requires.private（glib-networking 同款） |
| 3 | gnome.gdbus_codegen 找不到 gdbus-codegen | meson gnome 模块回退到 gio-2.0.pc 的 gdbus_codegen 变量 | gio-2.0.pc 注入 `gdbus_codegen=<glib_pkg>/bin/gdbus-codegen` |
| 4 | 消费者测试运行报 `Error loading shared library libupower-glib.so.3: Permission denied` | OHOS musl 加载器拒绝带无效 .codesign 占位段的共享库（ld.lld 链接时自动加占位段） | package() 用 binary-sign-tool 对安装 ELF 签名（PACKAGE_CODESIGN=PASS） |
| 5 | 测试二进制 `Error relocating ... up_device_kind_to_string: symbol not found` | 同 #4：库未被加载导致符号不可解析 | 同 #4，签名后 dlopen/链接运行全部正常 |
| 6 | 上游 `up_device_kind_to_string(COMPUTER)` 无法 round-trip | 上游 from_string 无 "computer" 分支（真实上游缺陷/行为） | 鸿蒙专项测试按实测上游行为断言（to_string→"computer"，from_string→UNKNOWN） |

## 依赖版本

- glib/2.88.3（ohpcd 已发布，W0 核验 `conan download glib/2.88.3 -r=ohpcd --only-recipe` 通过）

## 验证结果

- conan create（含 test_package）: EXIT 0；`upower-glib consumer test OK` 与
  `upower-glib OHOS specialty test OK` 均在 test() 内真实运行通过
- 上游 self-test（meson `test('self-test')` / up_self_test）: EXIT 0，6/6 ok
  （/power/backend、/device、/device_list、/history、/native、/daemon）
- 上游测试双口径: 全量声明 59（self-test 6 + integration-test.py 53），当前配置实例化 6，
  执行通过 6，通过率 6/59 (10.2%)；配置可执行集合 6/6 (100%)
- commands.json: archives/u/upower-glib/commands.json（type=tool，versions.ref=upower-glib/0.99.20，
  binary=false 待发布后置 true），随 PR 交付；构建产物含 bin/upower CLI 与 bin/upowerd
- ⚠️ 深度适配说明（R40）: upower 守护进程以 dummy 后端构建（OHOS 无 udev/gudev 硬件枚举层），
  客户端库 libupower-glib 的公开 API 在本平台实测可用；upower/upowerd CLI 依赖系统 D-Bus
  服务（本平台无 org.freedesktop.UPower 系统总线），运行时需 OHOS 侧提供 D-Bus 服务方可完整使用

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | meson 配方（glib pc-fix + OHOS ELF 签名） |
| conandata.yml | 官方源 URL + SHA-256 |
| test_package/ | 消费者测试 test_upower-glib + 鸿蒙专项 test_ohos（均在 test() 内执行） |
| commands.json | CLI 工具声明（bin/upower、bin/upowerd） |
| notes.md 内嵌 | 上游测试双口径台账摘要（59/6/6，详见下方） |

上游测试双口径台账（全量）:
- source_declared_total=59（self-test 6 个 g_test_add_func 用例 + src/linux/integration-test.py 53 个 unittest 方法）
- configured_executable_total=6（OHOS dummy 后端实例化的 up_self_test）
- executed_passed_total=6，失败=0，未实例化=53（integration-test 受上游
  `os_backend=='linux' and gobject_introspection.found()` 门控，属真实上游条件）
- 全量通过率: 6/59 (10.2%)；配置可执行集合: 6/6 (100%)
- 完整映射链（源码声明/注册项 -> 预处理条件 -> 构建目标 -> meson 注册 -> 执行日志）:
  6 项 g_test_add_func（up-self-test.c:288-293，无宏门控）-> up_self_test 目标
  （src/meson.build:107 build_by_default:true）-> test('self-test', up_self_test)
  （src/meson.build:114）-> 实跑日志 .oh-executor/upower-glib-r01-upstream-selftest.log
  （SHA-256 f169d5a760a1bcdd227d630c49146bb405be63b0563860444aef1181899bd499）；
  53 项 integration-test 方法（integration-test.py:98+，unittest 类）-> 注册门控
  src/meson.build:132-145（os_backend=='linux' and introspection）-> OHOS dummy 后端未实例化
---

**编译结束**: 2026-09-19 03:03
**最终状态**: built
