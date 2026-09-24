# libaudec 0.3.4 适配笔记

## 编译环境
- 构建系统: meson（tool_requires: meson/1.11.0 + ninja/1.12.1，设备无 ambient meson）
- 编译日期: 2026-09-21
- 编译器: clang（OHOS SDK，/data/service/hnp/bin/clang）
- 状态: built（O5：release upload 确认前不标 published）

## 上游形态（W0 实况）

libaudec 是 Zrythm 项目的音频解码/重采样封装库。v0.3.4 的 meson.build
通过 pkg-config 解析 `sndfile`（>=1.0.25）与 `samplerate`（>=0.1.8），
另有 CMake subproject 兜底（subprojects/*.wrap，本适配不触发：
MesonToolchain 默认 wrap_mode=nofallback，且两个依赖 ohpcd 均已发布）。
任务卡提示的 ffmpeg/glib 依赖不成立：ffmpeg 后端（src/ad_ffmpeg.c）被
上游注释，mp3 走捆绑的 minimp3 头文件库；全无 glib。

## 适配要点

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 `both_libraries()` 无视 default_library，连带构建 libaudec.so | ohpcd libsamplerate/0.2.2 静态库非 PIC（llvm-readelf -r：src_sinc.c.obj 含 31 处 R_AARCH64_ABS64 绝对重定位），链入 .so 必被 lld 拒绝 | patch 0001：`both_libraries(` → `static_library(`，meson.build 与 tests/meson.build 两处 `audec.get_static_lib ()` → `link_with: audec`（static_library 对象无该方法，首轮采信轮实测报 `Unknown method "get_static_lib" in object <StaticLibraryHolder>`）；R26 静态交付，`audec` CLI 仍安装 |
| 2 | meson `dependency('samplerate')` 找不到依赖 | conan 的 libsamplerate 包未设 pkg_config_name，PkgConfigDeps 只生成 `libsamplerate.pc` | generate() 里 `pc.set_property("libsamplerate", "pkg_config_aliases", ["samplerate"])` 生成别名 .pc |
| 3 | meson 解析不到 conan 依赖 .pc | Conan 不自动把 generators 目录注入 PKG_CONFIG_PATH（实测 conanbuildenv 无该变量） | build() 用 `conan.tools.env.Environment` 显式 `prepend_path("PKG_CONFIG_PATH", self.generators_folder)` |
| 4 | 设备/worker 无 ambient meson；worker 导出 llvm-* 裸名使 meson 报 "Unknown linker(s): llvm-ar"（at-spi2-core 同根因） | meson 机器文件需要绝对工具路径 | `tool_requires("meson/1.11.0")`+`ninja/1.12.1`；pop AR/AS/STRIP/NM/RANLIB 后把 `shutil.which` 绝对路径写入 tc.ar/as_/strip/binaries |
| 5 | meson install 改写 RUNPATH 破坏链接器自签 .codesign，加载报 EPERM（E077） | OHOS 对 install 后被改写的 ELF 拒绝加载 | `_resign_elf()`：llvm-objcopy 剥 `.codesign` 后用 SDK binary-sign-tool 重签（at-spi2-core 同款） |
| 6 | OHOS 无 /var/tmp、根只读 | 构建工具写临时目录失败 | build 环境把 TMPDIR/TMP/TEMP 指到 build 目录内 tmp/ |

## 依赖版本

- libsndfile/1.2.2（ohpcd，fPIC=True，OS=OHOS/arch=armv8/Release 二进制在场）
- libsamplerate/0.2.2（ohpcd，shared=False 二进制在场；静态库非 PIC 是要点 #1 的根因）
- 工具: meson/1.11.0、ninja/1.12.1（ohpcd，OHOS 二进制在场）

## 测试

- 上游 3 项（tests/meson.build 注册，`meson test` 运行）：wav_test、
  mp3_test、log_test；计数口径与断言明细见 test_package/MANIFEST.yml。
- 鸿蒙消费者 1 项（test_package/test_audec.c，12 项断言）：运行期合成
  WAV，覆盖 finfo/open/read 恒等解码 + libsamplerate 下采样。
- 采信轮实测数字在验证完成后回填 manifest.yaml 与 reports/test-report.md。

## 注意事项

- 版本级 `knowledge_gained` 已按行尾 `# knowledge_ref:` 形态引用路径 B
  草稿 E644/E645。
- 交付物为静态库 `lib/pkgconfig/audec.pc` + `include/audec/audec.h` +
  `bin/audec`（CLI）；消费者静态链接时需连带 libsndfile/libsamplerate
  （cpp_info.requires 已声明）。
