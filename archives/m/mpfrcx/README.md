# MPFRCX - Polynomials over arbitrary precision real/complex numbers

## 简介

MPFRCX 是一个 C 语言库，实现系数为任意精度实数（MPFR）或复数（MPC）的一元多项式算术。它构建在 GMP、MPFR 和 MPC 之上，支持多项式的求值、插值、子乘积树、求导、求根等高级运算，主要服务于 CMH（代数几何高精度计算）等科研软件。

## 主要功能

- **多项式基本运算**: 初始化、赋值、加、减、乘、取负
- **精度控制**: 创建多项式时指定系数精度（`mpcx_init` / `mpfrx_init` 的 prec 参数）
- **求值**: `mpcx_eval` / `mpfrx_eval`（Horner 法，复数或实数点）
- **实部虚部提取**: `mpfrcx_real` / `mpfrcx_imag`
- **高级运算**: 余除、求导、子乘积树、多点插值（Hecke 表示）、由根重构多项式
- **版本查询**: `mpfrcx_get_version`

## OHOS 适配要点

### 平台识别问题

1. **config.guess 识别失败**: 原始脚本无法识别 HarmonyOS，需要添加 `*:HarmonyOS:*:*` 分支输出 `MACHINE-unknown-linux-ohos`
2. **config.sub 三元组验证**: 需要在 kernel-os 白名单添加 `linux-ohos*`，否则报 "Kernel 'linux' not known to work with OS 'ohos'"
3. **临时目录权限**: configure 中 mktemp 使用 umask 077 在当前目录建临时目录，HarmonyOS 用户存储下会权限不足，需改为 `TMPDIR` + umask 022

### 依赖配置

configure 使用三个 `--with-<pkg>=DIR` 参数，每个参数同时添加 `-I DIR/include` 和 `-L DIR/lib`：

```bash
./configure --with-gmp=$GMP_PREFIX --with-mpfr=$MPFR_PREFIX --with-mpc=$MPC_PREFIX
```

注意不能使用 mpc 配方里的 `--with-gmp-include` / `--with-gmp-lib` 拆分形式——mpfrcx 的 configure.ac 只接受单一 DIR。

### Conan 构建

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

## 依赖关系

- **GMP** 6.3.0（任意精度整数/浮点底层）
- **MPFR** 4.2.2（任意精度浮点）
- **MPC** 1.3.1（任意精度复数）

## 使用示例

```c
#include <stdio.h>
#include "mpfrcx.h"

int main(void) {
    /* p(x) = 1 + 2i + (3 - 4i) x，系数精度 128 bit */
    mpcx_t p;
    mpc_t c0, c1;
    mpcx_init(p, 2, 128);
    mpc_init2(c0, 128); mpc_init2(c1, 128);
    mpc_set_si_si(c0, 1, 2, MPC_RNDNN);
    mpc_set_si_si(c1, 3, -4, MPC_RNDNN);
    mpcx_set_deg(p, 1);
    mpcx_set_coeff(p, 0, c0);
    mpcx_set_coeff(p, 1, c1);

    /* 在 x = i 处求值 */
    mpc_t x, r;
    mpc_init2(x, 128); mpc_init2(r, 128);
    mpc_set_si_si(x, 0, 1, MPC_RNDNN);
    mpcx_eval(r, p, x);
    /* r = 1 + 2i + (3 - 4i) * i = 5 + 5i */

    mpc_clear(r); mpc_clear(x);
    mpc_clear(c0); mpc_clear(c1);
    mpcx_clear(p);
    return 0;
}
```

## 参考资料

- **项目主页**: https://gitlab.inria.fr/mpfrcx/mpfrcx
- **源码下载**: https://gforge.inria.fr/projects/mpfrcx/
- **GMP**: https://gmplib.org/
- **MPFR**: https://www.mpfr.org/
- **MPC**: https://www.multiprecision.org/

## 版本历史

- **0.6.3** : OHOS aarch64 适配（本仓库 Conan 配方）
