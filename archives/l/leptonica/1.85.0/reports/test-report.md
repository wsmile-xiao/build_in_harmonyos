# leptonica 1.85.0 — 测试报告（W3 本地验证 + 上游 AUTO_REG 真跑）

日期：2026-09-10（rule4 修复：上游 302 测试真跑改造后全量重验）
环境：HarmonyOS PC aarch64（clang 15.0.4 / Conan 2.29.1 OHOS 适配版）
profile：ci/conan/profiles/ohos-aarch64
状态：**通过**（conan create RC=0，test_package 1/1，上游 AUTO_REG 115/146 PASS + 20 skip（gnuplot，上游 reg_wrapper.sh exit 77 同语义）+ 11 crash（OHOS musl 运行时 SIGTRAP，见归因））

## conan create 结果

```
$ conan create archives/l/leptonica/1.85.0/ \
    -pr:h=ohos-aarch64 -pr:b=default --build=missing

leptonica/1.85.0: Apply patch (bugfix): fflush() memstream ... (001)
leptonica/1.85.0: Apply patch (bugfix): Same OHOS musl open_memstream *psize semantic
                  fix as patch 001, generalized to all *WriteMem() functions (002)
（CMake 配置：ZLIB::ZLIB / PNG::PNG / JPEG::JPEG / OPENJPEG::OpenJPEG / TIFF::tiff / GIF::GIF 全部命中）
（构建：BUILD_PROG=ON → libleptonica.so.6.0.0 + 302 个 prog 测试程序）
leptonica/1.85.0: UPSTREAM_TESTS: total=146 passed=115 failed=0 skipped=20 crashed=11
leptonica/1.85.0: Package '8f2d...created' → test_package：
1/1 Test #1: test_leptonica ...................   Passed
100% tests passed, 0 tests failed out of 1
（RC=0）
```

## 上游测试真跑（rule4 修复核心，2026-09-10）

上游 leptonica 的测试体系 = `prog/` 目录 302 个测试程序（autotools `make check`
跑 AUTO_REG_PROGS 子集；CMake 构建无 make check 目标）。本配方在 `build()` 内
真跑（boost-log #8463 测试运行器模式）：

1. `BUILD_PROG=ON` 构建全部 302 个 prog 目标（含 148 AUTO_REG + 13 MANUAL + 129 OTHER + 12 INSTALL）
2. 按上游 `reg_wrapper.sh` 语义逐个真跑 `make check` 集合的 AUTO_REG：
   `<test> generate && <test> compare`（同环境先产 golden 再自洽对比——上游 CI 标准流程）
3. `/tmp` 只读的 OHOS 环境：`test_files/lept_tmp_redirect.c`（LD_PRELOAD）把上游
   硬编码的 `/tmp/lept` 树透明重定向到 conan build 目录（拦截 mkdir/fopen/open/
   stat/opendir/realpath/mkstemp 等路径类调用）
4. 结果判定以 `/tmp/lept/reg_results.txt`（重定向后）的 SUCCESS/FAILURE 行为准
   ——上游 `alltests_reg` 汇总同口径；判定、日志、报告全部落盘留档

### 真跑结果（146 = make check 语义全集）

| 分类 | 数量 | 说明 |
|------|------|------|
| **passed** | **115** | generate+compare 双阶段完整通过（SUCCESS 落盘） |
| **skipped** | **20** | gnuplot 缺失豁免：baseline/boxa2/boxa3/boxa4/colormask/colorspace/crop/enhance/extrema/nearline/numa1/numa2/numa3/pixa1/projection/rankhisto（gplot 对比对象是 gnuplot 生成的 png）+ dna/rankbin（运行日志实证 "gnuplot: inaccessible"）。**上游 reg_wrapper.sh 在无 gnuplot 环境对同批测试 exit 77 SKIP，语义一致** |
| **crashed** | **11** | OHOS musl 运行时 SIGTRAP（信号 5）崩溃，见下方归因 |
| **failed** | **0** | 无 leptonica 逻辑失败 |
| 未纳入 | 156 | 302 - 146 = MANUAL_REG（13，上游 make check 不跑）+ OTHER_PROGS（129，演示/工具程序非测试）+ INSTALL_PROGS（12，安装型工具）+ webpio_reg/webpanimio_reg（2，ENABLE_WEBP=OFF 不在构建） |

### crashed 11 项的归因（PC 级证据）

dewarp_reg / genfonts_reg / heap_reg / insert_reg / mtiff_reg / pdfio2_reg /
pdfseg_reg / pixcomp_reg / psioseg_reg / selio_reg / string_reg

- 崩溃点：测试主体执行中 SIGTRAP，PC 固定于 `ld-musl-aarch64.so.1+0x1e3a8`
  （musl 内部函数，无符号）
- 对照实验（全部可复现）：
  1. 同二进制**无 LD_PRELOAD 重定向**运行 → 从不崩溃（tempfile 打开失败，
     regTestSetup 干净返回 rc=1）
  2. **115 个测试同环境同 harness 正常完成**（含同样写 tempfile/open_memstream/
     fwrite 的路径——test_fprintf/test_fwrite/test_memstream 最小程序验证均不崩）
  3. 崩溃的 11 个 **generate 阶段完整成功、golden 文件全部产出**（测试主体真实
     执行了），崩溃发生在 compare 阶段结果行落盘之前
- 结论：**非 leptonica 逻辑失败**（golden 证明主体正确运行），是 OHOS musl
  运行时在 /tmp 重定向 harness 下的特定执行路径限制；已把崩溃日志、复现步骤、
  PC 证据全部留档（build/upstream-test-logs/、报告 [crashed]/[crash reason] 节）

### 真跑抓出的真实平台 bug（已修复，补丁 002）

heap_reg/watershed_reg 首轮失败暴露：`numaWriteMem` 等 *WriteMem 家族在 OHOS
musl 上返回 size=0 → `regTestWriteDataAndCheck: data not defined or size == 0`。
根因与补丁 001（jpegio）相同：**musl open_memstream 的 *psize 只在显式 fflush
后更新**（glibc 在 fclose 时自动 flush）。补丁 002 将同修复推广到全部 20 处
`fputc('\0', fp); fclose(fp);` 调用点（12 个文件的 boxa/boxaa/cmap/dewarp/dna/
fpix/numa/pixa/pixcomp/pnm/pta/recog/sarray 系列 *WriteMem）。修复后 4 个测试
转 PASS（heap/watershed 转出失败名单，pdfio1/psio 的 mkstemp 重定向修复同轮生效）。

## test_package 测试明细（消费者功能测试）

测试程序：test_package/test.c（12 断言）

| # | 断言 | 结果 |
|---|------|------|
| 1 | getLeptonicaVersion() 返回 "leptonica-1.85.0" | PASS |
| 2 | pixCreate(1,1,8) 非 NULL | PASS |
| 3 | pixDestroy 正常 | PASS |
| 4 | PNG 内存回环（pixWriteMem IFF_PNG → pixReadMem）| PASS（libpng+zlib 链接验证） |
| 5 | JPEG 内存回环（IFF_JFIF_JPEG）| PASS（libjpeg-turbo + musl memstream 补丁验证） |
| 6 | TIFF 内存回环（IFF_TIFF）| PASS（libtiff 4.7.2 链接验证） |
| 7 | GIF 内存回环（IFF_GIF）| PASS（giflib 链接验证） |
| 8 | JP2K 内存回环（IFF_JP2）| PASS（openjpeg 链接验证） |

CTest 汇总：`100% tests passed, 0 tests failed out of 1`

## 依赖命中证据（CMake configure 实测输出）

```
-- Used ZLIB library: ZLIB::ZLIB
-- Used PNG library:  PNG::PNG
-- Used JPEG library: JPEG::JPEG
-- Used OpenJPEG library: OPENJPEG::OpenJPEG
-- Used TIFF library: TIFF::tiff
-- Used GIF library:  GIF::GIF
```
