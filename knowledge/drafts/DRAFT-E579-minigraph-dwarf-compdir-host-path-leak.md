# DRAFT-E579: minigraph 0.21 DWARF comp_dir 宿主路径泄漏（-ffile-prefix-map 三重映射）

## 问题

`conan create` 全绿后，对产物二进制做交付前"无宿主路径"扫描：

```console
$ strings minigraph | grep -E '^/storage|^/home|/Users/'
/storage/Users/currentUser/.conan2/p/b/minig<hash>/b
/storage/Users/currentUser/usr/local/bin/../sysroot/usr/include
```

构建机绝对路径被永久嵌入二进制（DWARF 调试信息），违反"无宿主路径泄漏"
验收规则；真机分发时泄漏构建环境信息。

## 根因

上游 Makefile 自带 `CFLAGS = -g -Wall ... -O3`：

1. `-g` 生成 DWARF 时 `DW_AT_comp_dir` 记录编译器工作目录的绝对路径。
   `make -C <source_folder>` 执行时编译器 cwd 是 **source_folder**
   （`.../b`，Conan 的源码目录），不是 `build_folder`
   （`.../b/build-release`）——只映射 build_folder 无效（实测复现）。
2. DWARF `#line` 引用的系统头文件记录工具链 sysroot 的绝对路径
   （`/storage/Users/<user>/usr/local/bin/../sysroot/usr/include`），
   需要单独映射工具链根目录。

CI 的 L5 只扫 `lib/` 下 `.so` 的 DT_NEEDED 绝对路径，不覆盖二进制
DWARF——本地 CI 全绿不代表交付验收通过。

## 解决

在配方 build() 组装 CFLAGS 时追加三条 `-ffile-prefix-map`：

```python
maps = []
for folder in (self.source_folder, self.build_folder):
    maps.append("-ffile-prefix-map={}=/pkg-build".format(
        os.path.abspath(folder)))
# make -C 下编译器 cwd 是 source_folder；工具链根覆盖 sysroot +
# clang resource dir 的头文件引用
maps.append("-ffile-prefix-map={}=/_toolchain".format(
    os.path.dirname(os.path.dirname(os.path.abspath(cc)))))
cflags = "<upstream cflags verbatim> " + " ".join(maps)
```

上游 CFLAGS 其余部分逐字保留（零补丁）。实测映射后
`strings | grep -E '^/storage|^/home|/Users/'` 归零。

## 边界（适用条件与禁止）

- **仅在真实存在路径泄漏时启用映射**：先对产物执行字节级绝对路径扫描
  （`strings <binary> | grep -E '^/storage|^/home|/Users/'`）确认确有宿主
  路径嵌入，再启用三条 -ffile-prefix-map；无泄漏的构建不要加。
- **不得全局删除 -g**：-g 是上游/调试能力的一部分，删 -g 丢失 DWARF
  调试信息（真机符号化栈回溯需要）；路径问题用映射解决，不用摘除
  调试开关解决。
- **不得删除整个调试段来掩盖路径**：`llvm-objcopy --strip-debug` 之类
  会同时丢掉调试能力，是掩盖而非修复；仅在交付明确不需要 .debug 信息
  时才可作为降级选项（见 kv fallback）。
- **不得硬编码本机构建路径**：映射的左侧必须是
  `os.path.abspath(self.source_folder / self.build_folder / cc)` 等运行时
  推导值，右侧虚拟路径（/pkg-build、/_toolchain）是通用占位符；禁止
  写死 /storage/Users/<某用户>/... 这类机器特定路径。
- **三条都要**：实测只映射 build_folder 时 comp_dir 仍泄漏 source_folder
  路径；只映射前两条时 sysroot include 路径仍在 DWARF #line 里。
- **必须保留产物字节级绝对路径扫描**：映射不是免除验收的理由——
  test_package 仍须断言二进制无 /storage/、/home/、/Users/ 等宿主路径
  （minigraph test 17），作为泄漏回归的门禁。

## 验证

- 单映射 build_folder：comp_dir 仍泄漏 source_folder 路径（复现）
- 双映射（source+build）：sysroot include 路径仍在（复现）
- 三重映射：零泄漏，17/17 测试通过，ELF/AArch64/musl/.codesign 全过

## 相关

- 同族：hoedown CFLAGS 草稿（Makefile 标志传递）、E295（产物完整性门禁）
- 配方：archives/m/minigraph/0.21/conanfile.py build()
- 测试：test_minigraph.sh Test 15（二进制宿主路径扫描断言）
