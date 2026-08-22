# cryptokit

OCaml 加密库 by Xavier Leroy

**版本**: 1.21.1 (release1211)
**类别**: crypto
**构建系统**: Dune (OCaml) + C stubs
**许可证**: LGPL-2.0-or-later WITH OCaml-LGPL-linking-exception

## 依赖
- OCaml >= 4.13.0（完整构建）
- dune >= 2.5（完整构建）
- zlib/1.3.1（OCaml 完整构建，C stubs 层不需要）

## OHOS 适配状态
- ⚠️ C stubs 层已编译验证通过（19 个算法文件）
- ❌ OCaml 源码层需要 OCaml 编译器和 dune 构建系统
- 完整验证需要安装 OCaml >= 4.13.0
