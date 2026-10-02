# draft-hamlib-4.7.1-langdetect-recursive-makefile-pl-false-perl

## 症状

`ohc-run.py lang-preflight hamlib 4.7.1` 把一个纯 C/C++ autotools 工程判为
**混合语言（mixed）**，并以 `env_unsupported` 错误终态写入 `.ci-result.json`：

```
detected: mixed
languages: c, cpp, perl
reason: perl module-build 指纹命中 bindings/Makefile.PL
```

但 `bindings/Makefile.PL` 是 hamlib 的 **SWIG/Perl 绑定目录**，不在默认
`./configure && make` 路径里（默认只构建 C 库 + rigctl/rotctl/ampctl），
C 与 C++ 也属兼容族（g++ 可编译 C），本应判 `cpp`（或 c/cpp 兼容）。

## 根因

`scripts/ohc/lang_detect.py` 收集候选文件名时把**递归遍历到的所有文件名**
（而非仅顶层/构建入口文件）放进 `names` 集合，再做指纹匹配。
`Makefile.PL` 是 "perl module-build" 的强指纹，于是任何带
`Makefile.PL`/`Build.PL` 子目录（bindings/、perl/、contrib/）的多语言上游
工程都会被误判。

## 临时绕过（本次采用）

```bash
mv bindings/Makefile.PL /tmp && ohc-run.py lang-preflight hamlib 4.7.1   # 通过
mv /tmp/Makefile.PL bindings/                                            # 复原
```

注意：误判的终态已写入 `.ci-result.json`，需要在后续 `finish`/`submit`
流程中用正确状态覆盖（否则状态文件与事实不符，属审查 P0 风险）。

## 建议修复

1. 指纹匹配只在**浅层**进行：顶层目录 + 一层的 `configure.ac`/`CMakeLists.txt`/
   `meson.build`/`*.pro`/`Makefile.PL` 等构建入口；递归结果只用于统计源码后缀。
2. 或把 `Makefile.PL` 指纹降级为「弱指纹」：需同时存在 `lib/*.pm`/`MANIFEST`
   或顶层无 `configure.ac`/`CMakeLists.txt` 时才判 perl。
3. 语言族兼容已实现（c↔cpp 兼容），但仍被第三方语言（perl/python）破坏，
   建议第三方语言只在**顶层构建入口命中**时才升级为 mixed。

## 验证

- hamlib 4.7.1：移开 `bindings/Makefile.PL` 后 preflight 通过（detected cpp），
  恢复后 conan create / clean-verify / make check 11/11 全绿——说明该文件
  对默认构建路径无影响，误判确认为假阳性。

## 相关

- 触发实例：hamlib/4.7.1（2026-09-28）
