# libgcobol

> GCC 16 COBOL 前端（GCOBOL）的运行时库

## 简介

libgcobol 是 GCC 16 引入的 COBOL 语言前端（GCOBOL）配套的运行时库，由 COBOLworx 的
`gcc-cobol` 项目贡献并并入 GCC 主树。它提供 COBOL 程序的数值运算（十进制/二进制转换、
IEEE-754 十进制浮点）、文件 IO、字符串处理（INSPECT/UNSTRING）、数学函数与 XML 解析
等运行时能力。

libgcobol 仅被 GCOBOL 前端编译生成的 COBOL 可执行文件链接使用，其接口是编译器与运行时
之间的 `extern "C"` ABI 约定，不对外发布 C/C++ 头文件。它以共享库 `libgcobol.so.2`
（soname）分发，也支持静态链接（但体积很大，仅调试用）。

## OHOS 适配要点

- 本质是 GCC 的 target library（autotools），无独立 release tarball，源码从 `gcc-16.1.x`
  tarball 的 `libgcobol/` 子目录获取。
- 构建依赖：libxml2（运行时）、可选 libquadmath（Float128，可 `--disable-libquadmath` 禁用）。
- `posix/` 与 `compat/gnu/` 两个子库为 COBOL 源，需 GCOBOL 前端编译；仅需主库时可裁剪。
- 交叉编译到 OHOS 时用 `--with-target-libxml2{,-include,-lib}` 指定 target libxml2（PR122839）。
- 纯 C++ 主库可用 `--host=aarch64-unknown-linux-musl --build=...` 交叉编译。

## 排除与替代

- 不含 GCOBOL 编译器本体（`gcobol`/`gcc` 的 cobol 前端），本包只提供运行时库；
  编译 COBOL 程序需 GCC 16 cobol 语言前端（已由 `feat/gcobol-16.1.0` 适配，
  见 `archives/g/gcobol/`）。
- 静态链接（`--enable-static`）不推荐，产物体积极大，仅调试用。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| libxml2 | 2.15.3 | 运行时，COBOL XML 解析 |
| libquadmath | (GCC 内建) | 可选，已 `--disable-libquadmath` 规避 |
| libgcc / libstdc++ | 设备运行时 | 系统依赖 |

## 功能验证

libgcobol 是运行时库，完整语义验证用 GCOBOL 前端编译真实 COBOL 程序、链接 libgcobol、
运行断言（见 test_package/test.sh + test_program.cob，覆盖 COMPUTE 整数/浮点、MOVE、IF、
PERFORM、FUNCTION MAX/MIN 共 7 条断言）：

```bash
# 1) ABI 探针（无对外头文件，按 ABI 声明符号）
cat > t.cpp <<'EOF'
#include <cstdio>
extern "C" __int128 __gg__power_of_ten(int n);
int main(){ __int128 p=__gg__power_of_ten(2); std::printf("%lld\n",(long long)p); return p==100?0:1; }
EOF
clang++ t.cpp -o t -L<prefix>/lib -lgcobol -Wl,-rpath,<prefix>/lib && ./t

# 2) 端到端（GCOBOL 前端编译 COBOL 程序，链接 libgcobol 运行）
gcobol -o t.cobx test_program.cob && ./t.cobx
```

上游完整 COBOL 语义测试 = GCC 顶层 `gcc/testsuite/cobol.dg`（464 项，GCOBOL 前端编译 +
libgcobol 运行），已在 `feat/gcobol-16.1.0` 真机逐项真实跑通（PASS 450 + XFAIL 13 +
FAIL 0 + SKIP 1）。

## 参考

- [GCC 官方](https://gcc.gnu.org)
- [libgcobol 源码树（gcc.git）](https://gcc.gnu.org/git/?p=gcc.git;a=tree;f=libgcobol)
- [COBOLworx / gcc-cobol](https://gitlab.cobolworx.com/COBOLworx/gcc-cobol)
