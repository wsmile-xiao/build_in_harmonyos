# autotools 探测污染：LIBS 预置依赖库使 AC_CHECK_FUNCS 假阳，生成变量为空导致链接缺库

> Draft: `DRAFT-XFSPROGS-720-AUTOTOOLS-LIBS-PRESET-POISONS-AC-CHECK`
> Stem: `xfsprogs-7.2.0-autotools-libs-preset-poisons-ac-check` — 与同名 `.kv` 配套
> 实例来源: xfsprogs 7.2.0 适配（探索期 configure 传 `LIBS=-luuid` → `LIBUUID` 空）
> 关联知识: E232/E325/E434/E402（依赖与链接类）、E514（构建环境注入类）

## 基本信息

- **ID**: DRAFT-XFSPROGS-720-AUTOTOOLS-LIBS-PRESET-POISONS-AC-CHECK
- **严重度**: 2
- **类别**: autotools, build-system, detection, linking, portability
- **触发工具**: configure|make|ld
- **阶段**: configuration（后果出现在 linking）

## 使用说明（这份知识怎么用）

- **适用**：autotools 项目 configure 阶段"明明缺库却能通过函数探测"，
  而最终链接报 undefined reference；尤其是构建流程用环境变量把依赖 `-l` 注入 LIBS 的场合。
- **不适用**：项目用 `AC_CHECK_LIB`/`PKG_CHECK_MODULES` 显式探测库的场合（不会被污染）。
- **判定口诀**：`checking for <fn>... yes`（没有 "in -l<lib>"）就是危险信号。

## 输入输出定义

- **输入**：`configure.ac` 的探测宏（`AC_CHECK_FUNCS`/`AC_SEARCH_LIBS`/`AC_CHECK_LIB`）+ 依赖列表。
- **输出**：生成的构建变量（如 `include/builddefs` 的 `LIBUUID/LIBINIH/LIBBLKID`）
  与最终链接命令行——两者必须一致；不一致即命中本模式。

## 错误特征（逐字实测）

```
checking for uuid_compare... yes            <- 危险：libuuid 未进 -l 探测路径，却"自带"
...
# include/builddefs（生成物）
LIBUUID =                                    <- 空！正式链接不会出现 -luuid
...
ld.lld: error: undefined symbol: uuid_parse  <- 链接期才爆
>>> referenced by ...
```

对照组（干净的 configure）：

```
checking for uuid_compare in -luuid... yes
LIBUUID = -luuid
```

## 根因

`AC_CHECK_FUNCS` 的链接测试使用**当前 LIBS**。若环境（或构建脚本）预置
`LIBS="-luuid"`，测试自然能解析 `uuid_compare` → configure 认为 libc 自带该函数 →
项目自己的 `AC_CHECK_LIB(uuid, ...)` 分支不会执行 → 生成变量留空。

## 影响范围

- 所有 autotools 项目 + 自动注入环境变量的打包/构建流程（conan、发行版、CI 脚本）；
- 特别常见于"库函数名与库名不同、探测宏用 `AC_CHECK_FUNCS`"的项目；
- 反向影响：假阳会让 configure 忽略"依赖缺失"的真实报错，把问题推迟到链接期甚至
  更晚（共享库运行时），排障成本更高。

## 推荐方案

**方法**: `keep-configure-link-tests-clean-separate-cppflags-ldflags-libs`

三分离原则：

| 变量 | 只放 | 不放 |
|------|------|------|
| CPPFLAGS（必要时 CFLAGS/CXXFLAGS） | 依赖头 `-I` | 库 |
| LDFLAGS | 依赖库搜索路径 `-L` | `-l` |
| LIBS | 项目自身链接测试必需的最小集合 | 全部依赖的 `-l` |

- 让项目自己的 `AC_CHECK_LIB`/`AC_SEARCH_LIBS` 去发现并登记依赖库
  （它们会把结果写进 `LIBXXX` 变量与 LIBS）；
- xfsprogs 实例：`LIBS="-lurcu"`（仅供 `AC_HAVE_LIBURCU_ATOMIC64` 链接测试），
  uuid/inih/blkid 全部交给项目宏 → `LIBUUID=-luuid`、`LIBINIH=-linih`、`LIBBLKID=-lblkid` 正确生成；
- 修复后自查：对每个生成变量 `grep "^LIBXXX" include/builddefs` 应非空，
  且与 `configure` 摘要中的 "in -l<lib>" 行一一对应。

## 验证命令

```bash
# 复现（两次 configure 对照）
LIBS="-luuid" ./configure && grep "^LIBUUID" include/builddefs   # 期望：空
LIBS=""       ./configure && grep "^LIBUUID" include/builddefs   # 期望：-luuid

# 审计探测宏，圈出属于依赖库的函数
grep -n "AC_CHECK_FUNCS\|AC_SEARCH_LIBS\|AC_CHECK_LIB" configure.ac
```

## 取证记录

- 包: xfsprogs 7.2.0（`archives/x/xfsprogs/7.2.0`）
- 探索期日志: `checking for uuid_compare... yes` + `include/builddefs` 中 `LIBUUID =`（空）
- 修复策略落地: 配方 `generate()` 只向 configure 暴露 `LIBS=-lurcu`
  （`conanfile.py` generate() 注释与 W3 配置一致）；最终 12 工具全部链接成功
