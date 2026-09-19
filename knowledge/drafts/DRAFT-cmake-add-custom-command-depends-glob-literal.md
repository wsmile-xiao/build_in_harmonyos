# CMake `ADD_CUSTOM_COMMAND` 的 `DEPENDS` 中写 `*.ext` 字面通配符导致 Make 报 No rule to make target

## 基本信息

- **严重度**: 2
- **类别**: cmake, build-system, make, patching
- **阶段**: compilation（configure 阶段不报错）
- **适用面**: 任何 CMake 项目在 `ADD_CUSTOM_COMMAND` 的 `DEPENDS` 中
  写 `*.ext` 形式通配符，且使用 **Make 生成器** 时触发

## 错误特征

```
make[2]: *** No rule to make target '*.inc', needed by '<custom-output>'.  Stop.
make[1]: *** [CMakeFiles/Makefile2:<n>] Error 2
make: *** [Makefile:<n>: all] Error 2
```

注意 `*.inc` 为字面量（未展开），实际文件名前缀各异（`*.def`、`*.cmake` 等同理）。

## 根因分析

CMake 的 `ADD_CUSTOM_COMMAND(DEPENDS ...)` 条目会被**原样写入**生成的 Makefile
依赖列表，而 **Make 不展开 shell 通配符**（Ninja 等其它生成器行为不同）。

上游若写成：

```cmake
ADD_CUSTOM_COMMAND(
    OUTPUT  ${CMAKE_CURRENT_BINARY_DIR}/generated.cc
    COMMAND <tool> ${CMAKE_CURRENT_SOURCE_DIR} input.xml ${CMAKE_CURRENT_BINARY_DIR}
    DEPENDS <tool> input.xml *.inc          # ← 问题行
)
```

Make 会把字面量 `*.inc` 当作一个**必须存在的目标名**，因找不到生成它的规则而报
`No rule to make target '*.inc'`。

上游意图通常是"任一 `.inc` 分片变化时重新生成"，该语义在 Make 生成器下不成立。

**易误判点**：
1. **CMake 配置阶段不报错**——`*.inc` 作为字符串是合法的 CMake 语法，
   错误仅在 `make` 阶段暴露，容易被误判为工具链缺失或源码不完整；
2. 报错中的 "No rule to make target" 会让人先怀疑缺少生成规则，而非依赖列表写法。

## 推荐方案

**最小修复**：补丁移除字面通配符条目：

```diff
-	DEPENDS <tool> input.xml *.inc
+	DEPENDS <tool> input.xml
```

**显式枚举替代**（若确需字面量变化触发重新生成）：

```cmake
    DEPENDS <tool> input.xml c-int-source-funcs.inc c-int-query-defines.inc ...
```

### 附：补丁 hunk 行号必须以目标源码为准重新生成

同一段上游代码在不同 release/tag/snapshot 间因前后文增删而**行号偏移**，
直接复用其它版本的补丁会报：

```
hunk no.N doesn't match source file at line L
  expected: b'<old context line>'
  actual  : b'<new context line>'
```

**正确做法**：对**目标版本源码**执行 `diff -u` 生成补丁（或在目标源码上手工修改后
`git diff`），不要手工推算行号。

实测案例：同一 `ADD_CUSTOM_COMMAND` 块在两个相邻上游快照间因新增两行 `SET`
语句而下移一行，hunk header 需从 `@@ -36,7 +36,7 @@` 改为 `@@ -37,7 +37,7 @@`，
且上下文行内容也需同步更新（不能只改行号）。

## 验证方法

```bash
# 1. 干跑确认补丁可应用（必须在目标版本源码上执行）
patch -p1 --dry-run < patches/000N-remove-glob-dependency.patch
#    期望 exit 0；若报 "doesn't match source file" 说明 hunk 行号需重新生成

# 2. 实际构建
make -j4
#    期望退出码 0，全部 target 构建成功
```

实测：修正后 `make -j4` 退出码 0；修正前 `make[2]: Error 1`。

## 关键词

`No rule to make target`, `DEPENDS`, `ADD_CUSTOM_COMMAND`, `wildcard`, `glob`,
`make`, `generated source`, `*.inc`, `*.def`, `hunk doesn't match`,
`patch line offset`

## 来源

- 首次记录：libmusicbrainz5 5.1.0-git20150707 适配（2026-09-17）
  —— 上游 `src/CMakeLists.txt` 的 `DEPENDS make-c-interface cinterface.xml *.inc`
- 该模式为通用 CMake/Make 问题，不限特定库
