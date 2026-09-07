# DRAFT: IT_PROG_INTLTOOL 类库在 OHOS 的 intltool 工具链 stub

- **草稿 ID**: `DRAFT-ohos-intltool-toolchain-stub`
- **触发软件**: dbustest (dbus-test-runner) 19.04.0
- **状态**: DRAFT（待主编/AI 审核提升为 E 条目）
- **姊妹条目**: E135（libintl.so.8 运行时 ELF 签名，问题层不同、互补）

## 问题

autotools 库的 `configure.ac` 声明 `IT_PROG_INTLTOOL([0.35.0])` 时（如
dbustest/dbus-test-runner 19.04.0），生成的 configure 脚本强制检查两类工具：

1. **GNU gettext 工具**：`xgettext` / `msgmerge` / `msgfmt` 三者都必须存在，
   且 `--version` 输出含 `"(GNU"`，否则报
   `configure: error: GNU gettext tools not found; required for intltool`。
2. **perl + XML::Parser**：`perl >= 5.8.1` 且 `perl -e "require XML::Parser"`
   必须成功，否则报
   `configure: error: XML::Parser perl module is required for intltool`。

### OHOS 上的现状

| 检查项 | OHOS 状态 |
|--------|-----------|
| xgettext | ✅ 存在（/data/service/hnp/bin） |
| msgfmt | ✅ 存在（/data/service/hnp/bin） |
| **msgmerge** | ❌ **系统缺失**；gettext/0.22.5 conan 包只装 libintl.a + 头文件，不装 gettext-tools |
| perl >= 5.8.1 | ✅ 存在（5.42.0） |
| **perl XML::Parser** | ❌ **CPAN XS 模块缺失**；OHOS 无预编译包且需 libexpat 源码编译，不可装 |

两个缺失叠加，使 `IT_PROG_INTLTOOL` 类库 configure 必败。

## 方案（conanfile.py build() 内联，无需外部补丁文件）

### 1. msgmerge stub 前置 PATH

```bash
# 可写目录下创建 msgmerge，内容：
#!/bin/sh
echo 'msgmerge (GNU gettext-tools) 0.22.5'
exit 0
chmod 755 <stubbin>/msgmerge

# configure 时：
./configure PATH=<stubbin>:$PATH ...
```

`IT_PROG_INTLTOOL` 的 msgmerge 检查只跑
`$MSGMERGE --version | grep '(GNU '`，stub 返回的 GNU 版本字符串可骗过检查
（xgettext/msgfmt 用系统真实工具）。

### 2. XML::Parser stub 注入 PERL5LIB

```bash
# <stubdir>/XML/Parser.pm，内容：
package XML::Parser;
our $VERSION = '2.44';
1;

# configure 时：
./configure PERL5LIB=<stubdir>:$PERL5LIB ...
```

检查只跑 `perl -e "require XML::Parser"`，stub 使 require 成功。

### 3. --disable-nls 跳过 po/ 翻译

`po/` 目录的翻译产物（.po → .gmo）由 intltool-update 驱动，OHOS 不需要。
`--disable-nls` 后 make 阶段 po/ 不实际构建翻译产物，stub 只需骗过 configure
检查即可。**注意**：若 `Makefile.am` 的 SUBDIRS 无条件含 po，需确认
`--disable-nls` 下 make 不实际调用 msgmerge/intltool-update 生成 .gmo。

### 4. 依赖注入对齐

`IT_PROG_INTLTOOL` 之后 configure.ac 才有
`PKG_CHECK_MODULES(DBUS_TEST_RUNNER, glib-2.0 ... dbus-glib-1)`——若依赖 .pc
缺失，会在 intltool 检查通过后卡在 `No package 'xxx' found`。需同步保证
PKG_CONFIG_PATH 含全部依赖（含 glib 的 Requires 链 pcre2 等）。

## 验证

dbustest 19.04.0：conan-verify 全门禁 PASS（G0-G5/L2/L4/L5），test_package
编译链接成功（构造/析构 API 校验）。configure 输出关键行：

```
checking for msgmerge... <stubbin>/msgmerge
checking for XML::Parser... ok
--disable-nls 后 make 正常，po/ 翻译不构建
```

## 推广价值

适用于任何 `IT_PROG_INTLTOOL` 类库（GNOME/ayatana/Unity 系：dbustest、
libayatana-*、GNOME 组件）在 OHOS（无 gettext-tools + 无 perl XML::Parser）
的适配。与 E135（libintl.so.8 运行时签名）互补——E135 覆盖运行时加载，
本条目覆盖 configure 阶段工具链检查。

## 相关条目

- E135：libintl.so.8 运行时 ELF 签名（不同问题层）
- E007/E160/E205：config.guess/config.sub OHOS 识别
- DRAFT-ohos-la-libdir-hardcode：依赖包 .la libdir 硬编码重定位
