# libdicom 1.3.0 适配笔记

## 上游信息
- 上游项目: ImagingDataCommons/libdicom (C library for reading DICOM files)
- 版本: 1.3.0 (2024-02 发布)
- 许可证: MIT
- 构建系统: Meson (meson.build, meson >= 0.55)
- 官方源码: https://github.com/ImagingDataCommons/libdicom/releases/download/v1.3.0/libdicom-1.3.0.tar.xz（GitHub Releases 正式产物）
- SHA256: 75f1167f5153c659cdd58f2b432d2592bf0477abe0087e195bc621b5594ef10a
- 语言: 纯 C（lang-preflight 检测 c，任务语言 cpp，c↔cpp 兼容族通过）

## 适配内容
### 构建适配
1. 构建系统为 Meson：tool_requires meson/1.11.0（ohpcd 制品仓已有），MesonToolchain + PkgConfigDeps
2. 运行时依赖 uthash/2.3.0（header-only）：上游用 cc.check_header('utarray.h'/'uthash.h') 检测，Conan 包头文件经 MesonToolchain CFLAGS 注入即可命中，subproject wrap 兜底不触发
3. 测试依赖 check/0.15.2（test_requires）：PkgConfigDeps 生成 check.pc 供 meson dependency('check') 解析
4. llvm-ar/llvm-ranlib 注入 conan_meson_cross.ini（profile 只给了 clang 路径，跟随 libavtp/0.2.0 已验证方案）
5. 共享库（default shared）：meson install 产生 libdicom.so.1.3.0 + .so.1 + .so 符号链接链，HMDFS 软链不稳 → 物化为实体拷贝（R5）
6. 工具产物 dcm-dump / dcm-getframe 也一并安装到 bin/（库类型为主，无需 commands.json——R38 只对命令行工具类软件要求）

### 依赖
- 必需: uthash/2.3.0 (header-only)
- 测试: check/0.15.2 (Check 单元测试框架)
- 构建: meson/1.11.0 (Conan 工具包)

### 测试
- 上游测试: meson test → check_dicom（Check 框架，31 个 START_TEST 用例）
  - test_error, test_log_level, test_tag_validity_checks, test_vr_validity_checks,
    test_dict_tag_lookups, test_dict_vr_lookups, test_element_AE/AS/CS_multivalue/
    CS_multivalue_empty/DS/IS/ST/SQ/SQ_empty/UI/US/US_multivalue/US_multivalue_empty,
    test_sequence, test_dataset, test_file_sm_image_file_meta/metadata/frame/
    file_meta_memory, test_file_ct_brain_single, test_encapsulated_empty_BOT_1_to_1/
    2_to_1, test_encapsulated_defined_BOT_1_to_1/2_to_1/2_to_2
- 测试 fixture: data/test_files/*.dcm（7 个 DICOM 样本文件，SRCDIR 宏引用）
- 消费者测试: test_package 运行 test_libdicom 解析 sm_image.dcm（上游样例，
  以 base64 文本 sm_image.dcm.b64 随包携带——GitCode PR diff 无法携带二进制文件，
  .diff 端点对 binary 只输出 'Binary files differ' 无 patch 数据，CI checkout-pr
  的 git apply 会失败），验证 TransferSyntaxUID (0002,0010)、
  MediaStorageSOPClassUID (0002,0002)、metadata subset 遍历

### 关键踩坑与修复（本次适配实战经验）
1. **posix_spawn 不解析 PATH**（HarmonyOS CPython 因 SELinux 策略强制 subprocess 走
   posix_spawn 快速路径，musl posix_spawn 不做 PATH 搜索）：meson 的 ninja 检测
   （`ninja --version` 裸名 spawn）报 ENOENT → `Could not detect Ninja v1.8.2 or newer`。
   修复：conanfile `_inject_archive_tools()` 向 conan_meson_native.ini 的 [binaries]
   段注入 `ninja = '/data/service/hnp/bin/ninja'`（绝对路径），且 `_run_meson()` 给
   所有 meson 子命令加 `NINJA=绝对路径` 环境变量前缀（tooldetect 优先读 NINJA env）。
2. **LD_LIBRARY_PATH 脏项坑**：设备环境变量含空白项（`"         /system/lib64"`），
   musl loader 无法解析 → ninja（链接 libc++_shared.so）spawn 报 127 relocation 错误。
   修复：`_meson_environment()` 清洗 LD_LIBRARY_PATH（去空白项 + 补 /system/lib64）。
3. **meson tests 选项类型**：meson_options.txt 里 tests 是 boolean 类型，MesonToolchain
   传 `'true'/'false'`（不能传 enabled/disabled——那是 feature 类型语法）。
4. **check_dicom build_by_default: false**：meson test --no-rebuild 前必须显式
   `meson compile check_dicom` 构建测试目标。
5. **test_package 运行共享库程序**：conan `self.run(env=list)` 在 OHOS 不生效，
   用命令内联 `LD_LIBRARY_PATH=... ./test_libdicom`（acsccid/1.1.13 已验证方案）。
6. **HMDFS 符号链接**：meson install 产生 libdicom.so.1.3.0 → .so.1 → .so 链接链，
   物化为实体拷贝（R5）。

### 测试结果（2026-09-03 实测）
- 构建产物：19/19 meson 目标全部编译成功（libdicom.so.1.3.0 + dcm-dump + dcm-getframe + check_dicom）
- 上游测试（meson test → check_dicom，Check 框架）：
  `100%: Checks: 31, Failures: 0, Errors: 0`（31/31 用例通过，0 失败 0 错误）
  meson 汇总：`1/1 libdicom:check_dicom OK`
- 消费者测试（test_package/test_libdicom）：
  解析 ct_brain_single.dcm，TransferSyntaxUID=1.2.840.10008.1.2.1，
  MediaStorageSOPClassUID=1.2.840.10008.5.1.4.1.1.2，metadata subset 100 元素，PASS
- conan create 最终 EXIT 0

### 注意事项
- 上游 meson.build 有 doc/env/bin sphinx 自定义 target，meson install 不触发构建，无需处理
- conandata.yml 只写官方 GitHub Releases URL（R39：CI 自动加镜像 fallback，不手动加前缀）
- 本机为 HarmonyOS PC (aarch64)，构建与测试均在设备本地原生运行（native build）
---

**编译结束**: 2026-09-03 19:28
**最终状态**: built
