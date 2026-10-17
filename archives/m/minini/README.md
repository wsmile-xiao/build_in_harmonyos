# minini

**minIni** —— 可移植、可裁剪的 INI 文件读写库（C 与 C++ 双接口），上游：
<https://www.compuphase.com/minini.htm>（GitHub: `compuphase/minIni`），
许可证 Apache-2.0。

设计上是"单文件源码库"：核心是 `minIni.c` + `minIni.h`，通过 glue 头
（`minGlue.h` 默认 stdio，另有 FatFs/EFSL/CCS/mdd 等嵌入式后端）把文件 I/O
映射到目标平台。

## OHOS（鸿蒙 PC / aarch64）适配状态

| 版本 | 状态 | 依赖 | 交付 |
|------|------|------|------|
| 1.5 | 已适配（上游 29 断言测试通过；消费者用例 16/16；自检 8/8） | 无 | `lib/libminIni.a`、`include/minIni.h` + glue 头、`share/minini/minIni.c`（内嵌用） |

> ⚠️ 上游 1.5 在 ANSI/非 Windows 配置下**无法编译**（`ini_putbool` 声明/实现误用未定义的
> `TCHAR`）。本包在构建时按二进制方式就地改为 `mTCHAR`（保留上游 CRLF 行尾），
> 详见 `1.5/notes.md`。

## 使用

```ini
[requires]
minini/1.5
```

```c
#include <minIni.h>
long port = ini_getl("server", "port", 8080, "app.ini");
ini_puts("server", "host", "example", "app.ini");
```
