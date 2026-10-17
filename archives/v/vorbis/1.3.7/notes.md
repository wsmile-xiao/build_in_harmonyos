# vorbis 1.3.7 适配记录

## 任务背景（2026-09-16）

- 平台任务 #13473（taskBranch=feat/vorbis-1.3.7），`vorbis` 包名线。
- 与既有 `libvorbis/1.3.7`（archives/l/libvorbis/）**同一上游 tarball、不同包名线**，
  两者并存互不冲突——多包名先例同 ogg（archives/o/ogg/）与 libogg（archives/l/libogg/）。
- 依赖链：`vorbis/1.3.7 → ogg/1.1.1`（旧 ogg 包名线，PR #10038），对应 libvorbis 线的
  `libvorbis/1.3.7 → libogg/1.3.6`。

## Conan 配方（2026-09-16）

- 复用 libvorbis/1.3.7 已验证的 CMake 配方骨架，仅将依赖从 libogg/1.3.6 换成
  ogg/1.1.1，并把 0002 补丁的变量名沿用 `VORBIS_OGG_*`（补丁原样复用）。
- 上游 tarball 与 libvorbis 线完全一致（sha256 相同），两个 patch 与 libvorbis 线逐字节一致：
  - `0001-cmake-minimum-version.patch`：cmake_minimum_required 2.8.12 → 3.5
  - `0002-link-ogg-by-soname.patch`：以 `-L + -Wl,-l:libogg.so` 方式链接 ogg，
    避免 CMakeDeps IMPORTED_LOCATION 绝对路径写进 DT_NEEDED
- 导出 Conan 组件：`Vorbis::vorbis`、`Vorbis::vorbisenc`、`Vorbis::vorbisfile`
  （cmake_file_name 同为 Vorbis，与 libvorbis 线一致——同源码的导出目标名本来就相同）。

## 测试（N 实测口径）

- 上游 `test/Makefile.am` 注册 `check_PROGRAMS = test` → **N = 1 个上游测试程序**
  （编码/解码往返矩阵：1-8 声道 × 11 质量档（q-0.5~q9.5）× 6 采样率 = 528 个组合，全 ok）。
- 上游 CMake 构建不含 test/ 子目录 → 上游测试源码接入 test_package/ 在**安装后的库**上执行
  （libvorbis 1.3.7 同款先例）：`upstream/test.c + util.c + write_read.c`（与上游 tarball
  逐字节一致，diff 验证过）。
- test_package 消费者 smoke：`test_vorbis.c` 覆盖版本字符串、vorbis_encode_init_vbr、
  comment API、vorbisfile 符号链接。
- 本地实测（ohos-aarch64 profile，conan create）：exit 0，528/528 组合 ok，
  消费者 smoke 输出 `vorbis consumer smoke passed: Xiph.Org libVorbis 1.3.7`。

## 依赖发布状态（W0 卡点）

- `ogg/1.1.1` 前置钥匙 PR #10038 在本任务开工时**尚未 merge**（CI 绿 + AI 过 +
  review/test approved，等平台合并），制品仓暂无 ogg/1.1.1（conan download 与假包名
  同报"system acceleration policy not enabled" = 包不存在）。
- 本地验证用 #10038 分支配方 conan create 出本地 ogg/1.1.1 制品完成全链验证。
- **CI 依赖闸（L0i/PF4）会拦截未发布依赖**——PR 提交前必须等 #10038 merge +
  release 流水线发布 ogg/1.1.1 到制品仓。

## 编译环境

- 构建系统: cmake
- 编译日期: 2026-09-16
- 编译器: clang/clang++（ohos-aarch64 profile）
- 状态: built（本地 conan create + 上游测试 528/528 + 消费者 smoke 通过）
