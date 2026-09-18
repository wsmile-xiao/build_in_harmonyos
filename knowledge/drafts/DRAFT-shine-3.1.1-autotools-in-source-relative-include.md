# shine 3.1.1 — autotools Makefile.am 相对 include 路径需 in-source 构建 (draft)

**Category**: build-system | conan | autotools · **Severity**: 3 · **Tool**: conan/make/clang

## 症状

Conan 2 `conan create`（ohos-aarch64）G2 编译子目录源文件报：

```
src/bin/main.c:24:10: fatal error: 'layer3.h' file not found
```

configure 阶段全部正常（Makefile 已生成），错误只在 make 链接 shineenc 时出现，
且 `-Isrc/lib` 明确存在于编译命令行中。

## 根因

`basic_layout(self)`（含 `src_folder="."` 变体）默认把 build_folder 与 source_folder
分离（如 `build-release/`）。autotools 的 Makefile.am 常用相对**源码根**的 include
路径（`shineenc_CFLAGS = -Isrc/lib`）；automake 的 OoO/VPATH 构建下该路径相对
**build 目录**解析，源码根下的 `src/lib` 不存在 → 头找不到。configure 不受影响
（它在源码内探测），但 make 编译时立即失败。这是"配置通过、编译即炸"的经典
OoO 陷阱，且 `-I$(srcdir)` / `-I../lib` 之外的裸相对写法都会踩中。

## 处置（可复用）

配方 layout() 强制 in-source 构建（build 目录与源码目录合一）：

```python
def layout(self):
    self.folders.source = "."
    self.folders.build = "."
```

关键点：**不要**用 `basic_layout(self, src_folder=".")` —— 它仍会创建分离的
build-release/ 目录，相对 -I 照旧失效（实测踩过）。备选是补丁改
`-I$(srcdir)/src/lib`，但改源优先度低于 layout（R8 补丁最小化，patch 会带
平台宏/路径噪音）。

## 验证

- 修复前：`conan create` G2 失败，`layer3.h file not found`。
- 修复后：`conan-verify shine 3.1.1` G1-G4/L2/L4/L5 全部 PASS；libshine 与
  shineenc 均产出；test_package 消费者测试执行通过。

## 适用边界

- 生效：Makefile.am 用相对源码根 include 路径（`-Isrc/...`、`-I../...`）的
  autotools 包。
- 反例：纯库无子目录跨引用、或已用 `-I$(srcdir)` 显式写法的项目不受影响；
  CMake（CMakeLists 本身用源码相对路径 + include_directories 按源码解释）不同源。
- 关联：E392（raw makefile build_folder/source_folder）、E340（basic_layout +
  cargo 产物）。