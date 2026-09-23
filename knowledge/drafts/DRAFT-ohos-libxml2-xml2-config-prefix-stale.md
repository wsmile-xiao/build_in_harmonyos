# DRAFT — conan libxml2 包内 `xml2-config` 前缀陈旧导致 autotools 探测静默降级

## 现象

采用 `xml2-config` 探测 libxml2 的 autotools 项目，在依赖制品仓 `libxml2/2.15.3.1` 时：

```
checking for xml2-config... yes
checking for xmlParseMemory in -lxml2... no
checking for libxml/tree.h... no
```

configure 没有报错，构建全部成功；但产物 `lib/lib<name>.so` 的 `DT_NEEDED` 里**没有**
`libxml2` —— 即项目按"无 libxml2"分支编译，XML 后端被静默丢弃。

## 根因

制品包内 `bin/xml2-config` 是该包**自身构建期残留**的脚本，头部硬编码 `prefix=/usr/local`：

```
$ <libxml2-pkg>/bin/xml2-config --cflags
-I/usr/local/include/libxml2
$ <libxml2-pkg>/bin/xml2-config --libs
-L/usr/local/lib -lxml2 -lpthread -lm -ldl
```

`AC_CHECK_PROG(xml2-config, …)` 型探测把这两条输出原样写入 `CPPFLAGS` / `LIBS`，
后续 `AC_CHECK_LIB(xml2, xmlParseMemory)` 与 `AC_CHECK_HEADER(libxml/tree.h)` 双双失败
（`/usr/local` 下并无该包的头与库），于是 `HAVE_XML2` 未定义。

## 修复

1. 预置 `HAVE_XML2_CONFIG=no`（`AC_CHECK_PROG` 在变量已赋值时不再搜索程序），迫使项目走自身回退分支；
2. 用容器内真实路径补齐：`CPPFLAGS += -I<dep>/include/libxml2 -I<dep>/include`，`LDFLAGS += -L<dep>/lib`
   （路径取 `self.dependencies["libxml2"].cpp_info`）；
3. 不要由配方把依赖的 `bin/` prepend 到 `PATH`（正是这一步让陈旧脚本生效）；
4. 收尾验证必须看产物：`readelf -d … | grep libxml2` —— m17n-lib 在 `HAVE_XML2≠yes` 时会清空
   `XML2_LD_FLAGS`，因此 `DT_NEEDED libxml2.so.16` 是"后端真正启用"的可靠判据；
5. 顺带把 `PKG_CONFIG_PATH`/`PKG_CONFIG_LIBDIR` 收敛到 conan 生成目录，避免宿主 `.pc` 混入链接串。

## 实测（libm17n-core 1.8.6 / 上游 m17n-lib）

| 阶段 | configure 探测 | 产物 DT_NEEDED |
|---|---|---|
| 修复前 | `xmlParseMemory in -lxml2... no`、`libxml/tree.h... no` | 无 libxml2（仅 libc） |
| 修复后 | 通过 | `libxml2.so.16`, `libz.so`, `libc.so` |

`conan create`（OHOS aarch64）EXIT=0；`test_package/test.c` 56 项核心 API 断言在原生构建上 0 失败。

## 适用范围

- 所有用 `*-config` 脚本（xml2-config、curl-config、freetype-config…）探测 conan 依赖的 autotools 配方；
- 所有"构建成功但功能缺失"的排查场景。
- 不适用：走 pkg-config 或 CMake config-file 的依赖消费方式；制品仓已在打包阶段把 `*-config`
  prefix 就地改写为包内真实路径的依赖包。

## 与既有知识的关系

`xml2-config` 在 knowledge/ 中 0 命中；`rpl_malloc`（同次适配的另一条结论）见
`DRAFT-ohos-autotools-rpl-malloc`；config.guess/HarmonyOS 识别见 E007/E160/E533/E545 与
`DRAFT-hogweed-3.9.1-ohos-config-and-dependency-recovery`（其 HMDFS `mktemp` 目录内
`dummy.c` Permission denied 属另一故障面）；libintl 空壳见
`DRAFT-ohos-gi18n-gettext-identity-macro`。本稿新增价值核心是"**陈旧 `*-config` →
静默缺失功能 → 构建与测试皆绿**"这一模式及 `DT_NEEDED` 判据。
