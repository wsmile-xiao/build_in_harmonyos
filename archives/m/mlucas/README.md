# mlucas（HarmonyOS / OpenHarmony aarch64）

Mlucas 是 Ernst W. Mayer 为 GIMPS（Great Internet Mersenne Prime Search）开发的开源程序，
对形如 2^p−1 的 Mersenne 数执行 Lucas-Lehmer 素性检验，另含 P−1 分解、费马数模平方检验
等高精度数论功能。它**自带全套 FFT/radix 实现，不依赖任何外部 FFT 库**。

## 功能概述

- Lucas-Lehmer 素性检验（Mersenne 数），支持按指数自动选取 FFT 长度
- 构建后自检（`-s t/s/m/l/...`）与单长度抽查（`-fftlen … -iters … -radset …`）
- 费马数模平方检验（`-f`）、P−1 分解（`-pm1`）、伪素数检验（`-pp`）
- 多线程（pthread）与 CPU 亲和性设置（`-cpu`）
- GIMPS 结果提交助手 `primenet.py`（本包未打包，见下）

## 安装

```bash
conan install --requires=mlucas/20.1.1 -pr:h=<ohos-aarch64 profile> -r=ohpcd
```

安装后得到 `bin/mlucas`。

## OHOS 适配

| 项 | 说明 |
|---|---|
| 构型 | `nosimd`（scalar double）。上游 `makemake.sh` 无参时按 `/proc/cpuinfo` 自动选 SIMD 并附 `-march=native`，不可复现；Debian 在 arm64 上也只启用 `generic-c` |
| 补丁 1 | `src/platform.h`：`<sys/sysctl.h>` 改为 `__has_include` 探测（musl 无此头文件，且 `__GLIBC__` 未定义时上游条件取值为真） |
| 补丁 2 | `src/threadpool.c`：线程亲和性代码限定 `__GLIBC__`（`cpu_set_t`/`sched_setaffinity` 为 glibc 扩展），非 glibc 平台按上游 OpenBSD 分支的做法交给 OS |
| 平台宏 | 两处补丁均**不含** `__OHOS__` 等平台宏，按 C 库能力分支，glibc/BSD/macOS 行为不变 |
| 已知行为 | scalar 构型在接近各 FFT 长度推荐上限（`p/pmax_rec ≈ 0.995`）的指数上圆整误差裕度较小，自检会跳过部分 radix-set；小 FFT 长度另有 `radix < 16 do not support shifted residues` 的上游限制。均非适配缺陷 |

## 依赖关系

| 类型 | 依赖 | 说明 |
|---|---|---|
| 编译期/运行期 | `gmp/6.3.0` | 唯一强制第三方库（`src/Mlucas.h:47 #include <gmp.h>`；上游 `makemake.sh` 链接 `-lgmp`），以静态库链接 |
| 系统自带 | libc、libm、pthread、librt | OHOS musl 提供；产物 `readelf -d` 仅 `NEEDED libc.so` |
| 未打包 | `primenet.py` | 上游 GIMPS 提交助手，需 Python3 运行时；为保持包自包含未纳入 |

## 参考资料

- 上游仓库：https://github.com/primesearch/Mlucas
- 上游说明：https://www.mersenneforum.org/mayer/README.html
- 发行说明 / 命令行手册：源码树内 `help.txt`
