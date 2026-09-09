# DRAFT-ohos-makefileam-mechanical-cmake-overlay：autotools 库无预生成 configure——机械解析 Makefile.am 生成 CMake overlay

> Contributor: xiao921924 | Status: Draft | Updated: 2026-09-03
> Source: burp 3.3.0 HarmonyOS PC 适配（tarball 仅 Makefile.am，环境无 automake/libtool）

## 现象

autotools 库 tarball 只带 `Makefile.am` + `configure.ac`（无预生成
`configure`）。两条常规路都堵死：

```
$ ./configure
sh: configure: not found
$ ./autogen.sh
autogen.sh: automake: command not found   # OHOS 构建环境无 automake/libtool，网络受限装不了
```

转 CMake 时若**手工抄源文件清单**：30+ 源文件、多子目录、`$(VAR)` 展开
与 `+=` 追加组织下，漏抄一个 `.c` 就是链接期 undefined symbol，人工
逐行核对不可行（burp 曾因此修了 40 个 undefined symbol）。

## 与现有知识的关系

- E041/E248 是 automake **版本失配/缺失报错**，E058 是 autoconf 缺失
  报错——都是"autogen 这条路怎么修"，不是"改走 CMake 怎么生成"。
- 本条是新类别：放弃 autogen，用脚本机械解析 Makefile.am 生成
  CMakeLists.txt overlay 的完整方法。

## 方案

1. 写一次性 Python 脚本解析 `Makefile.am`：
   - 规则：`$(VAR)` 变量展开、反斜杠续行合并、`+=` 追加、`#` 注释剥离；
   - 每个 `bin_PROGRAMS`/`noinst_PROGRAMS` 目标映射为一个
     `add_executable`，源集合 = 目标主源 + 对应 `_SOURCES` 变量展开；
   - 子目录（`SUBDIRS`/`noinst_LTLIBRARIES`）逐目录建 `add_subdirectory`。
2. **镜像上游"按目标全量编译"语义**（不抽共享库）：上游每个 target
   各自编译全部所需 `.c`，overlay 保持同样结构——避免自创
   `libburp` 引入 ODR/重复符号问题。
3. 依赖查找对齐 conan CMakeDeps 目标（`find_path`/`find_library` 或
   直接链依赖包路径），不引 autotools 专属机制。
4. 生成脚本落盘备查 + README 说明解析规则；**归档只提交生成产物
   CMakeLists.txt**（上游源码零修改）。
5. 校验闭环：
   - `nm -u <bin> | grep ' U '` 中项目自身符号必须为 0（漏源文件会暴露）；
   - 上游测试套件全量跑通，行为与上游一致。

## 验证证据

- burp 3.3.0：脚本从 `Makefile.am` 生成 372 行 `CMakeLists.txt`
  （111 个主源 → `burp` target，177 个 → `runner` target），
  undefined symbol 清零，上游 check 套件 233 例全量可跑
  （226 通过 / 7 环境性失败，与 config.h 修复正交）。
- 适用软件：所有 tarball 仅含 Makefile.am（无 configure）且构建环境
  无法 autogen 的 autotools 库（源文件 >15、多子目录时收益最大）。
