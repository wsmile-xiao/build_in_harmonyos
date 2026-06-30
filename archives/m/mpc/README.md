# GNU MPC - Multiple Precision Complex Library

## 简介

GNU MPC 是一个复数算术库，基于 GNU MPFR 和 GNU GMP 实现，支持任意精度的复数运算。它提供了 C 语言接口，用于高精度科学计算和数学运算。

## 主要功能

- **复数运算**: 加、减、乘、除、幂运算
- **数学函数**: sin, cos, tan, exp, log, sqrt 等
- **精度控制**: 可设置任意精度的复数运算
- **复数比较**: 复数的大小比较和相等判断
- **输入输出**: 复数的字符串表示和解析

## OHOS 适配要点

### 平台识别问题

1. **config.guess 识别失败**: 原始的 config.guess 无法识别 HarmonyOS 系统，需要添加 `__OHOS__` 宏检测逻辑
2. **config.sub 三元组验证**: 需要在 kernel-os 白名单中添加 `linux-ohos*`，否则会报错 "Kernel 'linux' not known to work with OS 'ohos'"
3. **临时目录权限**: configure 和 config.status 中的 mktemp 会创建在当前目录，可能权限不足，需要修改为 `$TMPDIR` 或固定路径

### 编译环境配置

```bash
# 安装依赖
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- gmp 6.3.0
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- mpfr 4.2.1

# 设置编译参数
export PKG_CONFIG_PATH=/storage/Users/currentUser/usr/local/lib/pkgconfig
export CFLAGS="-I/storage/Users/currentUser/usr/local/include"
export LDFLAGS="-L/storage/Users/currentUser/usr/local/lib"
export TMPDIR=/storage/Users/currentUser

# 配置和编译
./configure --prefix=/storage/Users/currentUser/usr/local
make
```

### Libtool 兼容性问题

由于预编译的 gmp 包缺少 `libgmp.la` 文件，libtool 链接会失败。解决方案：
- 使用静态编译绕过 libtool：直接使用 `ar rcs libmpc.a *.o` 创建静态库
- 或手动创建 `libgmp.la` 文件（需要参考 libmpfr.la 格式）

## 依赖关系

### 编译依赖

- **GMP** (GNU Multiple Precision Arithmetic Library) >= 6.3.0
- **MPFR** (GNU Multiple Precision Floating-Point Library) >= 4.2.1

### 运行依赖

同编译依赖，运行时需要动态链接 gmp 和 mpfr 库（如果使用共享库）

## 使用示例

```c
#include <mpc.h>
#include <stdio.h>

int main() {
    mpc_t z;
    mpc_init2(z, 100);  // 100位精度

    // 设置复数: z = 1 + 2i
    mpc_set_si_si(z, 1, 2, MPC_RNDNN);

    // 计算平方
    mpc_sqr(z, z, MPC_RNDNN);

    // 输出结果: z^2 = -3 + 4i
    mpfr_t re, im;
    mpfr_init2(re, 100);
    mpfr_init2(im, 100);
    mpc_real(re, z, MPC_RNDNN);
    mpc_imag(im, z, MPC_RNDNN);

    printf("z^2 = %.20Rf + %.20Rf*i\n", re, im);

    mpfr_clear(re);
    mpfr_clear(im);
    mpc_clear(z);
    return 0;
}
```

编译命令：
```bash
cc -o test test.c -I~/usr/local/include -L~/usr/local/lib -lmpc -lmpfr -lgmp -lm
```

## 已知问题

1. **仅支持静态库**: v1.3.1 版本在 OHOS 上仅编译为静态库（libmpc.a），不提供共享库（libmpc.so）
2. **缺少 pkg-config 文件**: 预编译包未包含 mpc.pc，需要手动创建
3. **需要手动设置环境变量**: CFLAGS 和 LDFLAGS 需指向 gmp 和 mpfr 的安装路径

## 参考资料

- **项目主页**: https://www.multiprecision.org/mpc/
- **源码下载**: https://ftp.gnu.org/gnu/mpc/
- **文档**: https://www.multiprecision.org/mpc/html/
- **GMP**: https://gmplib.org/
- **MPFR**: https://www.mpfr.org/

## 版本历史

- **1.3.1** (2026-06-08): 编译成功，提供静态库，应用于 OHOS 平台适配补丁