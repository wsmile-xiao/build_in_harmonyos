# dieharder 3.31.1.4 — 鸿蒙 PC conan 制品

`os=OHOS, arch=armv8`(= aarch64) 的 conan 包：`libdieharder.so.3` + `dieharder` CLI，
随机数发生器统计测试套件（Diehard 电池 + RGB/STS/DAB 测试，共 31 个内置测试模块）。

## 出包（鸿蒙 PC CI）

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

> 源码由 `conandata.yml` 的 url 在 `conan create` 时下载并 sha256 校验（`source()` 用 `get()`）。
> 官方 tag 归档：https://github.com/eddelbuettel/dieharder/archive/refs/tags/3.31.1.4.tar.gz

## 依赖

- `gsl/2.8`（仓内 conan 包）：configure 硬检查 `gsl/gsl_sf_gamma.h`，
  `libdieharder_la_LIBADD = -lgsl -lgslcblas -lm`。
- **必须同时链 `-lgsl -lgslcblas`**：libgsl.so 把 CBLAS 符号留给消费方解析（同 gsl 包注意事项）。
- **消费方全局符号契约**：libdieharder.so 把 CLI 专属全局状态（verbose/rng/dh_rng_types/
  dh_test_types/ks_pvalue 等约 50 个符号）留空由使用方提供——上游 CLI 用 dieharder/globals.c
  定义（gcc10 -fno-common 后的正式约定），R 接口 embeddieharder 同款；musl 立即绑定，
  dlopen 或漏定义会在加载期直接报 undefined symbol。test_package/test.c 内含完整定义块可抄。

## 使用（CLI）

```bash
dieharder -l              # 列出全部内置测试模块
dieharder -a              # 对默认生成器跑全部测试（小时级）
dieharder -d 0 -p 100     # 单跑 Diehard_Birthday
dieharder -g 201 -d 15    # 指定生成器与测试
```

上游没有 `make check`/ctest 目标——dieharder CLI 本身就是官方测试入口。
注意：个别统计测试对特定生成器报 WEAK/FAILED 属上游统计特性（见 man dieharder），
不是移植缺陷；CLI 退出码只反映"是否跑完"（正常结束=0）。

## 已知边界

- configure 内 `umask 077` 由 recipe build() 就地替换为 022（gsl 同款，未打 patch）。
- 上游 tarball 不带 config.guess/config.sub（上游靠维护者跑 autogen.sh，文件未入库）：
  已 vendor GNU config 项目 master 副本到 `patches/0001-add-config-guess-sub.patch`
  （新增文件补丁），configure 才能规范化显式 `--build/--host` 三元组。
