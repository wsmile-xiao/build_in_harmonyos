# odinfmt

odinfmt 是 Odin 语言的官方代码格式化工具（类似 `gofmt` / `clang-format`），
本适配将其构建到 HarmonyOS PC（aarch64-linux-ohos）平台。

## 特性
- 纯 Odin 语言实现，产物为单一可执行文件 `bin/odinfmt`，无运行期动态库依赖
  （`DT_NEEDED` 仅 `libc.so`）。
- 格式化对象为 `.odin` 源文件：支持文件模式、目录递归模式、`-stdin` 标准输入模式
  与 `-w` 原地写回模式；排版参数由 `odinfmt.json` 配置（`-config` 显式指定）。

## 构建要点
- 构建工具链：`odin` 编译器（`tool_requires`），编译器本体依赖 LLVM ≥ 17。
- 上游源码不在独立仓：`odinfmt` 源码位于 **`DanielGavin/ols` 仓库的 `tools/odinfmt/`**
  （2026 年起 Odin 主仓 `tools/` 已移除），格式化核心在 `ols` 的 `src/odin/format`
  与 `src/odin/printer`，经 `-collection:src=src` 引入。
- 上游构建命令（`ci.sh` / `odinfmt.sh`）：
  `odin build tools/odinfmt/main.odin -file -collection:src=src -out:odinfmt -no-bounds-check -o:speed`

## 版本
- dev-2026-06（上游 `DanielGavin/ols` tag `dev-2026-06`，commit `fa36fac9770c1715c33c13755bd4090b1959159f`）
