# pdfsandwich 0.1.7 适配笔记

## 编译环境
- 构建系统: custom (simple configure script + Makefile)
- 编译日期: 2026-08-22 (Conan 适配)
- 原始编译: 2026-05-28
- 编译器: clang/clang++
- 状态: published (Conan 验证通过)

## Conan 适配步骤

1. OCaml 作为 `tool_requires("ocaml/4.14.1.1.4")` 声明（构建时依赖，非运行时）
2. 绕过 configure 脚本直接写 `makefile.installprefix`（configure 的 `test -d $(ocamlc -where)` 在 conan 环境下失败）
3. 使用 shell 命令从 `which ocamlc` 推导 `OCAMLLIB` 路径，设置环境变量覆盖 ocamlc 内置的陈旧路径
4. `conan create` 验证通过（G1-G4 + L2/L4/L5 全部 PASS）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | OCaml 编译器不可用 | 环境中没有预编译 OCaml 包 | 使用 conan 制品仓的 ocaml/4.14.1.1.4 (tool_requires) |
| 2 | ocamlc -where 返回不存在的路径 | conan 缓存重定位后内置路径失效 | 设置 OCAMLLIB 环境变量，从 ocamlc 二进制位置推导正确路径 |
| 3 | configure 检查 test -d $(ocamlc -where) 失败 | 同上，ocamlc -where 返回陈旧路径 | 绕过 configure，直接写 makefile.installprefix |
| 4 | install -s strip 失败 | OCaml 生成的二进制格式 strip 不兼容 | 0001-Makefile.patch: 移除 -s 标志 |
| 5 | self.dependencies["ocaml"] KeyError | conan 2 中 tool_requires 不可通过 self.dependencies 直接访问 | 改用 shell 命令从 PATH 推导路径 |

## 源码修改

- 0001-Makefile.patch: 移除 INSTALL 中的 -s strip 标志

## 依赖版本

- OCaml: 4.14.1.1.4 (conan 制品仓)
- clang: 15.0.4
- GNU make: 4.4.1

## 验证结果

```bash
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
→ G1-G4 + L2/L4/L5 全部 PASS
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方 (application 类型, tool_requires ocaml) |
| conandata.yml | 源码 URL + SHA256 + 补丁声明 |
| test_package/conanfile.py | 消费者测试 (运行 pdfsandwich -version) |
| test_package/MANIFEST.yml | 上游测试声明 |
| patches/0001-Makefile.patch | 移除 -s strip 标志 |
| commands.json | 命令行工具声明 (R38) |

---

**Conan 适配完成**: 2026-08-22
**最终状态**: published
---

**编译结束**: 2026-08-22 08:16
**最终状态**: built
