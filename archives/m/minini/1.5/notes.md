# minini 1.5 适配记录

## 上游与交付

- **上游**：minIni（CompuPhase）1.5 —— 可移植、可裁剪的 INI 读写库（C/C++ 双接口）。
  GitHub tag `v1.5`：`https://github.com/compuphase/minIni/archive/refs/tags/v1.5.tar.gz`，
  sha256 `3356fd4c…964c5a6a2`。平台任务：`minini` / `1.5`。
- **上游形态**：**没有构建系统**，设计上就是"把 `dev/minIni.c` 拖进你的工程"，
  靠 glue 头（`minGlue.h` = stdio，另有 FatFs/EFSL/CCS/mdd 后端）适配 I/O。
- **交付**：
  - `lib/libminIni.a`（用 profile 的 `tools.build:compiler_executables` 编译，R33）
  - `include/minIni.h` + 全部 glue 头（消费者可换后端）
  - `share/minini/minIni.c` —— 保留上游"内嵌源码"用法（`cpp_info.resdirs` 同时发布该目录）
  - `licenses/{LICENSE,NOTICE}`（Apache-2.0）+ `README.md`

## 必须的移植修正（上游 1.5 的缺陷）

`ini_putbool` 的**声明**（`dev/minIni.h:54`）与**实现**（`dev/minIni.c:961`）误用了
未定义类型 `TCHAR`（其余所有 API 都是 `mTCHAR`；而 `minIni.c` 里
`#define TCHAR char` 出现在 `#include "minIni.h"` **之后**，等于没生效）⇒
在 ANSI/非 Windows 配置（即 Linux/OHOS）下**整包编译失败**，上游自带测试也编不出来。

修法：两处 `TCHAR` → `mTCHAR`（配方内联按二进制替换，保留上游 CRLF 行尾；
放在 `build()` 编译前）。修好后上游测试与消费者用例都能编译运行。

> 顺带一条经验：minIni 源码是 **CRLF 行尾**，GNU `patch` 必须加 `--binary`，
> 否则它会剥掉补丁里的 CR 并报 `different line endings`；因此本包用配方内联修正而非补丁文件。

## 测试证据

| 层级 | 内容 | 结果 |
|------|------|------|
| 上游自带测试 | `dev/test.c`（**29 条 assert**，需要 `test.ini`/`testplain.ini` 夹具）：字符串/整数/布尔/浮点读取、大小写与尾随注释、缺省值、`ini_getsection`/`ini_getkey` 枚举、`ini_browse` 回调、相对路径 INI | 在 `build()` 里编译并运行，**退出码 0**（本地原生 gcc 实测；CI 原生构建同样真跑） |
| 完整消费者用例（rule12） | `test_package/test_minini.c` 16 步：写 6 个键 → 读回字符串/整数/布尔/浮点 → 缺失键/段的默认值 → `ini_haskey`/`ini_hassection` → 枚举（2 段 / paths 2 键 / browse 6 个键值对）→ 覆盖写 port=9090 → `ini_puts(...,NULL,...)` 删键（browse 剩 5）→ 上游夹具的尾随注释剥离与 plain（无段落）INI 解析 | **16/16 通过**（本地原生编译 + 运行实测） |
| 适配自检（M） | `test_package/test_layout.py`：静态库（ar 归档）、`minIni.h`、glue 头、`share/minini/minIni.c` 含移植修正、许可、未夹带中间产物 | **8/8 通过** |

## 本地验证的边界（如实说明）

本工作站（x86_64）没有 OHOS 工具链，本地用**同一份源码 + gcc 原生复现配方流程**
（内联修正 → 编译静态库 → 跑上游测试 → 跑消费者用例）验证；OHOS 侧构建与真机执行
由平台 CI 完成（host/build profile 同为 `ohos-aarch64` → 原生构建 → build() 里的
上游测试与 test_package 都真跑）。
