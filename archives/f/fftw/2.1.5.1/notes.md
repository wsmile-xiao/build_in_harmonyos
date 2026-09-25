# fftw 2.1.5.1 修复笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-19
- 编译器: clang 15.0.4 (OHOS SDK)
- 状态: built（conan-verify G0-G5 全 PASS，W3 本地 CI 100%）

## 编译步骤

```bash
# FFTW2 需以单精度 + s 前缀模式构建，产出 libsfftw/libsrfftw + sfftw.h/srfftw.h，
# 供 CCP4 clipper（fftmap.cpp include <srfftw.h>/<rfftw.h>）使用
./configure --prefix=$DEFAULT_PREFIX \
    --enable-float --enable-type-prefix \
    --disable-shared --enable-static \
    --disable-threads --disable-mpi
make -C fftw -j1
make -C rfftw -j1
make -C fftw install DESTDIR=$TEST_PREFIX
make -C rfftw install DESTDIR=$TEST_PREFIX
```

> 顶层 `make`/`make install` 会遍历 SUBDIRS 中的 doc/threads/mpi（即使禁用仍进入），
> 耗时极长。只构建/安装 fftw、rfftw 两个核心子目录即可满足下游（clipper）需求。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure: error: cannot guess build type` | 2003 版 config.guess 不认识 HarmonyOS（E007） | 用 autoconf 2.72 新版 config.guess/config.sub 替换后打 OHOS 补丁（0001/0002） |
| 2 | `config.sub: Kernel 'linux' not known to work with OS 'ohos'` | config.sub 内核列表缺 `linux-ohos*-`（E072 第3处） | 补丁脚本对新版语法（带 `-`）误判 skip，手工补 `linux-ohos*-` 条目 |
| 3 | `config.status: ./confstatXXXXXX/config.h: Permission denied` | config.status 用 `umask 077 && mktemp -d` 建 0700 临时目录，HMDFS 属主归一化后当前进程无法写入 | configure 补丁改为 `mkdir + chmod 775`（0003，组可写+其他只读；与 a52dec 0002 同因） |
| 4 | 顶层 make 反复超时 | SUBDIRS 遍历 doc/threads/mpi 极慢 | conanfile build/package 只对 fftw、rfftw 子目录操作 |
| 5 | test_package 链接 | FFTW2 符号保持 `fftw_*`/`rfftw_*` 前缀（type-prefix 只加在库文件名/头文件，不加在符号） | test.c 直接用 fftw_create_plan/fftw_one/fftw_destroy_plan |

## 源码修改

- `patches/0001-config.guess.patch`：config.guess 升级现代版 + HarmonyOS(aarch64-linux-ohos) 识别
- `patches/0002-config.sub.patch`：config.sub 升级现代版 + ohos-linux/ohos*/linux-ohos 三元组支持
- `patches/0003-configure.patch`：config.status 临时目录改为 mkdir+chmod（HMDFS 权限兼容）
- `patches/0004-Makefile.in-sed-source.patch`（2.1.5.1 修复）：fftw/Makefile.in 中 sfftw.h 生成规则 sed 源由 `$(srcdir)/fftw.h` 改为 `fftw.h`（build 目录相对路径）。因 conan out-of-source 构建时 `$(srcdir)/fftw.h` 指向源码目录的未配置模板（FFTW_ENABLE_FLOAT 未定义），导致发布包 sfftw.h 为 double 版与 float 库 ABI 不匹配（clipper SINGLE_FFTW2 检查失败）
- `patches/0005-fftw.h-float-template.patch`（2.1.5.1 修复）：源码模板 fftw/fftw.h 中 `/* #undef FFTW_ENABLE_FLOAT */` 改为 `#define FFTW_ENABLE_FLOAT 1`，强制单精度。因库源码（fn_*.c）以引号形式 `#include "fftw.h"` 优先解析到源码同目录模板（double），导致 conan 构建的库编译为 double 精度（反汇编确认 `fsub d4` 双精度指令）；修复后库为 float 精度（`fsub s4` 单精度指令）

## 依赖版本

- 无外部依赖（纯 C 库，零 requires）

## 验证结果

```bash
# 探索阶段真实执行：
cd tests
./fftw_test -c 16    # Testing correctness for n = 16...OK
./fftw_test -c 32    # OK
./fftw_test -c 64    # OK
./rfftw_test -c 16   # Testing correctness for n = 16...OK

# conan-verify 8 道门禁（G0-G5）全部 PASS
# W3 本地 CI 模拟：L0 PASS / L1 PASS / L5 PASS，Pass rate 100% (1/1)
# test_package：delta 脉冲 DFT 正变换 → 全 1 谱（4 项断言）
```

上游测试情况：autotools 项目无 make check/ctest 注册，tests/ 目录有独立测试程序
`fftw_test`/`rfftw_test`（correctness 模式实测通过）。test_package 自研 4 项断言
补齐功能验证。

## 注意事项

- FFTW2 是 2003 年遗留库，仅 clipper 需要其单精度 sfftw/rfftw 接口；
  现代 FFTW3（fftw/3.3.10.x）API 不兼容，不可替代
- 补丁 0001/0002 体积大（config.guess/sub 整体升级），属 E007/E072 标准路径，
  已在 MANIFEST 的 patch_type 标注 portability
---

**编译结束**: 2026-09-20 16:50
**最终状态**: built
