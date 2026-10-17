# DRAFT-kakasi-2.3.6 — automake make check 的 TESTS 脚本在 HMDFS 上无执行权限，sh 循环须容忍 skip(77)

> 触发事件: kakasi 2.3.6 HarmonyOS PC shadow CI
> 库类型: C 库 + 命令行工具（autotools，tests/ 下 9 个 shell 测试脚本）

## 问题

kakasi 的上游测试是 `tests/` 下的 shell 脚本（`kakasi-1` … `kakasi-9`），
由 automake 的 `make check` 驱动。真机上直接跑 `make check` 报：

```
/system/bin/sh: ./kakasi-1: Permission denied
FAIL: kakasi-1
```

改用 `sh ./kakasi-N` 显式调用后，测试又"整体失败"——日志显示 `kakasi-4`
打印 `not GNU echo.` 后退出，整个循环 exit 1。实际上 `kakasi-4` 是按
automake 约定返回 **77（SKIP）**，不是失败；`kakasi-5`（上游 disabled）也
返回 77，`kakasi-7` 返回 0。问题出在循环写法把 77 当成了失败。

## 根因

两层：

1. **HMDFS 不给脚本执行权限**（见 E087）：`chmod +x` 不生效，automake 的
   `check-TESTS` 直接 `./kakasi-N` 就 `Permission denied`。解法是用 `sh` 前缀
   显式调用（E087 的推荐方案）。
2. **手动循环误判 skip**：改用 `sh ./test || exit 1` 时，automake 的 SKIP 约定
   是进程退出码 77，而 `|| exit 1` 把所有非零（含 77）都当失败，导致有 skip
   逻辑的测试（无 GNU 工具、上游 disabled）把整个测试循环带崩。

## 方案

用 `sh` 显式调用，并在循环里只把「非 0 且非 77」当作失败：

```python
# 在 recipe build() 里，cwd 指向 tests 目录
self.run(
    "for t in kakasi-2 kakasi-3 kakasi-4 kakasi-5 kakasi-7 kakasi-8; "
    "do sh ./$t; rc=$?; [ $rc -eq 0 ] || [ $rc -eq 77 ] || exit 1; done",
    env="conanbuild", cwd=tests_dir,
)
```

其中退出码语义：0 = PASS，77 = SKIP（automake 标准），其他 = FAIL。

## 验证

- OHOS armv8 真机：`kakasi-2`/`kakasi-3`（romaji）PASS，`kakasi-8`（libkakasi
  链接）PASS，`kakasi-4`（无 GNU echo）SKIP，`kakasi-5`（上游 disabled）SKIP，
  `kakasi-7`（上游 disabled）PASS；`conan create` 通过。
- 另注意：`kakasi-1` 依赖 GNU `echo -e`（toybox echo 不解释 `\NNN` 转义），
  属 toybox 兼容性（E010）范畴，单独排除。

## 适用边界

- automake/autotools 的 `make check`（`TESTS` 变量驱动 shell 脚本）；
- HMDFS 上 `./test: Permission denied`；
- 测试脚本自身带 SKIP 逻辑（`exit 77`），或上游 disabled 用 77/0 占位。

## 反例

- 测试脚本没有 skip 语义（不会返回 77）：简单 `sh ./test || exit 1` 即可，
  不必加 77 容忍；
- 目标文件系统正常授予执行权限：`make check` 原生可用，无需 sh 前缀。

## 限制

- `sh` 显式调用会丢掉测试脚本 shebang 里的 `-e`（如 `#!/bin/sh -e`），
  脚本内已显式 `exit 1` 的错误仍能捕获，但隐式命令失败的 set -e 保护失效；
  如需保留，用 `sh -e ./test` 但先确认 disabled/skip 分支不会被 `-e` 误伤。
- 跳过（77）的数量与原因必须在 notes/manifest 里如实申报，不得把 SKIP 记为 PASS。
