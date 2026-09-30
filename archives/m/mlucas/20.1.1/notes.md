# mlucas 20.1.1 适配笔记

## 软件与来源

| 项 | 值 |
|---|---|
| 软件 | mlucas 20.1.1（Mersenne 数 Lucas-Lehmer 素性检验，GIMPS） |
| 上游仓库 | https://github.com/primesearch/Mlucas （Ernst Mayer's Mlucas / Mfactor） |
| 源码 ref | commit `039e912fa7a246788c7a2c6b1a1f4c13485bbf23`（"Added files for mlucas v20.1.1."，2022-07-12）——该仓库没有 v20.1.1 标签，仅有 v21.0.1/v21.0.2 |
| 源码包 sha256 | `fd15734f9065dd41a20e9e8dd9a6420f46d37d070e57d1474bd4ce5987b46580`（两次独立下载一致） |
| 许可证 | GPL-3.0-or-later（上游仓库 license=GPL-3.0） |

## 编译环境

| 项 | 值 |
|---|---|
| 构建系统 | 上游 `makemake.sh`（生成纯 Makefile）→ `make` |
| 编译器 | clang 15.0.4（OHOS SDK，`aarch64-linux-ohos`，musl） |
| 目标 | OHOS aarch64，Release |
| 构件构型 | `nosimd`（scalar double，无 SIMD） |
| 依赖 | gmp/6.3.0（Conan 预编译静态库；唯一强制第三方库） |
| 日期 | 2026-09-29 |

## 编译步骤（真实命令）

```bash
# 1) 取源码 + 应用补丁（conanfile.py 自动完成）
conan create archives/m/mlucas/20.1.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 -r=ohpcd

# 2) 等效的手工步骤（探索期实际执行）
export C_INCLUDE_PATH=<gmp pkg>/include LIBRARY_PATH=<gmp pkg>/lib
CC=clang bash makemake.sh nosimd      # 生成 obj_nosimd/Makefile 并 make -j$(nproc)
# 产物: obj_nosimd/Mlucas_nosimd → 安装为 bin/mlucas
```

## 构型选择说明

上游 `makemake.sh` 在无参数时按 `/proc/cpuinfo` 自动挑 SIMD，并附带 `-march=native`
——在 CI/异构环境中不可复现。本配方显式传 `nosimd`（scalar double），与 Debian 在
arm64 上的选择一致（`debian/rules` 只启用 `generic-c`，`debian/changelog: disable simd
on arm64`）。x86 SIMD 与 `asimd` 构型本次不适配（前者非目标平台，后者需 `-march=native`）。

## 遇到的问题与解决方案

| # | 问题（首个真实错误） | 根因 | 解决方案 | 验证 |
|---|---|---|---|---|
| 1 | `../src/platform.h:1306:11: fatal error: 'sys/sysctl.h' file not found`（20 个 TU 全部命中，`grep -c "error:" build.log` = 20） | `platform.h:1302` 的条件 `#if defined(OS_TYPE_MACOSX) \|\| !defined(OS_TYPE_GNU_HURD) && ((__GLIBC__ < 2) \|\| (__GLIBC_MINOR__ < 30))`：OHOS 走 musl，`__GLIBC__`/`__GLIBC_MINOR__` 未定义 → 在 `#if` 中按 0 参与运算 → `(0 < 2)` 为真 → 进入 `#include <sys/sysctl.h>`；而该头文件是 glibc/BSD 专有，OHOS sysroot 中不存在 | 补丁 0001：把 warning+include 包进 `#if __has_include(<sys/sysctl.h>)`（能力探测，不改其他平台语义） | 该错误消失；`--` 全量重建 exit=0 |
| 2 | `../src/threadpool.c:324:3: error: use of undeclared identifier 'cpu_set_t'`（另有 `cpu_set` ×4，共 5 处） | `threadpool.c` 的 `#elif defined(OS_TYPE_LINUX)` 分支使用 `cpu_set_t`/`CPU_ZERO`/`CPU_SET`/`sched_setaffinity`，这些是 glibc 扩展，musl 不提供；OHOS 定义了 `__linux__` 因此命中该分支 | 补丁 0002：该分支条件收紧为 `OS_TYPE_LINUX && __GLIBC__`，并新增一个 `OS_TYPE_LINUX`（非 glibc）分支，按上游既有 OpenBSD 分支的做法把亲和性交给 OS | 该错误消失；`Mlucas_nosimd` 生成，`readelf -d` 仅 `NEEDED libc.so` |

> 两处修改均**未使用 `__OHOS__` 等平台宏**，而是按 C 库/头文件能力分支（`__has_include` 与
> `__GLIBC__`），对 glibc/BSD/macOS 的行为保持不变。

## 源码修改

补丁位于 `patches/`，由 `apply_conandata_patches()` 应用（`conandata.yml` 已声明）：

| 补丁 | 文件 | 修改 |
|---|---|---|
| `0001-src-platform.h.patch` | `src/platform.h` | 用 `__has_include(<sys/sysctl.h>)` 包住 `#warning` + `#include <sys/sysctl.h>`（+5 −0） |
| `0002-src-threadpool.c.patch` | `src/threadpool.c` | 亲和性分支限定 `&& defined(__GLIBC__)`；新增非 glibc 的 Linux 分支（+7 −1） |

## 依赖版本

| 依赖 | 版本 | 类型 | 可消费性 |
|---|---|---|---|
| gmp | 6.3.0 | 强制第三方库（构建+运行；`src/Mlucas.h:47 #include <gmp.h>`，`upstream/makemake.sh:159 -lgmp`） | `conan download gmp/6.3.0 -r=ohpcd --only-recipe` → exit 0；`conan install … --build=never` → `Package installed` |
| libc / libm / pthread / librt | 平台自带 | 系统库 | — |

> 产物 `readelf -d bin/mlucas`：`NEEDED libc.so` 仅一项（gmp 已静态链接进可执行文件），
> 因此运行期无额外 `.so` 依赖。

## 验证结果

### 1) 构建与门禁

```bash
conan create archives/m/mlucas/20.1.1 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=… -r=ohpcd
# exit=0（111s，含 build + package + test_package）
python3 scripts/ohc-run.py conan-verify mlucas 20.1.1
# → G0/G1/G2/G3/G4 + L2/L4/L5 全 PASS，exit=0
```

### 2) 上游测试（真实执行）

上游 GitHub 源码树不带 `tests/` 目录；官方 release tarball 附带的 3 个 autotools
check 脚本（`tests/spot-check`、`tests/fermat-test`、`tests/self-test`）正文即下列调用，
本次逐条在本机实际执行。**计数口径（与 `reports/test-report.md`、`test_package/MANIFEST.yml`
一致）**：上游 check-target **3**（`Makefile.am:22 TESTS=`，全部执行）→ 展开命令 **4**；
另补执行自检档 **1**（`-s t`，上游程序自带能力，不在 `TESTS` 清单）→ **实际执行命令总数 5，
通过 5 / 失败 0 / 跳过 0 / 漏测 0**。未执行且不在 `TESTS` 清单：`-s l/all/xl/xxl`（各需 10 小时~数天）。

| 用例 | 命令 | 结果 | 耗时 | 日志 |
|---|---|---|---|---|
| spot-check | `mlucas -fftlen 192 -iters 100 -radset 0` | exit 0，`Res64: 71E61322CCFB396C` | 2s | `logs/uptests/01-spot-check.log` |
| fermat-test #1 | `mlucas -fftlen 1024 -f 24 -iters 100` | exit 0，`12 of 12 radix-sets … passed` | 41s | `logs/uptests/02-fermat-test.log` |
| fermat-test #2 | `mlucas -fftlen 1024 -radset 4 -f 24 -iters 1000` | exit 0 | 37s | 同上 |
| self-test（tiny） | `mlucas -s t` | exit 0，32 个 FFT 长度中 15 个写入 cfg | 21s | `logs/uptests/03-selftest-tiny.log` |
| self-test（medium） | `mlucas -s m -cpu 0:3` | exit 0，16/16 FFT 长度全部写入 cfg 条目 | 761s | `logs/uptests/04-selftest-medium.log` |

### 3) test_package

`conan create` 内自动执行：OHOS 产物断言（aarch64 小端 ELF + OHOS musl 解释器）+
复现 spot-check 并校验 `Res64`，全部通过（`✅ mlucas spot-check OK`）。

## 注意事项

- **scalar 构型的圆整误差裕度**：自检在接近各 FFT 长度推荐上限（`p/pmax_rec ≈ 0.995`）
  的指数上会因 MaxErr 触顶而跳过部分 radix-set，小 FFT 长度还会因
  `radix < 16 do not support shifted residues` 被跳过——均为上游对 scalar/非 SIMD 构型的
  固有行为（上游自己提示 "PLEASE CHECK YOUR BUILD OPTIONS"），非本次适配缺陷；`-s t`
  中 32 个 FFT 长度有 15 个成功写入 cfg 条目，整体 exit=0。
- **仅打包可执行文件**：上游 `primenet.py`（PrimeNet 结果提交助手）需 Python3 运行时，
  未纳入本包，以保持包自包含（`bin/` 仅 `mlucas`）。

## 交付物

| 文件 | 说明 |
|---|---|
| `conanfile.py` | Conan 2 配方（application，requires gmp/6.3.0） |
| `conandata.yml` | 源码 URL + sha256 + 2 个补丁声明 |
| `patches/0001-src-platform.h.patch` | sysctl 头文件能力探测 |
| `patches/0002-src-threadpool.c.patch` | 亲和性代码限定 glibc |
| `test_package/{conanfile.py,test.sh,MANIFEST.yml}` | OHOS 产物断言 + 上游 spot-check 复现 |
| `manifest.yaml` | 版本级元数据 |
---

**编译结束**: 2026-09-29 17:37
**最终状态**: built
