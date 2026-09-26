# DRAFT-json-build-1.2.0-init-build-nested-source-promote-test-dir：init_build 嵌套源码提升误将 test/ 子目录提升为源码根（C 单头文件库）

> Contributor: pc4-47 | Status: Draft | Updated: 2026-09-26
> Source: json-build 1.2.0 HarmonyOS PC adaptation（archives/j/json-build/1.2.0，r01）
> 对应：knowledge/drafts/DRAFT-json-build-1.2.0-init-build-nested-source-promote-test-dir.kv

## 现象

json-build 1.2.0（单头文件 C89 JSON 序列化库）在 OHOS PC 适配 init-build 阶段，
`ohc-run.py init-build json-build 1.2.0` 输出：

```text
ℹ️ 嵌套源码检测: 找到源码在 test，正在提升到 json-build-1.2.0.orig ...
✅ .orig 已解压: .../json-build-1.2.0.orig
✅ .work 已创建 (复制): .../json-build-1.2.0.work
✅ 基线指纹: 6 个文件 (json-build-1.2.0.work)
```

随后发现 .orig/.work 中只剩 test/ 内容（Makefile/fuzz.c/greatest.h/test.c/
test_auto.c），根目录的 `json-build.h`、README.md、LICENSE 全部丢失——
header-only 库连头文件都没有，conan-init 之后的 G2 必然空包。

## 根因分析

`init_build._promote_nested_source` 按 C/C++ 构建标记（configure /
CMakeLists.txt / Makefile / meson.build）递归识别"真正的源码子目录"并提升为
源码根。单头文件 C 库的 tarball 根目录只有头文件与文档、没有构建标记，而
`test/` 子目录含 Makefile（构建上游测试用）→ 启发式误把 test/ 当作源码根。

与 E466（Python sdist 误把 docs/ 提升为源码根）同源：**任何"根目录无构建标记 +
子目录有构建标记"的布局都会触发误判**。E466 覆盖 Python sdist 场景；本条目
补充 C 单头文件库（根头文件 + test/ 子目录）这一新增边界。

## 触发条件

- 库为单头文件/header-only，头文件位于 tarball 根目录
- 根目录无 configure/CMakeLists.txt/Makefile/meson.build 等构建标记
- 存在 test/（或其它）子目录且其内含 Makefile 等构建标记

## 修复

```bash
cd <build_dir> && rm -rf json-build-1.2.0.orig json-build-1.2.0.work
mkdir -p json-build-1.2.0.orig
tar xzf <tarball> -C json-build-1.2.0.orig --strip-components=1
cp -a json-build-1.2.0.orig json-build-1.2.0.work
# 核对根头文件已回到 .work 根目录
ls json-build-1.2.0.work/*.h
```

不得修改 scripts/ohc/init_build.py（框架脚本只读，W2）。

## 验证

- 修复后 .work 结构 = 官方 tag v1.2.0 真实结构（json-build.h 在根，test/ 为子目录）
- 后续 conan-verify G2 PASS（header-only 配方打包 json-build.h 成功）
- 上游测试 21/21、test_ohos T1-T5 全通过

## 适用边界 / 反例

- 适用：单头文件 C/C++ 库（根头文件 + test/ 子目录含 Makefile）
- 与 E466 的分界：E466 是 Python sdist 的 docs/ 误提升；本条目是 C 库的
  test/ 误提升，修复均靠手工重建 .orig/.work 保持真实结构
- 反例：根目录本身有 CMakeLists.txt/Makefile 的库不会触发（启发式命中根目录）
