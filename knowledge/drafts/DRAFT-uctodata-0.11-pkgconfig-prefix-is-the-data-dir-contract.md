# DRAFT: 消费方用 pkg-config 反查数据目录时，数据包配方必须自己展开 .pc.in

> Contributor: username- | Status: DRAFT | Created: 2026-09-18
> 来源: uctodata 0.11 适配（ucto 分词器的独立数据包）

## 症状

上游是"代码 + 数据"分开发布的结构：`ucto` 是分词器，`uctodata` 是它的数据。
按常规 autotools 数据包的做法（`get` + `cp` 数据文件，`.pc` 照搬上游模板或不装）
产出的包，装机后**消费方 configure 直接报错**：

```
configure: error: ucto datafiles are not installed!. Please install uctodata package.
```

而数据文件明明都在 `share/ucto/` 下，`ls` 一看数量也对。症状具有误导性——
容易被当成"数据没装进去"而去反复检查 `package()`。

## 根因

`ucto` 的 `configure.ac` 不写死数据目录，而是**用 pkg-config 反查**：

```m4
UCTODATA_PRE=`pkg-config --variable=prefix uctodata`
UCTODATA_DIR=$UCTODATA_PRE/share/ucto
AC_DEFINE_UNQUOTED([UCTODATA_DIR], ["$UCTODATA_DIR/"])
```

于是 `uctodata.pc` 里的 `prefix` 成了数据目录的**唯一来源**。上游的
`uctodata.pc.in` 内容是：

```
prefix=@prefix@
exec_prefix=@exec_prefix@

Name: uctodata
Version: @VERSION@
Description: datafiles for ucto
```

- 若配方把 `.pc.in` 原样拷进产物 → `prefix` 是字面量 `@prefix@`，
  `pkg-config --variable=prefix uctodata` 返回空/无意义值，消费方拼出
  `@prefix@/share/ucto`，检查失败。
- 若配方干脆不装 `.pc` → `pkg-config` 找不到 `uctodata`，
  上游 configure 走 `PKG_CHECK_MODULES` 的 else 分支报同一个错。

这类包有个共同特征：**没有源码、没有编译步骤**，所以问题不可能在构建期暴露，
只有在"被另一个包消费"时才现形。

## 修复

配方自己生成 `.pc`，`prefix` 指向 `package_folder`（Conan 的可重定位约定）：

```python
def package(self):
    ...
    pc_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
    os.makedirs(pc_dir, exist_ok=True)
    with open(os.path.join(pc_dir, "uctodata.pc"), "w", encoding="utf-8") as handle:
        handle.write(
            f"prefix={self.package_folder}\n"
            "exec_prefix=${prefix}\n\n"
            "Name: uctodata\n"
            f"Version: {self.version}\n"
            "Description: datafiles for ucto\n")

def package_info(self):
    self.cpp_info.resdirs = [self._datadir]
    self.cpp_info.set_property("pkg_config_name", "uctodata")
```

并用 `pkg_config_name` 让 Conan 的 `pkg_config` generator 也能对上名字，
`resdirs` 给不查 pkg-config 的消费方留一条路。

## 判据

```sh
# 1) 契约成立（有 pkg-config 时直接执行，就是消费方的那条命令）
pkg-config --variable=prefix uctodata     # 必须等于 package_folder

# 2) 没有残留的 autotools 占位符
grep -c '@prefix@\|@VERSION@' <pkg>/lib/pkgconfig/*.pc    # 必须为 0
```

这两条已固化为 `test_package/test_data.py` 的断言：先静态检查 `.pc` 文本，
再在环境存在 `pkg-config` 时真的执行一次上表第 1 条命令（不存在则显式 skip，
不静默通过）。

## 附：数据包的完整性断言不能靠直觉推断

同一类包还有一个容易写错的地方。给"每种语言一个缩写表"这种结构写完整性检查时，
直觉写法是：

```python
for lang in ("eng", "nld", "deu", "fra", "ita", ...):
    expect(f"{lang}.abr")
```

在 uctodata 上这会**直接失败**，因为上游的真实清单不是对称的：

- 有 `tokconfig-ita`，但**没有** `ita.abr`；
- 荷兰语的缩写表叫 `nld_afk.abr`，**不叫** `nld.abr`；
- 真实清单是 `config/Makefile.am` 的 `config_DATA`：17 个 tokconfig + 10 个 abr
  + 3 个 rule + 5 个 table = **35 个文件**。

正确做法是**逐字复刻上游的安装清单**（并把 `Makefile.am` 这种 `EXTRA_DIST` 项排除），
同时用一条断言守住"产物里不含构建系统文件"，防止后人把逐文件 `copy` 改回通配符 `*`。

## 知识库查重与边界

按关键词（`pkg-config`、`pkgconfigdir`、`pkgconfig_DATA`、`@prefix@`、数据包、
`install-data`、`architecture independent`、`resource data package`、NLP 词典数据包）
检索 `knowledge/graph/` 全部 540 条正式条目，最接近的 4 条及其边界：

| 条目 | 覆盖内容 | 与本条的差异 |
| --- | --- | --- |
| **E255** 资源型数据包在 OHOS 上的 Conan 适配与验证通用方法 | 纯资源/数据包的**通用配方形态**：`package_type="unknown"`、无编译、`copy()` 到 `share/`、符号链接循环处理、L0/L1 门禁不适用 | 它解决的是"数据包怎么写才不被质量门禁误伤"，**完全没有涉及 `.pc` 文件**，也没有讨论"数据目录如何被下游发现"。本条补的正是装配期契约这一层 |
| **E251** NLP 词典/分词数据包在 OHOS 上的适配模式 | 词典包的 hash 固定、UTF-8 校验、条数统计、索引生成、样本文本比对（mecab 系） | 同属 NLP 数据包，但它的消费方是**同仓构建出的索引工具**；uctodata 的消费方是**另一个独立包 ucto，靠 pkg-config 反查路径**。发现机制不同，失败面也不同（E251 是内容正确性，本条是目录发现） |
| **E241** 数据/规则清单型库的固定版本、hash 完整性、规则查询与精确输出比对 | JSON/规则清单型数据的完整性校验方法 | 同样只覆盖"数据内容对不对"，不覆盖"数据放在哪、下游怎么找" |
| **E089** aclocal `@am_AUTOM4TE@` 未替换导致 `pkgconfigdir` 缺失 | 构建期 autotools 宏未展开（要跑 aclocal 的场景） | 相邻但方向不同：E089 是**构建工具自身**的占位符没替换，修法是打 `configure.ac`/`aclocal.m4`；本条是**我方配方生成的产物里**的占位符，修法是配方自己写 `.pc`，且不经过任何 autotools |

检索取证：`grep -rl 'pkg-config' knowledge/graph/E*.kv` 命中 8 条（E058/E075/E089/E123/
E139/E158/E183/E243），逐条读过，**没有一条讨论"用 pkg-config 的 prefix 变量反查数据目录"
这一装配契约**；`grep -rl '@prefix@' knowledge/graph/E*.kv` 零命中。

**结论**：本条增量 = ① 一条可判定的装配期前提（数据包无源码，契约破了也不会构建失败，
只在被消费时以 `datafiles are not installed` 现形）；② 一条可复用修法（配方自写 `.pc`，
`prefix=<package_folder>`，配 `pkg_config_name`/`resdirs`）；③ 两条判据（
`pkg-config --variable=prefix` 必须等于 `package_folder`；`.pc` 中不得残留 `@xxx@`），
外加"完整性断言逐字复刻上游 `config_DATA`、不用对称性直觉推断"这条防呆。

## 可推广性

这是一个**跨库复用的装配期契约**，适用于所有满足以下条件的包：

1. 上游把数据拆成独立发布的包（`*-data`、`*-dict`、`*-fonts`、`*-models`…），
   且数据包本身**没有源码**；
2. 上游用 `pkgconfigdir` + `pkgconfig_DATA` 声明 `.pc`，模板里是 `@prefix@`；
3. 消费方用 `pkg-config --variable=prefix <name>`（或 `--variable=<datadir>`）
   反查数据目录，而不是编译期写死路径。

这三条同时成立时，"数据装没装对"无法通过构建失败发现，必须靠
**`.pc` 契约断言 + 上游清单逐字复刻**这两件显式手段兜住。
