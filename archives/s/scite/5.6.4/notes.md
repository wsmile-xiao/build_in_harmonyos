# scite 5.6.4 适配笔记

## 编译环境
- 构建系统: makefile（GTK3/Linux 版，共 3 个子组件：lexilla/scintilla/scite 同一 tarball）
- 编译日期: 2026-10-03
- 编译器: clang 15.0.4 / clang++（OHOS SDK 配套，libc++ 15）
- 状态: built

## 编译步骤

源码包 scite564.tgz 顶层含 3 个目录（lexilla/scintilla/scite），无单一包裹目录。

```bash
# 1) Scintilla GTK3 核心（生成 scintilla.a + libscintilla.so）
cd scintilla/gtk && make GTK3=1 -j2

# 2) Lexilla 词法库（生成 liblexilla.a + liblexilla.so）
cd lexilla/src && make -j2

# 3) SciTE 编辑器本体（生成 bin/SciTE，链接 GTK3 + scintilla + lexilla + 内置 Lua）
cd scite/gtk && make GTK3=1 -j2

# 依赖注入（本机验证）：PKG_CONFIG_PATH 指向 PkgConfigDeps 生成的 .pc 目录
export PKG_CONFIG_PATH=$PWD/../.. ; export LD_LIBRARY_PATH=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib
```

conan create 验证：`conan create archives/s/scite/5.6.4 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable` → G1-G4 + L2/L4/L5 全部 PASS。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 解压后 .work 只剩 CheckLexilla.c/makefile | `_promote_nested_source` 对三顶层目录 tarball 误判，把 `lexilla/examples/CheckLexilla/` 提升为源码根并删除其余源码 | 手动重建 .orig/.work：保留 lexilla/scintilla/scite 三目录结构 |
| 2 | `std::ranges::sort` 等 24 处 C++20 ranges 算法编译失败 | OHOS libc++ 15 未定义 `_LIBCPP_ENABLE_EXPERIMENTAL` 时主动定义 `_LIBCPP_HAS_NO_INCOMPLETE_RANGES`，把整个 std::ranges 命名空间关停 | 11 个补丁：全部改写为 C++17 标准算法（std::sort/replace/find/count/transform + begin/end） |
| 3 | `fileName <=> other.fileName`（string spaceship）编译失败 | OHOS libc++ 15 未实现 std::string 的 operator<=>（P1614R2 首发 LLVM 19） | FilePath.cxx 改写：compare() 三次判断映射 weak_ordering::less/greater/equivalent |
| 4 | `gmodule-no-export-2.0.pc` 缺失导致 CONFIGLIB 展开为空、GTK 链接符号未定义 | glib 包里只有 gmodule-2.0.pc；scite makefile 的 CONFIGLIB 需要 gmodule-no-export-2.0 | conanfile.py generate() 依据现成 gmodule-2.0.pc 生成转发别名 gmodule-no-export-2.0.pc |
| 5 | conan create source() 报 "tgz contains more than 1 folder in the root" | scite564.tgz 顶层 3 个目录，strip_root=true 冲突 | conandata.yml 改 strip_root: false（多顶层目录不剥离） |
| 6 | conan create 应用 0004 补丁报 "can't backup original file to ...PropSetFile.cxx.orig" | 上游 tarball 自带 3 个 .orig 残留（PositionCache/StyleWriter/PropSetFile.cxx.orig），与补丁应用的 .orig 备份冲突 | source() 解压后遍历删除 *.orig 残留 |
| 7 | make install 在 conan 环境失败（cp 无法创建 share/scite 目标目录） | OHOS toybox `install` 命令语义差异（本地 shell install 可用，conan 洁净环境行为不同） | conanfile.py package() 改为手动 copy 产物（SciTE/libscintilla.so/liblexilla.so/properties/html/png） |
| 8 | `std::string::contains` 编译失败 | OHOS libc++ 15 未实现 string::contains（C++20） | 核查源码使用点全为 std::set/map/自定义 VarChain 的 contains（均可用），无需改源码 |

## 源码修改

11 个补丁（全部为 C++20 → C++17 可移植改写，无平台宏）：

- `0001-scite-src-EditorConfig.cxx.patch` — ranges::replace → std::replace
- `0002-scite-src-FilePath.cxx.patch` — spaceship(<=>) 改写 + ranges::replace/sort → std 等价
- `0003-scite-src-PathMatch.cxx.patch` — ranges::replace → std::replace
- `0004-scite-src-PropSetFile.cxx.patch` — ranges::find → std::find
- `0005-scite-src-SciTEBase.cxx.patch` — ranges::replace → std::replace
- `0006-scite-src-SciTEBuffers.cxx.patch` — ranges::replace → std::replace
- `0007-scite-src-SciTEIO.cxx.patch` — ranges::replace ×5 → std::replace
- `0008-scite-src-SciTEProps.cxx.patch` — ranges::find/count/replace → std 等价
- `0009-scite-src-StringHelpers.cxx.patch` — ranges::transform/find → std 等价
- `0010-scite-src-StringList.cxx.patch` — ranges::sort ×3 → std::sort
- `0011-scite-src-StyleDefinition.cxx.patch` — ranges::replace → std::replace

## 依赖版本

- gtk/3.24.38（pkg_config_name=gtk+-3.0），及其传递依赖：glib 2.84.0.1 / cairo 1.18.4 / cairo-gobject / pango 1.56.4 / harfbuzz 14.2.0 / gdk-pixbuf 2.44.6 / atk 2.38.0.1 / fribidi 1.0.16 / libepoxy 1.5.10 / zlib 1.3.1.1 / fontconfig 2.18.1.1
- 全部为 conan 制品仓已发布版本（本地 conan install 注入，未触碰 usr/local）

## 验证结果

```bash
# scintilla 单元测试
cd scintilla/test/unit && make CLANG=1 && ./unitTest    # PASS: 52 cases / 3812 assertions
# lexilla 词法测试
cd lexilla/test && make CLANG=1 && ./TestLexers          # PASS: 全部 lexer 样例
# scite 单元测试
cd scite/test && make CLANG=1 && ./unitTest              # PASS: 11 cases / 212 assertions
# conan 配方验证
ohc-run.py conan-verify scite 5.6.4                      # PASS: G1-G4 + L2/L4/L5
# 产物
scite/bin/SciTE（4.0MB GTK3 版）+ libscintilla.so + liblexilla.so
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | makefile/GTK3 构建配方（package_type=application，R38 commands.json 声明） |
| conandata.yml | 官方源 https://www.scintilla.org/scite564.tgz + sha256 + 11 补丁声明 |
| patches/0001-0011 | C++20 ranges/spaceship → C++17 可移植改写 |
| test_package/ | 消费者冒烟测试（SciTE 二进制 + 组件库 + 属性文件完整性）+ MANIFEST.yml |
| commands.json | tool 类型命令行工具声明 |

## 注意事项

- 上游 tarball 自带 3 个 .orig 残留文件，source() 已自动清理（否则与 conan 补丁备份冲突）
- SciTE 为 GTK3 GUI 应用：headless 环境 gtk_init 会快速失败，test_package 中
  二进制执行仅在校验产物完整性后进行（can_run 时）；GUI 完整功能需带显示设备人工确认（R40）
- 知识库新增草案 E587-draft-0D23：OHOS libc++15 默认禁用 C++20 ranges 算法
  （宏根因 _LIBCPP_HAS_NO_INCOMPLETE_RANGES，加 -D_LIBCPP_ENABLE_EXPERIMENTAL 可启用）

**编译结束**: 2026-10-03 18:51
**最终状态**: built