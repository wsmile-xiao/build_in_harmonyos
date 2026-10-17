# atracdenc 0.2.3 适配笔记

## 构建配置

- 分支：`feat/atracdenc-0.2.3`
- 构建系统：CMake（C++17 / C11）
- 包类型：application（`bin/atracdenc` 命令行工具）
- 依赖：libsndfile/1.2.2（pcm_io_sndfile.cpp 链接 libsndfile）、gtest/1.17.0（测试）
- 源码：GitHub release `dcherednik/atracdenc` tag 0.2.3，
  sha256 `c2668c2cefb20722341f4a03370f4c7e8fe196c6b0e0c5ef7ab13fc5ffe6ae1a`

## OHOS 适配要点

1. **CMAKE_SYSTEM_NAME=Linux（E092）**：CMake 无 HarmonyOS 平台模块。上游顶层
   CMakeLists.txt 用 `if (UNIX)` 包住 `find_package(GTest)` + `add_subdirectory(test)`
   + `enable_testing()`，若不设 Linux 则测试分支不启用、无测试可跑。generate()
   中强制 `CMAKE_SYSTEM_NAME=Linux`，触发 UNIX 分支。

2. **man page gzip 兼容（补丁 0001-man-page-gzip.patch）**：上游
   `gzip --no-name --to-stdout` 使用 GNU 长选项，OHOS 的 toybox gzip 仅支持短
   选项，且 gzip 可能缺失。补丁改为 `find_program(GZIP_EXECUTABLE gzip)` +
   `${GZIP_EXECUTABLE} -c`，并整体包进 `if (GZIP_EXECUTABLE)`，gzip 缺失时跳过
   man page，不影响二进制安装。

3. **上游测试接入**：上游 release tarball 自带 gtest 测试（test/CMakeLists.txt
   注册 6 个 gtest 可执行文件：atracdenc_ut、at3plus_pqf_ut、
   at3plus_bitstream_ut、at3plus_gha_ut、at3plus_mdct_ut、bs_encode_ut）。
   TEST 用例审计：src/ 下 `_ut.cpp` 共 80 个 `TEST(`（atrac3denc_ut 6、
   atracdenc_ut 2、transient_detector_ut 1、util_ut 3、bitstream_ut 6、
   encode_ut 3、mdct_ut 10、atrac_scale_ut 1、at3p_bitstream_ut 6、
   at3p_gha_ut 28、at3p_mdct_ut 5、ipqf_ut 9）。
   build() 末尾执行 `ctest --output-on-failure -V -j1`，解析 gtest
   `[  PASSED  ] N tests` 输出累计，输出 `HMBS_UPSTREAM_TEST_RESULT` 标记；
   退出码非 0 或失败数 >0 时 raise。

4. **测试数据**：at3plus_pqf_ut 需要 `test_data/ipqftest_pcm_mr.dat` 与
   `ipqftest_pcm_out.dat`，均在 release tarball 内（test/CMakeLists.txt 通过
   configure_file COPYONLY 拷入构建目录），无需额外下载。

5. **libgha 子模块**：release tarball 已包含 `src/lib/libgha/` 完整内容
   （CMakeLists.txt + src/ + include/），无需 `git submodule update`。

## 验证

- 未提交工作树，等待 HMBS 真机预检（conan create + test_package + 上游测试）。
- 预期：`HMBS_UPSTREAM_TEST_RESULT` status=passed（80/80），
  `HMBS_TEST_PACKAGE_RESULT` discovered=2 passedCount=2。

## 下一步

- HMBS 同步未提交工作树执行真机预检，通过后统一提交推送。

## 本轮（真机预检 compile 失败修复：依赖解析到 conancenter 触发 cmake KeyError 'OHOS'）

- 失败阶段 compile，conan create 依赖图把 `libsndfile/1.2.2` 与 `gtest/1.17.0`
  解析到 **conancenter 的 CCI 配方**（预检日志：libsndfile 下载了 recipe revision
  `331a3bf2dc523194f5b4880ca807072a`），CCI libsndfile 的 tool_requires 拉入
  `cmake/4.4.2`，其 build() 读取 `conan_data["sources"][version][str(os)]` 时
  `KeyError: 'OHOS'`（conancenter cmake 配方无 OHOS 源码条目）→ 构建中止。
- 根因：预检 conan 环境 conancenter 与 ohpcd 均可用，同版本时 conancenter 优先；
  atracdenc 配方此前用无 RREV 的裸引用，依赖被解析到未适配的 CCI 配方。
- 修复（同 libgsf 经验 1）：requirements() 显式 pin 本仓已发布配方的 RREV，
  强制解析到 ohpcd 适配配方（已发布二进制，跳过源码构建，避开 cmake tool_require）：
  - `libsndfile/1.2.2#1b78b3490f71169ed12d0a25fa0daada`
  - `gtest/1.17.0#210a20e5a583106265b578ecdaef66dc`
- RREV 计算：conan 2.30 FileTreeManifest.summary_hash（md5 内容哈希 + md5 摘要，
  LF 规范化，导出文件集合 = conanfile.py + conandata.yml + export_source/patches/*）。
  算法已用已知 pin 值复核：freetype→7e95a2b2（graalvm/pycairo）、
  zlib/1.3.1.1→9a23e7d5（libgsf R45 ohpcd 实际值）、libpng→d25df07a（pycairo），
  本机计算全部命中；libsndfile/gtest 的 RREV 即按同一算法对本仓当前配方计算。
- readonly_tmp 提示（`preflight.sh[229]: can't create temporary file /tmp/...`）来自
  hmbs 包装脚本，非本配方（配方内仅 test_package/test.sh 使用 $TMPDIR，符合规范），
  失败根因以 ConanException（cmake KeyError 'OHOS'）为准，未改配方。
- 未提交，等待 HMBS 重新预检验证 RREV pin 是否解析到 ohpcd。

## 本轮（真机预检 compile 失败修复：RREV pin 值在 remotes 不存在）

- 失败阶段 compile：`ERROR: Package 'libsndfile/1.2.2' not resolved: Unable to
  find 'libsndfile/1.2.2#1b78b3490f71169ed12d0a25fa0daada' in remotes. Required
  by 'atracdenc/0.2.3'`（conancenter 与 ohpcd 均无此 RREV）。
- 根因：上一轮按 FileTreeManifest.summary_hash 算法**本地复算**的 RREV 与实际
  发布值不一致；cnb.cool 制品仓不支持同版本多 revision 并存，pin 到不存在的
  RREV 时依赖图直接解析失败。同 libgsf 经验 2：RREV 必须取 ohpcd 实测值。
- 修复（经验 2 应用）：调用 ohpcd conan v2 API
  `GET /v2/conans/{name}/{version}/_/_/revisions` 读取实际发布 RREV：
  - `libsndfile/1.2.2#cf6ded313ae8c9c830e5ec3d3a8ce497`（发布于 2026-08-20）
  - `gtest/1.17.0#ab1bc3bf51522490eef07a83c2dbd203`（发布于 2026-08-10）
  同步更新 conanfile.py requirements() 与 manifest.yaml dependencies；
  test_package 未引用 RREV，无需改动。
- 验证方法参照：libsndfile/gtest 均为本仓已合入适配配方（libsndfile 曾通过
  shadow CI），ohpcd 该 RREV 即为发布时的真实 recipe 内容。
- 未提交，等待 HMBS 重新预检：依赖解析成功后将进入 atracdenc 自身编译与测试。

## 本轮（真机预检 compile 失败修复：conandata.yml patches 格式错误导致补丁从未生效）

- 失败阶段 compile：`[  1%] Generating atracdenc.1.gz` → `gzip: Unknown option
  'to-stdout' (see "gzip --help")` → make 在 man-atracdenc target 报错。
  日志中 export_sources 只复制了 conandata.yml/conanfile.py，**没有任何
  '.patch' 文件复制行**，说明补丁在导出阶段就未生效。
- 根因：conandata.yml 的 `patches:` 段写成「补丁文件名为 key 的 dict」：
  ```
  patches:
    "0001-man-page-gzip.patch":
      patch_file: ...
  ```
  Conan 2.30 `apply_conandata_patches`/`export_conandata_patches`
  （conan/tools/files/patches.py）只接受两种形态：`{版本: [条目]}` dict 或
  直接 `[条目]` list。文件名作 key 会被当成版本 dict，查 `patches.get("0.2.3")`
  返回空 → 静默跳过导出与应用（不报错），构建仍跑上游原始命令
  `gzip --no-name --to-stdout`，OHOS toybox gzip 不认长选项 `--to-stdout` 而失败。
- 修复：改为仓库惯例的 list 格式（与 a52dec/aa3d 等已通过预检的配方一致）：
  ```
  patches:
    - patch_file: "patches/0001-man-page-gzip.patch"
      patch_description: "..."
      patch_type: "portability"
  ```
- 补丁本身（0001-man-page-gzip.patch）经本地 `git apply --check` 对上游
  CMakeLists.txt 验证可干净应用：`find_program(GZIP_EXECUTABLE gzip)` 保护 +
  `gzip -c` 短选项 + 整体包进 `if (GZIP_EXECUTABLE)`，gzip 缺失时跳过 man page。
- 依赖解析已正常（日志中 libsndfile#cf6ded31 与 gtest#ab1bc3bf 均按 pin 命中
  ohpcd），本轮仅剩补丁未生效问题。
- 未提交，等待 HMBS 重新预检。
