# camlpdf 2.9.1 适配笔记

## 编译环境
- 构建系统: makefile (OCamlMakefile)
- 编译日期: 2026-05-29
- 编译器: clang/clang++ (OCaml 4.13.1)
- 状态: built

## 编译步骤

1. 下载源码 https://github.com/johnwhitington/camlpdf/archive/refs/tags/v2.9.1.tar.gz
2. `make` — 使用 OCamlMakefile 构建 byte-code 和 native-code 库
3. 手动安装到 DESTDIR staging 目录（因缺少 ocamlfind）
4. 安装路径: $DEFAULT_PREFIX/lib/ocaml/site-lib/camlpdf/

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | ocamlfind 不可用 | 系统未安装 ocamlfind | 手动安装库文件到 site-lib/camlpdf/ |
| 2 | G0 干净构建验证失败 | G0 试图运行 ./configure，但 camlpdf 是 OCaml 项目无 configure 脚本 | 手动构建验证通过，G0 不适用 |
| 3 | verify-build 报 manifest 缺少 build_system | manifest 中 build.system 为嵌套字段，脚本需要扁平字段 | 添加顶层 build_system: makefile |

## 源码修改

无源码修改，无需补丁。

## 依赖版本

- OCaml 4.13.1 (ocamlc, ocamlopt)
- clang 15.0.4

## 验证结果

```bash
# 编译产物验证
ls camlpdf.cma camlpdf.cmxa camlpdf.a libcamlpdf_stubs.a dllcamlpdf_stubs.so
# 所有文件存在，编译成功

# 本地安装验证
ls $DEFAULT_PREFIX/lib/ocaml/site-lib/camlpdf/
# 186 个文件已安装
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| camlpdf-2.9.1-ohos-aarch64.tar.gz | 22MB | 主打包文件（含库和模块文件） |
| camlpdf-2.9.1-ohos-aarch64-debug.tar.gz | 112KB | 调试符号包 |

## 注意事项

1. camlpdf 是 OCaml 库，使用 OCamlMakefile 构建系统，不是 autotools/meson 项目
2. ocamlfind 不可用时，需手动安装库文件到正确的 site-lib 目录
3. 该项目没有 configure 脚本，G0 干净构建验证不适用
4. camlpdf 没有可执行二进制文件（纯库），所以功能验证(G2)是警告而非失败

---
**编译结束**: 2026-05-29 10:39
**最终状态**: built