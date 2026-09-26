# libtiff 4.7.2.1 编译笔记（HarmonyOS PC · Conan cmake）

## 产物
`libtiff.so`、`libtiffxx.so`（C++ 封装）。

## 编解码后端
八个后端全部接入，均由 conan 依赖提供（不依赖设备上预装的系统库）：

| 后端 | CMake 开关 | 依赖包 |
|------|-----------|--------|
| zlib | `-Dzlib=ON` | zlib/1.3.1.1 |
| libdeflate | `-Dlibdeflate=ON` | libdeflate/1.25 |
| JPEG | `-Djpeg=ON` | libjpeg-turbo/3.2.0 |
| Zstd | `-Dzstd=ON` | zstd/1.5.7 |
| WebP | `-Dwebp=ON` | libwebp/1.6.0 |
| LERC | `-Dlerc=ON` | lerc/4.1.1 |
| JBIG | `-Djbig=ON` | jbigkit/2.1 |
| LZMA | `-Dlzma=ON` | xz/5.6.2 |

## 关键适配
- 关掉不需要的构建目标：`-Dtiff-tools=OFF -Dtiff-tests=OFF -Dtiff-docs=OFF -Dtiff-contrib=OFF`。
- 产物 `.so` 经 `llvm-objcopy --remove-section .codesign` 去旧签名后由
  `binary-sign-tool sign -selfSign 1` 自签（HarmonyOS XPM 拒绝未签名/被改动的 ELF）。
- 无源码补丁。

## 状态
built —— 真机 `conan create` 通过。

## 上游测试套件实测（R51 三步法，2026-09-24 本机 aarch64 原生执行）

**清点**（源码 tiff-4.7.2.tar.gz 的 `test/` 目录）：52 个测试源文件/脚本（.c/.py/.sh/.cmake），
CMake ctest 注册 **158 项**（证据：构建目录 `ctest -N` 末行 `Total Tests: 158`）。

**运行**：本机即 aarch64（HarmonyOS/musl，clang 构建、原生执行），无需 qemu。
配方新增 conf 开关 `-c "user.libtiff:tests=ON"` → `-Dtiff-tests=ON -Dtiff-tools=ON`
（ctest 的 TIFF 读写比对测试依赖 tiffcp/tiffinfo 等 CLI 工具，必须同时开 tools），
`conan create --build="libtiff/*" -c "user.libtiff:tests=ON"` 后在构建目录跑
`ctest -j4 --output-on-failure`：

> **N=158 / N′=158 / 通过 M=158，通过率 100%**
> 证据行：`100% tests passed, 0 tests failed out of 158`（reports/ctest-run.log，
> Total Test time (real) = 4.84 sec）。逐项日志见 reports/ctest-run.log，完整 create 日志
> reports/conan-create-tests.log。

无失败项，无需逐项崩溃点说明。默认构建（不开 conf）仍为 `-Dtiff-tests=OFF
-Dtiff-tools=OFF`，测试产物不进发布包（已复验 rc=0，reports/conan-create-default.log）。

## 鸿蒙特有测试（test_package 补全，参考 zlib 1.3.2.1 PIC-DSO 探针 git 7839425281）

原 test.c 是空壳（dlopen+dlsym 无读写断言），已替换：

1. **test.c / test_probe** — 链接 libtiff 的消费者真实读写断言（R34）：对 **10 个
   COMPRESSION_* 后端**（NONE/LZW/DEFLATE/ADOBE_DEFLATE/JPEG/ZSTD/LZMA/WEBP/LERC/JBIG，
   覆盖 zlib 与 jpeg 两个必查后端）各写 32x16 图再 TIFFReadEncodedStrip 读回比对。
   实测要点（与上游一致的上游约束）：
   - WEBP 只支持 3/4 bands（"WEBP driver doesn't support 1 bands"）→ 用 RGB + 无损
     `TIFFTAG_WEBP_LOSSLESS`（有损实测 maxdiff=209 不可用）；
   - JBIG 无 scanline 编码（"ISO JBIG scanline encoding is not implemented"）→ 用
     TIFFWriteEncodedStrip + 1 bps 双值图；
   - JPEG 有损 → 容差比对（实测 maxdiff=13 ≤ tol 24）。
   运行输出：`PASS: all 10 codec backends roundtrip OK`（reports/test-package-run.log）。
2. **pic_probe.c + probe_main.c / probe_main** — 鸿蒙特有 PIC-DSO 探针（E539/E541 同法）：
   消费 libtiff 的真实读写代码以 `-shared -fPIC` 链成 DSO，readelf 校验无 TEXTREL、
   NEEDED 含 libtiff.so（证明真实链到被测包，非系统库 fallback——build() 同时显式校验
   包内 include/lib 路径存在，配 L1e 反向验证）；dlopen 运行器真实调用写图+逐行读回像素比对。
3. **test() 实际执行**（R34/PF3）：`self.run('./test_probe')` + `self.run('./probe_main')`，
   无 skip 分支。实测 rc=0（reports/test-package-run.log，conan test 全绿）。

声明数（test_package/MANIFEST.yml）：13 条断言（10 后端往返 + JPEG quality/tag 回读 +
DSO 无 TEXTREL + DSO NEEDED 校验 + DSO 像素往返）。

## 改动文件
- conanfile.py：build() 新增 `user.libtiff:tests` conf 开关（默认 OFF 不影响 CI）。
- test_package/test.c：空壳 → 10 后端真实读写断言。
- test_package/pic_probe.c、probe_main.c：新增鸿蒙特有 PIC-DSO 探针。
- test_package/conanfile.py：产物存在性自检 + 编译三个测试 + test() 实际执行。
- test_package/MANIFEST.yml：申报表回填。
- reports/：ctest-run.log、conan-create-tests.log、conan-create-default.log、
  test-package-run.log、upstream-test-verification.md。
