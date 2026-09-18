# libcangjie 1.4.0.really.1.4.0 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-09-16
- 编译器: clang/clang++
- 状态: built

## 编译步骤

上游为 Meson 项目（meson_version >= 1.3.2，c_std=gnu11），依赖 sqlite3：

```bash
meson setup --native-file conan_meson_native.ini builddir src --prefix=/
meson compile -C builddir -j1
meson test -v -C builddir --no-rebuild --print-errorlogs
meson install -C builddir --destdir package --no-rebuild
```

Conan 侧用 MesonToolchain 生成 cross/native machine 文件，PkgConfigDeps
生成 sqlite.pc 并别名为 sqlite3.pc 供 `dependency('sqlite3')` 查找。
machine 文件的 [binaries] 段注入 llvm-ar/llvm-ranlib/ninja 绝对路径。

## 上游测试

tests/meson.build 注册 4 项：

- Test common functions（test_libcangjie，约 9 个 assert：版本查询）
- Test Cangjie Character（test_cangjiechar，约 11 个 assert）
- Test Cangjie（test_cangjie，约 170 个 assert，需 CANGJIE_DB 指向构建产物 data/cangjie.db）
- Test Canjigie Character List（test_cangjiecharlist，约 15 个 assert）

合计约 205 个 assert，4 个 meson 测试项。`meson test` 在 conanfile build()
中真实运行，解析 `Ok:/Fail:/Skipped:` 计数并输出
`HMBS_UPSTREAM_TEST_RESULT` 标记；任一失败即抛异常中断构建。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson `dependency('sqlite3')` 找不到包 | sqlite 配方经 PkgConfigDeps 生成 sqlite.pc，而上游找 sqlite3.pc | generate() 中复制 sqlite.pc -> sqlite3.pc |
| 2 | meson 探测 ar/ninja 失败 | profile 仅固定编译器路径；HarmonyOS CPython posix_spawn 不解析 PATH 裸名 | 向 conan_meson_cross/native.ini 的 [binaries] 注入 ar/ranlib/ninja 绝对路径，NINJA 环境变量 запускать meson |
| 3 | 共享库别名链在 HMDFS 上不可靠 | meson 安装 libcangjie.so.3.1.0 + 软链别名 | 物化为实体拷贝（rm -f && cp） |
| 4 | 数据库默认路径为构建时 prefix | CANGJIE_DB 编译进 config.h（prefix=/） | test_package 用 CANGJIE_DB 环境变量指向包内 share/libcangjie/cangjie.db（上游 cangjie_new 原生支持该覆盖） |

## 依赖版本

- sqlite/3.53.3（运行时，`dependency('sqlite3')`）
- meson/1.11.0（tool_requires）

## 验证结果

待真机预检回填：`meson test` 4/4，test_package 消费者测试 Ruben。

```bash
# 预期（真机实测为准）
meson test -v -C build --no-rebuild --print-errorlogs
# Ok: 4, Fail: 0
```

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libcangjie.so.3.1.0（含 .so.3/.so 实体拷贝） | 共享库 |
| include/cangjie/*.h | 公开头文件 |
| lib/pkgconfig/cangjie.pc | pkg-config 元数据 |
| share/libcangjie/cangjie.db | 输入法数据库 |
| bin/libcangjie-cli、libcangjie-bench、libcangjie-dbbuilder | 辅助工具 |

## 注意事项

- 本库为仓颉输入法实现，非图形/多媒体/系统底层库，无需 R40 深度适配。
- 版本号沿用 Debian 命名 1.4.0.really.1.4.0，对应上游 v1.4.0，源码包 sha256 与 Debian .orig 一致。
- test_package 必须设置 CANGJIE_DB，否则 cangjie_new 返回 CANGJIE_DBOPEN。
