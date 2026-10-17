# gst-plugins-bad 1.28.3 verification report

## Environment

- OpenHarmony/HarmonyOS PC aarch64
- Clang 15.0.4 (aarch64-unknown-linux-ohos), ld.lld 15.0.4
- Conan 2.29.1 (OHOS adapted), profile: ohos-aarch64
- Meson 1.11.1, ninja 1.13.1

## Verification

- `conan create` (ohos-aarch64 profile, `--build=missing`): exit 0
  - 955+ build targets (gst-plugins-bad + vendored gst-plugins-base subproject)
  - meson install + 132 pristine build artifacts restored (OHOS ELF signature
    protection, see notes.md)
  - package created: lib/ 88 files (17 bad libs + base libs + SONAME symlinks),
    lib/gstreamer-1.0/ bad+base plugins, include/gstreamer-1.0/ headers, bin/ tools
- `conan-verify` (G0-G4 + L2/L4/L5): PASS
- W3 local CI simulation (`CI_PACKAGES=... zsh ci/conan/build_and_test.sh`):
  exit 0 (L0 gates + conan create + test_package)
- W4 pre-PR audit: PASS (0 P0, 0 P1)

## test_package

Consumer test (R34-compliant, gst-libav pattern):

- Consumer binary links against all 17 packaged libraries via CMakeDeps
  (find_package + target_link_libraries) — validates headers, metadata, linking
- Runtime (loader maps all NEEDED libs — validates OHOS ELF signatures):
  - `readelf -d` SONAME assertions on libgstinsertbin-1.0 / libgstcodecparsers-1.0 /
    libgstwebrtc-1.0 / libgstvideo-1.0: 4/4 PASS
  - Plugin directory scan: > 10 plugin .so present (assertion PASS)
  - `readelf --dyn-syms` gst_plugin_acc* symbols in libgstaccurip.so: PASS
  - `dlopen("libgstinsertbin-1.0.so.0", RTLD_NOW|RTLD_LOCAL)`: PASS
  - `dlsym("gst_insert_bin_new")`: PASS
- 测试断言: 7 (4 SONAME + plugin count + plugin symbols + dlopen/dlsym run)
- 通过: 7 / 失败: 0

## 上游测试情况（R51）

- 上游 `tests/check/` 套件（GStreamer check 框架，数百个用例）按仓库惯例禁用
  （`-Dtests=disabled`，与已发布的 gstreamer/1.28.3、gst-libav PR #4373 配方一致）。
  根因：check 框架运行需 GST_PLUGIN_SCANNER fork 子进程与完整插件注册，OHOS 上
  消费端 gst_init() 因静态 glib/gstreamer 副本类型注册表冲突死锁（实测复现，见
  notes.md 问题 6），无法在 conan create 环境内执行。
- 等价覆盖：test_package 以链接 + loader 签名校验 + dlopen/dlsym + readelf 结构
  校验覆盖包的可消费性；插件级运行时行为（gst-inspect/pipeline smoke）待动态链接
  版 glib2/gstreamer 发布后可补充（R40 需人工确认适配完整性，已在 PR 描述声明）。

## Result

配方在 OpenHarmony PC aarch64 环境验证通过（built），等待 PR 合并后由 release
流水线发布到制品仓。
