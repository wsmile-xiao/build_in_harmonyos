# gsl

## 简介

GNU Scientific Library (GSL) 是一个面向 C / C++ 的数值计算库，提供特殊函数、线性代数、
随机数发生器、统计、插值、积分、FFT、常微分方程求解等大量数值例程。

## OHOS 适配要点

- 构建系统为 autotools；源码包自带的 `config.guess` / `config.sub` **不识别 HarmonyOS**，
  必须应用 `patches/0001-config.guess.patch` 与 `patches/0002-config.sub.patch`，
  才能用 `--host=aarch64-unknown-linux-ohos` 配置（详见各版本的 `notes.md`）。
- `make` 必须 `-j1`：鸿蒙 SELinux 禁止 automake jobserver 的并行 FIFO。
- `libgsl.so` 把 CBLAS 符号留给消费方解析，**消费时必须同时链接 `-lgsl -lgslcblas`**；
  只 `dlopen("libgsl.so")` 会报 `cblas_sdsdot: symbol not found`。
- 本机动态加载器不跟随符号链接解析 `DT_NEEDED`，安装出的 `libgsl.so.25 -> libgsl.so.25.1.0`
  这类软链在运行期会加载失败；部署或跑测试时需把 `.so` 名字摊平成实体文件。

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 2.8 | built | conan 配方；显式 `--build/--host=aarch64-unknown-linux-musl` 跳过 config.guess，无需补丁 |
| 2.7 | built | conan 配方；走 `config.guess` / `config.sub` 平台识别补丁（上游骨架既定方案） |

## 依赖

无第三方依赖（只依赖 libc / libm）。

## 命令行工具

- `gsl-histogram` — 从标准输入读数值并输出直方图
- `gsl-randist` — 生成指定分布（gaussian / poisson / …）的随机样本表

## 消费示例

```bash
# conan 工程
conan install --requires=gsl/2.7 -pr ohos-aarch64
```

```c
#include <gsl/gsl_sf_bessel.h>
/* 链接：-lgsl -lgslcblas -lm */
```

## 测试

| 层级 | 内容 | 实测 |
|------|------|------|
| 上游测试套件 | `make check`（Automake parallel test harness，55 个目录） | 59/59 通过（0 失败 / 0 跳过） |
| 鸿蒙消费者用例 | `test_package/consumer.c` 的 HC-1..HC-6（sf / linalg / rng / statistics / blas / histogram），由 `test_package/test.sh` 逐字比对实测值与参考值 | 6/6 通过 |

各版本的用例明细与参考值来源见版本目录下的 `notes.md`（其中含 R51 上游测试申报表与 `test_package` 鸿蒙消费者用例明细）。

## 参考

- https://www.gnu.org/software/gsl/
