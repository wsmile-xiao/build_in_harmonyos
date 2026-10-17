# mpreal

`mpreal` 是 [MPFR](https://www.mpfr.org/)（多精度浮点运算库）的单头文件 C++ 封装
（MIT），提供 `mpfr::mpreal` 类：运算符重载的高精度算术、与 `double`/字符串的
互转、`toString`/`toDouble` 格式化输出，以及数值极限（epsilon/min/max 等）工具，
C++11 起可用。

```cpp
#include <mpreal.h>
mpfr::mpreal::set_default_prec(256);        /* 默认精度 256 bit */
mpfr::mpreal s = mpfr::sqrt(mpfr::mpreal("2"));
std::string repr = s.toString(20, 10);      /* 1.4142135623730950488... */
```

- 上游仓库：https://github.com/advanpix/mpreal
- 版本：3.7.1（tag `mpfrc++-3.7.1`）
- 许可证：MIT
- 构建系统：header-only（上游无库构建；仅 example/ 演示程序）
- 类型：头文件库（无库产物），依赖 mpfr/4.2.2.1（传递引入 gmp/6.3.0）

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 3.7.1 | built | 首次适配 HarmonyOS PC (aarch64) |
