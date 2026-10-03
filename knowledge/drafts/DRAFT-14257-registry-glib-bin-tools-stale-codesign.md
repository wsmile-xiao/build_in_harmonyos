# registry glib 包构建期 ELF 工具 .codesign 过期 → exec 126 → generate() 就位重签

## 错误特征

CI 上 meson/ninja 构建在资源文件生成步骤失败，三台不同 worker 同款复现（确定性
配方/环境问题，非病机）：

```
FAILED: [code=126] src/vteresources-gtk4.cc.c
/data/.../p/glibXXXX/p/bin/glib-compile-resources ../src/vte-gtk4.gresource.xml ...
/bin/sh: /data/.../p/bin/glib-compile-resources: Operation not permitted
ninja: build stopped: subcommand failed.
ConanException: Error 126 while executing
```

特征：失败的 ninja 目标是 `gnome.compile_resources` / `gnome.compile_schemas` 生成的
自定义命令（目标名通常含 `resources` / `gschemas`），被 exec 的工具路径指向
conan 缓存里 **glib 依赖包** 的 `p/bin/`。

## 根因

1. registry glib 包的 bin 工具是 OHOS aarch64 ELF 可执行体，链接期 `.codesign`
   段在（部分）worker/内核上已不被信任 → OHOS XPM exec 拒绝 → exit 126
   "Operation not permitted"（不是权限位问题，chmod 无效）。
2. 这些工具没有 RPATH，即使签名有效，exec 时也要求 glib 自身 lib 目录在
   `LD_LIBRARY_PATH`（否则 `Error loading shared library libgio-2.0.so.0`）。
3. 该层与既有条目互补：E077 管**自家产物** post-install 重签，E452 管 task-private
   运行时副本，E472 管 test_package 产物——本条管**构建期 exec registry 依赖包内
   工具**，是任何 meson+glib 生态包（gnome.compile_resources 场景）都可能撞上的层。

## 解法

在配方 `generate()` 里、任何 build exec 之前，对解析到的 glib 依赖包 `bin/` 下全部
ELF 工具就位重签（`llvm-objcopy --remove-section .codesign` + `binary-sign-tool
-selfSign 1`），shebang 脚本（glib-mkenums/glib-genmarshal/gdbus-codegen）跳过；
同时把 glib 的 lib 目录前置到 `LD_LIBRARY_PATH`。完整代码见 .kv 的 solution 块
（vte/0.84.1 `_re_sign_glib_tools()`，commit f9a4be4b）。

验证链：本机复现三台 worker 同款 126 → 手动重签后 `glib-compile-resources
--version` → 2.84.0 恢复可执行 → 配方内固化 → conan create 全绿 → CI #66314 /
#66320 双绿。

## 红线

- 禁止用 chmod/属性位"修"——126 是 XPM 签名拒绝，不是权限位问题。
- 重签必须发生在 `generate()`（build exec 之前）；放在 build() 里第一条也行，但
  PkgConfigDeps 工具变量解析前完成更稳。
- 只签 ELF（magic `\x7fELF`），别把 python/shebang 工具卷进去。
- glib 包可能被多个上下文解析（host/build 各一），按 `dependencies` 遍历取
  name=="glib" 即可，重复重签幂等无害。
