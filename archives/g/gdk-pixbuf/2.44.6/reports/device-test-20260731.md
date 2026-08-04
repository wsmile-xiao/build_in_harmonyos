# gdk-pixbuf 2.44.6 HarmonyOS PC 真机验证

## 验证范围

- 在两台 AArch64 HarmonyOS PC 上分别使用全新的 Conan home，从官方源码完整执行 `conan create`。
- 执行上游 `tests/meson.build` 登记且本配置可构建的全部 23 个测试。
- 执行 `test_package/test.c` 的 15 项消费检查。
- 检查软件包文件数、ELF 架构、共享库别名、动态依赖和 `.codesign` 节。

## 配方输入一致性

两台设备使用的六个 CI 输入文件与提交工作树逐文件 SHA256 一致：

| 文件 | SHA256 |
|------|--------|
| `conanfile.py` | `2ca46352f6d91a3224d9faca935d12fc055bbf3b89bc0b6f85ec053b4a2ec878` |
| `conandata.yml` | `8aae5190cd872ae9e3331ec8ac4042d867026c608eeea04f1379d7e1320aac14` |
| `test_package/conanfile.py` | `42564daf7afc9120ae1046874fe45b0061ea022e983812ba59151e540bebb4b3` |
| `test_package/CMakeLists.txt` | `8ecc72577d04ad78000b74fb7110c7d0134ed964e0e08f07e0d5539992f5e9f3` |
| `test_package/MANIFEST.yml` | `d4a31031f06f83c582f499cfead5e1fb5312e633cd9938c8d64bfa2f12b1097f` |
| `test_package/test.c` | `1873ac64fc4d1c0e5bb7e939a81a3f0f386a6347e3a64ab7da8c84adbea502e2` |

## 真机 1

- 连接目标：`currentUser@10.62.135.191:2222`
- 完整构建退出码：`0`
- 上游测试：`23/23`，失败 `0`
- 消费测试：`15/15`
- RREV：`dd84a01ac263b78875a2b828a950ac1a`
- Package ID：`b0af90e1159efd308fd932b896270a6e02817540`
- PREV：`892039c3ce31b81c7e8e0213e1477c07`
- 完整日志 SHA256：`26eba5fd887630bd2169a25605cb55dc9f1a13b79446d053a1f5704b9d87e99d`

## 真机 2

- 连接目标：`currentUser@10.62.148.108:2222`
- 完整构建退出码：`0`
- 上游测试：`23/23`，失败 `0`
- 消费测试：`15/15`
- RREV：`dd84a01ac263b78875a2b828a950ac1a`
- Package ID：`b0af90e1159efd308fd932b896270a6e02817540`
- PREV：`1fee01d07a6106f420bc2e086bfe649f`
- 完整日志 SHA256：`d8e69c50eef871774e7f386276f86b4cd9814b59c92e6cf61ec108746d4b235f`

## 产物检查

- 两次软件包均包含 129 个普通文件。
- `gdk-pixbuf-csource`、`gdk-pixbuf-pixdata`、`gdk-pixbuf-query-loaders` 均为 64 位 AArch64 动态 ELF。
- `libgdk_pixbuf-2.0.so`、`libgdk_pixbuf-2.0.so.0`、`libgdk_pixbuf-2.0.so.0.4400.6` 均为普通 AArch64 ELF 文件，避免依赖 HMDFS 符号链接行为。
- 主库 `NEEDED` 包含 `libglib-2.0.so.0`、`libintl.so.8`、`libgobject-2.0.so.0`、`libgmodule-2.0.so.0`、`libgio-2.0.so.0`、`libpng16.so.16`、`libjpeg.so.62`、`libtiff.so.6` 和 `libc.so`。
- 主库存在 `.codesign` 节；完整构建日志同时记录三个命令行程序和三份主库普通文件均完成最终路径签名。

## 结论

同一配方在两台独立 HarmonyOS PC 上均完成源码构建、全部 23 个上游测试和 15 项消费测试，结果可复现。当前证据支持状态 `built`；CI、合并和制品发布仍是后续独立门禁。
