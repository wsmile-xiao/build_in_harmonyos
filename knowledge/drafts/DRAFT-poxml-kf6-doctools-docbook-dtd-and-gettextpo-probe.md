# poxml（KDE）：`FindGettextPO` 裸探测 + KF6 DocTools 的 DocBook DTD 缺口

> 配套结构化条目：`DRAFT-poxml-kf6-doctools-docbook-dtd-and-gettextpo-probe.kv`

## 现象（连续四层失败）

```
Could NOT find GettextPO (missing: GETTEXTPO_INCLUDE_DIR GETTEXTPO_LIBRARY)
kf.doctools.core: Error: Could not find kdoctools catalogs
kf.doctools.core: Error: `xmllint --noout` outputted text
   ... failed to load external entity "file:///docbookx.dtd"
/bin/sh: checkXML6: inaccessible or not found
```

## 坑 1：上游 `FindGettextPO` 是裸探测，必须铺 `CMAKE_PREFIX_PATH`

`poxml` 自带 `cmake/modules/FindGettextPO.cmake`，它**不是 config 包**：

```cmake
find_path(GETTEXTPO_INCLUDE_DIR gettext-po.h)
find_library(GETTEXTPO_LIBRARY NAMES gettextpo)
find_package_handle_standard_args(GettextPO DEFAULT_MSG
    GETTEXTPO_LIBRARY GETTEXTPO_INCLUDE_DIR)
```

所以仅有 Conan 依赖图不够——`gettext` 包前缀必须真的进入 CMake 搜索路径。
而 qtbase / KF6 / gettext 在本仓均为 `cmake_find_mode=none`，生成的
`conan_cmakedeps_paths.cmake` 不含它们的 `lib/cmake`，**配方需自行重写该文件**
（baloo / keditbookmarks 先例）：

```python
lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
for dep in host+build deps:
    lines.append('list(PREPEND CMAKE_PREFIX_PATH "%s/lib/cmake")' % dep.package_folder)
    lines.append('list(PREPEND CMAKE_PREFIX_PATH "%s")' % dep.package_folder)
    lines.append('list(PREPEND CMAKE_LIBRARY_PATH "%s/lib")' % dep.package_folder)
    lines.append('list(PREPEND CMAKE_INCLUDE_PATH "%s/include")' % dep.package_folder)
```

## 坑 2：KF6 DocTools 的 man 页链需要 DocBook XML 4.5 DTD

`kdoctools` 自带的 `kdedbx45.dtd` 用**绝对 URI** 引入官方 DocBook DTD：

```
<!ENTITY % DocBookDTD	    PUBLIC
  "-//OASIS//DTD DocBook XML V4.5//EN"
  "/docbookx.dtd"         >
```

- 该 DTD **不在 kdoctools 包内**（`share/kf6/kdoctools/customization/dtd/` 只有
  `kdedbx45.dtd` 与几个 `.elements`）；
- **ohpcd 没有 `docbook-xml` 包**（也搜不到 docbook-xsl / docbook / xmlcatmgr）；
- `meinproc6` 经 QStandardPaths 找 `customization/catalog.xml`（需
  `XDG_DATA_DIRS`），但 catalog 解析不了那个绝对 URI，`xmllint` 报
  `PEReference: %div.title.content; not found`。

即使手工下载官方 DTD 并写 XML catalog overlay 也**不生效**（实测：
`XML_CATALOG_FILES` 指向的 overlay 对 `file:///docbookx.dtd` 的映射未被
meinproc6/xmllint 采纳）。

**修法**：裁剪该链——`add_subdirectory(doc)` + `kdoctools_install(po)`。

## 坑 3：连带裁剪 checkXML6 的两处调用，但保留 `find_package(DocTools)`

上游 `tests/CMakeLists.txt` 的 `lauri.pot` 生成步与 `lauri_de` ctest 都调用
`checkXML6`（同样需要那个 DTD）：

```cmake
add_custom_command(OUTPUT .../lauri.pot
  COMMAND checkXML6 ${lauri_xml}      # ← 需 DocBook DTD
  COMMAND xml2pot ${lauri_xml} > lauri.pot
  ...)
add_test(NAME lauri_de COMMAND checkXML6 lauri_de.xml)   # ← 同上
```

去掉这两处 `checkXML6`，**保留真实的转换链**（`xml2pot` → `msgmerge` →
`msgfmt`、`po2xml` → `split2po`）与 `split2po` ctest。

**注意**：`checkXML6` 二进制来自 `kdoctools` 包，所以
`find_package(KF6 ... DocTools)` **要保留**；若把整个 kdoctools 依赖删掉，
测试会以 `checkXML6: inaccessible or not found`（Error 127）失败。

## 消费者验证

`test_package` 用自带的最小 DocBook 文档驱动完整往返：

| # | 步骤 | 断言 |
|---|---|---|
| 1 | 四个二进制存在可执行 | `split2po`/`xml2pot`/`po2xml`/`swappo` |
| 2 | `xml2pot sample.docbook` | 产出 POT 且含文档真实字符串 |
| 3 | `po2xml sample.docbook sample.po` | 产出合法 `<book>` XML |
| 4 | `split2po <英文XML> <译文XML>` | 拆回 PO |

**易错点**：`split2po` 需要**两个**参数（英文 XML + 译文 XML），
只传一个会报 `usage: split2po english-XML translated-XML`。

## 验证结果

- 上游：`100% tests passed, 0 tests failed out of 1`（裁剪后剩余 ctest）
- 消费者：`POXML-CONSUMER-OK`
