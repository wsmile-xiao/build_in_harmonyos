# smlfmt

Source code formatter for Standard ML.

- Homepage: <https://github.com/shwestrick/smlfmt>
- License: MIT

## HarmonyOS 适配

- 使用 `mlton/20241230` 作为 Conan build requirement 编译 smlfmt（MLton C codegen 需 `gmp/6.3.0`）。
- MLton C codegen 需显式传入 `-cc clang`、GMP include/lib 路径。
- 修复上游测试脚本 `runall` 的 shebang（`/usr/bin/python3` → `/usr/bin/env python3`）和 `git rev-parse --show-toplevel` 路径假设（tarball 非 Git 仓时失败，改为基于脚本自身路径定位源码根）。
- 绕过 Makefile `install` 目标（OHOS 无 `install` 命令），改用 Conan copy 手动打包 `smlfmt` 到 `bin/`。
- 为构建产物 `smlfmt` 二进制添加 HarmonyOS 自签名。
