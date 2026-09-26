# DRAFT-E666 — ohpcd 制品仓 FFTW3 只有双精度构建，依赖单精度 fftw3f 的包在 configure 直接失败

- **来源任务**: `feat/minimodem-0.24`（积分赛）
- **关联草稿**: `knowledge/drafts/DRAFT-E666-minimodem-0.24-fftw3f-single-precision-unavailable.kv`
- **状态**: 草稿（待审核 promote 为 E666）

## 一句话

FFTW3 按“同一份源码 + 不同 configure 开关”分别出单/双精度两套库：单精度要
`--enable-single`，产物 `libfftw3f` + `fftw3f.pc`，API 前缀 `fftwf_*`。ohpcd
制品仓的 fftw 全系（3.3.10 / 3.3.10.1 / 3.3.10.2 / 3.3.10.3 / 3.3.11）都只有
双精度构建，于是上游写死 `PKG_CHECK_MODULES(DEPS, [fftw3f sndfile])` 的包
（minimodem 0.24 实证）在 configure 阶段即失败。

## 实测证据（minimodem 0.24，2026-09-22）

- 制品仓清单：`conan list -r=ohpcd "fftw/*"` → 6 个版本（2.1.5 + 5 个 3.3.x）。
- 逐版本读配方 configure 参数：5 个 3.3.x 全部无 `--enable-single`；
  `fftw/3.3.10.3` armv8 二进制包内 `lib/pkgconfig/` 只有 `fftw3.pc`，
  `lib/` 只有 `libfftw3.so`（conan download 实查）。
- `fftw/2.1.5` 虽是 float 构建（`--enable-float --enable-type-prefix`），
  但属 FFTW2 API（`sfftw_*`/`fftw_real`），与 FFTW3 的 `fftwf_*` 不是同族 API。
- 上游失败形态：`configure: error: Package requirements (fftw3 sndfile)` 之前
  的 pkg-config 报错 `Package 'fftw3f', required by 'virtual:world', not found`
  / `No package 'fftw3f' found`。

## 修法（主方案：机械精度替换补丁）

minimodem 0.24 的用点集中在 `src/fsk.{h,c}` + `configure.ac` 三个文件：

1. `deps_packages="fftw3f"` → `"fftw3"`（configure.ac）；
2. `fftwf_malloc/free/execute/destroy_plan/plan_many_dft_r2c` → `fftw_*`，
   `fftwf_complex` → `fftw_complex`，`fftwf_plan` → `fftw_plan`；
3. 变换缓冲 `float *fftin` → `double *fftin`、`fftwf_complex *fftout` →
   `fftw_complex *fftout`；两处样本喂入的 `memcpy(..., sizeof(float))` 改为
   逐点循环赋值（float 样本 → double 缓冲），`bzero`/`sizeof` 同步改；
4. 幅值侧保持上游原精度口径（`band_mag()` 返回 float），测试阈值语义不变。

替换完成判据：`grep -rn fftwf_ src/` 零命中。补丁随配方
`patches/0001-fftw-double-precision.patch` 交付。

**结果**：采信轮干净构建实测——上游 28 个用例 TOTAL 28 / PASS 28 / FAIL 0
（含 amplitude / noise / rate-slop 阈值类），test_package 消费者 300 波特 WAV
往返 510 字节逐字节一致、`--version` 自报正常。双精度 FFT 精度只增不减，
阈值类测试不受反向影响。

## 反模式（禁止）

- **只做 `.pc` 别名**（`pkg_config_aliases` 把 fftw3f 桥到 libfftw3）：
  configure 绿、链接期 `fftwf_*` 全部 undefined symbol。别名只解决 .pc 文件名，
  解决不了符号集（与 libaudec 对 samplerate 的命名桥接不同：那是同名库别名，
  这是不同精度的不同符号集）。
- **拿 `fftw/2.1.5` 当 float 替代**：FFTW2 API 代际不匹配，头文件+链接双失败。

## 可复用判别命令

```sh
# 制品侧：确认无单精度构建（期望只有 fftw3.pc）
conan list -r=ohpcd "fftw/*"
find ~/.conan2/p -path "*fftw*" -name "*.pc"

# 源码侧：确认上游用点面（决定主方案 vs 捆绑构建）
grep -rn "fftw3f" <包源码>/ --include=configure.ac
grep -rln "fftwf_" <包源码>/
```
