# minimodem

`minimodem` 是通用命令行软件 FSK 音频调制解调器：把任意数据用 Bell103/202、
V.21、RTTY、TDD、Caller-ID（MDMF/SDMF）、SAME 等波特模式调制为音频（或从音频
解调回来），支持 `--file` WAV 文件模式与实时音频后端。

## Versions

| Version | Status |
| --- | --- |
| 0.24 | built |

Homepage: https://github.com/kamalmostafa/minimodem

## OHOS 适配要点（0.24）

- 依赖：`libsndfile/1.2.2` + `fftw/3.3.10.3`（ohpcd 制品仓 armv8/OHOS 二进制）。
  制品仓 FFTW3 只有双精度构建，补丁 0001 将上游单精度 `fftw3f` 依赖与
  `fftwf_*` API 适配为双精度 `fftw3`/`fftw_*`（变换缓冲 float→double）。
- 可选音频后端缺省禁用：`--without-alsa --without-pulseaudio`；sndfile 后端
  保留（`--file` 模式）。
- 上游 28 个测试（tests/*.test）经 `make check` 全量真跑，全部为 WAV 文件
  往返，不需要音频设备；补丁 0002 修测试脚本解释器路径与 `/tmp` 只读问题。
