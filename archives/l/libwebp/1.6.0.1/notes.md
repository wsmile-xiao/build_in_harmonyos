# libwebp 1.6.0.1 — 鸿蒙 PC 适配 notes

> **R37 递增说明**：上游 1.6.0 配方已入官方 main（archives/l/libwebp/1.6.0）且制品仓已有
> libwebp/1.6.0（libtiff 4.7.2.2 的 WebP codec 依赖，CI 已消费），同版本重提交会被 L0j 409
> 拒绝。故以 1.6.0.1 递增版适配（制品 1.6.0.1 ↔ 上游 1.6.0，R37 解耦）。

## 定位
- 上游：webmproject/libwebp 1.6.0（BSD-3-Clause，cmake 构建）
- 产物：libwebp.so + libsharpyuv.so（libwebp.so DT_NEEDED sharpyuv，两库都必须暴露）
- 消费方：libtiff（WebP codec）、任意 WebP 编解码消费者

## 关键适配点
1. **OHOS 工具链自发现 + 裸 cmake**（glfw/libjpeg-turbo/zstd/libtiff 同法，ML-0035）：
   conf user_toolchain → OHOS_NDK_HOME → /data/service/hnp/ohos-sdk.org glob 三级兜底，
   绕开 conan_toolchain。
2. **版本化 soname 软链**：libwebp 构建产 libwebp.so.7 → libwebp.so 软链，HMDFS 禁 symlink
   （ln -s EPERM）→ 构建期 symlink 探针失败即 -DCMAKE_PLATFORM_NO_VERSIONED_SONAME=ON
   （单文件名 libwebp.so；E492 同类）。
3. **命令行工具全关**：WEBP_BUILD_{CWEBP,DWEBP,GIF2WEBP,IMG2WEBP,VWEBP,WEBPINFO,WEBPMUX,
   ANIM_UTILS,EXTRAS}=OFF，仅编库本体。
4. **.so 签名**：剥 .codesign + binary-sign-tool -selfSign 重签（cmake/SDK-toolchain 自签无效）。
5. **并行构建**：真机 make -jN 静默失败 → cmake --build --parallel 8。
6. **源码镜像**：官方 storage.googleapis.com 国内不可达 → Debian orig（与官方字节一致，
   sha256 互证，无 +dfsg）USTC/aliyun 双镜像（R39 合规干净镜像）。

## test_package 升级（1.6.0 空壳 dlopen 探针 → 功能 roundtrip 探针）
- 直接链接 -lwebp -lsharpyuv（消费方真实形态，验证 cpp_info.libs）
- 运行期版本断言：WebPGet{Decoder,Encoder}Version 返回三字节打包发行版号
  (MAJOR<<16)|(MINOR<<8)|REV（vp8_dec.c 实现，decode.h 注释 v2.5.7→0x020507），
  1.6.0→0x010600，与 ABI 版本 0x0210 是两套数
- 近无损 VP8 roundtrip（q=100，平滑图案，RGB/alpha≤8 容差）
- 无损 VP8L 专属 API（WebPEncodeLosslessRGBA + WebPDecodeRGB）逐字节
- 有损 RGBA roundtrip（q=75，RGB≤64/alpha≤32 容差）
- 容器解析正反例：WebPGetInfo/WebPGetFeatures 拒绝损坏数据、接受有效流
- 共 11 断言，全部依赖内建编解码器，任何构建下全绿（R34 反空壳）

### 探针图案设计两坑（Windows 本机 PIL 复现 + 真机双向交叉验证定位）
1. **alpha=0 像素被 alpha cleanup 改写**：VP8L 编码器对透明像素 RGB 不承诺保真
   （exact=0 默认下改写成左邻预测值以利压缩，实测 16x16 棋盘 2 个 alpha=0 像素被改写
   7，与真机首轮失败逐字节一致）→ 无损图案 alpha 取 128..255 段避 0。
   曾误判为真机 NEON 无损路径 bug，实为图案设计错误。
2. **VP8 q=100 仍是有损**：高频图案实测 RGB 偏差可达 134（真机首轮 (0,0) G +1 即此）
   → 逐字节断言必挂；近无损断言改用平滑渐变 + 容差 8（实测 ≤2）。

## 上游测试
- 上游 tests/ 共 22 文件 = 12 个 fuzz 目标 + fuzz_utils.cc（13 .cc）+ 4 头文件 +
  CMakeLists.txt/fuzz.dict/patch.sh/oss-fuzz/build.sh/README.md 5 件（git tag v1.6.0 树与
  官方发行 tarball 一致，已核对）
- 12 个目标均为 **FuzzTest 框架**体系（`FUZZ_TEST(...).WithDomains(...)`，非旧式
  libFuzzer 入口），需 google/fuzztest 运行时（依赖 abseil），OHOS 工具链无此运行时。
- **真机真实执行（rule4 修复，2026-09-28）**：以 `upstream_test_runner/`（随本 MR 提交）
  在真机执行上游 12 个被测函数——编译期 shim 中性化 FUZZ_TEST 注册宏与域构造，
  driver `#include` 上游 .cc 直接调用其被测函数（上游源码零改动，17/17 md5 互证）；
  上游树 + OHOS 工具链（复用 1.6.0.1 包 generators 的 conan_toolchain.cmake，
  clang 15.0.4）静态构建（huffman 等目标依赖 .so 不导出的内部符号 VP8L* 等，
  只能静态链接驱动）。**结果 12/12 PASS，330 次被测函数执行零崩溃**，与 x86 本机
  （MinGW g++ 13.2 独立构建）逐目标一致；种子语料 [sanity] 自检真实可解码。
  取证见 upstream_test_runner/device-results.txt。种子语料以 base64 文本入库
  (upstream_test_runner/seeds_b64/,平台 PR diff 管线不支持二进制补丁),build_run.sh
  在真机 python3 解码还原并打印 md5,与 seeds_md5.txt 互证。

## 验证
- 本地 L0 预检：通过
- 真机（2026-09-27，华为 PC，Conan 2.29.1）：conan-verify G0-G4/L2/L4/L5 全绿
  （G2 conan create 干净构建），探针 11/11 ALL GREEN —— 见 reports/conan-verify-report.md
- 真机（2026-09-28）：上游 12 个 fuzz 目标被测函数驱动执行 12/12 PASS（见上，330 次执行）
- 双向交叉验证：本机 PIL(libwebp 独立构建) 无损编码 16x16 参照流 → 设备 WebPDecodeRGBA
  逐字节精确；设备 WebPEncodeLosslessRGBA 流 → 本机 PIL 逐字节精确
