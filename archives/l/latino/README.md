# latino for OpenHarmony (HarmonyOS)

本配方将 Latino 语言解释器 1.4.4 适配到 OpenHarmony（ohos-aarch64），通过 Conan 生态构建，同时产出 CLI 工具与可嵌入库。

## 软件信息

| 项目 | 值 |
|------|-----|
| 软件名称 | latino |
| 版本 | 1.4.4 |
| 官网 | https://lenguaje-latino.org/ |
| 源码 | https://github.com/lenguaje-latino/latino (v1.4.4) + latino-core 子模块 (3a6ecd4) |
| 许可证 | MIT |
| 构建系统 | CMake |

## 产物

- `bin/latino` — 解释器 CLI（`latino script.lat`、REPL、`--version`）
- `lib/liblatino.so` / `lib/liblatino.a` — 嵌入式库（`shared` 选项选择）

## 依赖（全部经 Conan 声明，无静默系统链接）

- readline/8.3（静态，含传递 ncurses/6.6）— REPL 行编辑
- libc/libm/libdl — 基础运行时（R26 允许）

## 构建

```bash
# shared（默认）
conan create archives/l/latino/1.4.4 \
  -pr:h <ohos-aarch64 profile> -pr:b <ohos-aarch64 profile> --build=missing

# static
conan create archives/l/latino/1.4.4 \
  -pr:h <ohos-aarch64 profile> -pr:b <ohos-aarch64 profile> \
  --build=missing -o "latino/*:shared=False"
```

## OHOS 适配要点

1. **E092**：上游 install 规则全部在 `if(UNIX)` 内，CMake 无 HarmonyOS 平台模块 → `CMAKE_SYSTEM_NAME` 映射 Linux（ableton-link 先例；OHOS clang 定义 `__linux__`，上游 Linux 分支语义完全适用）。
2. **musl 空壳 libintl.h + bison `YY_`→`dgettext`**（新通用根因，知识草稿 `DRAFT-latino-1.4.4-musl-empty-libintl-bison-dgettext`）：补丁 `0001-musl-no-dgettext-in-bison-prologue.patch` 加 `defined(__GLIBC__)` 守卫。
3. **裸 `-lreadline`**：Conan readline 经 `CPATH`/`LIBRARY_PATH` 注入；terminfo 符号经 `CMAKE_C_STANDARD_LIBRARIES=-lncursesw` 追加（CMake 将其放在链接行末尾，保持静态归档顺序）。
4. **静态库含 main()**（上游全平台缺陷）：`package()` 剥离 latino.o，回填仅含公共全局（`filename`/`parse_silent`）的 stub。
5. **传递头**：`latcompat.h` include readline 头 → `requires(..., transitive_headers=True)`，消费者经 `latino::latino` target 自动获得 readline 头路径。

## 测试

- 上游官方 ctest（`coverage`：ejemplos/coverage.lat）在 build() 阶段真机执行，1/1 通过。
- 消费者测试 3 项全过：嵌入 API 全链（latC_crear_mv → latA_analizar_arch → latC_analizar → latC_llamar_funcion → latC_destruir_mv）跑无递归有界脚本并逐行断言 6 行真实输出（含超时保护）、CLI 跑 10 项精确输出断言的语言测试、`--version`。
- shared/static 双包均验证。

## 已知上游问题（非适配范围，已记录于 manifest）

- 同一表达式内二元递归（`f(n-1)+f(n-2)`）VM 挂死（上游自带 ejemplos/11-fibonacci.lat 真机复现）。
- `desde` 循环体内函数调用 VM 挂死（顺序调用、`mientras` 循环正常）。
