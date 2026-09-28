# fft-c 3356ecd87d — 适配笔记

## 概览

- 上游：https://github.com/adis300/fft-c（commit 3356ecd87d，无 tag）
- 类型：纯 C 单文件库（fft.c + fft.h），FFTPACK 的易用封装
- 构建系统：上游无（仅演示 Makefile 目标 `example`）；配方自定义编译
- 依赖：无第三方库（仅 libm）
- 适配产物：libfft_c.a / libfft_c.so + fft.h，Conan 配方 + test_package + 鸿蒙专项测试

## 关键问题与处理

### 1. 上游 fft_backward 双重缩放 bug（已补丁修复）

- 现象：FFT_SCALED_OUTPUT 下 `fft_forward` + `fft_backward` 往返结果 = n×原信号。
  实测：impulse 往返 y[0]=1024（n×1）。
- 根因：`__fft_real_backward`（FFTPACK rfftb）是非归一逆变换，
  `rfftb(rfftf(x)) == n*x`；`fft_backward` 又在 SCALED 模式下对结果乘 n，
  与 `fft_forward` 的除 n 叠加成双重缩放。
- 修复：`patches/0001-fix-fft-backward-double-scaling.patch` 删除反向的多余乘 n。
  修复后往返误差 <1e-14（9 组断言全绿）。
- 验证：test_package 与鸿蒙专项测试的 roundtrip 断言（未打补丁时 1.529e4 失败，
  打补丁后 7.1e-15 通过）。

### 2. rfftf 输出排布（非标准，消费方注意）

- 实测排布：`out[0]=R0(DC)`，`out[N-1]=R_{N/2}(Nyquist)`，
  对 `1<=k<=N/2-1`：`out[2k-1]=R_k`，`out[2k]=I_k`。
- 与 netlib 标准排布（`[R0, R_{N/2}, R1,I1, …]`）不同；按 `out[2k], out[2k+1]`
  取 bin 会错位（15Hz 余弦会读成 0）。本库的测试与 test_package 均按实测排布取 bin。

### 3. codeload URL 无扩展名（配方的坑）

- 上游归档 URL（`/tar.gz/<commit>`）无 `.tar.gz` 扩展名，conan `get` 默认按 zip
  解压 → `BadZipFile`。配方显式声明 `filename: fft-c-3356ecd87d.tar.gz` 解决
  （aes-stream 同款经验）。

### 4. 共享库需 DT_SONAME

- W3 L5a 门禁：libfft_c.so 缺 DT_SONAME 会被拦截（无 SONAME 时下游链接器把
  绝对路径写进 DT_NEEDED，烤死包目录哈希）。配方共享库链接加
  `-Wl,-soname,libfft_c.so` 后通过。

## 基线隔离复验（W3 junk_check 命中其他库基线文件）

W3 的 junk_check 在 full 模式（git ls-files）下命中 4 个**提交前已存在**于
origin/main 的其他库基线空文件（非当前库、非框架文件）：

- `archives/c/cloog/0.21.1/.build-closed`（来自 cloog PR 906cc59ae7）
- `archives/c/cloog/0.21.1/.staging-verified`
- `archives/k/kics/2.1.20/.staging-verified`
- `archives/t/thc/3.8/.staging-verified`

按规程临时隔离（`git rm --cached` + 移出 worktree）、复跑 W3、原样恢复，
恢复后 SHA-256 与隔离前一致（均为空文件 e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855）。
这些路径未进入本库 diff/staged/PR。详见最终回报的 baseline_isolation_audit 逐项记录。

## 测试统计（双口径）

- 上游测试声明总数 `source_declared_total`：**0**（无测试框架/测试宏/测试目标；
  example.c 为样例，不计入用例——全量枚举台账见 `reports/upstream_test_ledger.md`）
- 当前配置可执行集合：0；执行通过：0；通过率：**0/0**（分母为 0，无未运行/未实例化项）
- test_package：9 组数值断言全过（频谱 bins 2/15、DC、泄漏、往返、HANNING 窗、cosq）
- 鸿蒙专项测试：9 组数值断言全过（`test_ohos/ohos_fft_test.c`，exit 0）
- 消费者用例：`test_consumer/`（主导频率检测场景，基于已安装包编译链接运行，exit 0）

## 验证环境

- 工具链：`/data/service/hnp/bin/clang` 15.0.4（target `aarch64-unknown-linux-ohos`）
- Conan：2.29.1（OHOS 适配版），profile `ci/conan/profiles/ohos-aarch64`
- W0 依赖预检：无依赖，通过；R37：fft-c/3356ecd87d 未占用制品仓版本

## 编译结束

本版本已完成构建、验证与归档收尾（status: built）。
---

**编译结束**: 2026-09-27 04:47
**最终状态**: built
