# paps 0.8.0 - HarmonyOS PC 适配笔记

## 编译环境
- 构建系统: meson (>= 0.44，设备 meson 1.12.0 / ninja 1.13.1)
- 编译日期: 2026-09-04
- 编译器: clang/clang++ 15.0.4（/data/service/hnp/bin，llvm 工具链）
- 状态: built
- 积分归类: 【依赖项】正常适配（平台任务 feat/paps-0.8.0）

## 上游事实

- 官方仓：github.com/dov/paps；tag v0.8.0 = commit
  f4052cac47583969f4839b384d21d315e6da188d（GitHub API 实测）
- 源码：GitHub 自动归档 tar.gz，SHA-256
  8fd8db04e6f8c5c164806d2c1b5fea6096daf583f83f06d1e4813ea61edc291f
  （设备 curl 下载实测一致）
- 许可证：LGPL-2.0（COPYING.LIB 为 LGPL 2.0 全文；paps.cc 头部注释含
  "GNU Library General Public License" 措辞，均为 LGPL 家族）
- 语言：C++（src/paps.cc 1854 行 + format_from_dict.cc 114 行；
  R47 lang-preflight 实测 detected=cpp，任务语言 cpp 匹配）
- 体量：75KB tar.gz，超小
- 测试入口：无——上游 meson.build 未注册任何 test() 目标，无 tests/ 目录，
  上游仓库无 CI 测试套件（GitHub Actions 无）

## 构建产物

- `paps` 可执行文件（bin/paps）——文本转 PostScript/PDF/SVG 命令行工具
- R38：含可执行文件，软件级 archives/p/paps/commands.json 已声明（type=tool）
- 辅助数据：share/paps/pango_markup.outlang + bin/src-to-paps（python 脚本，
  依赖 source-highlight，独立于主二进制）
- 无库文件（package_type=application）

## 依赖与解析

| 依赖 | meson 声明 | 采用（制品仓实测） | 说明 |
|------|-----------|-------------------|------|
| fmt | `dependency('fmt')` | fmt/12.2.0（shared, libfmt.so.12） | subprojects/fmt.wrap 是 fallback，被 wrap_mode=nodownload 禁用；pkg-config 解析 conan 包 |
| pangoft2 | `dependency('pangoft2')` | pango/1.50.14.1.1（shared） | .pc 修复目录提供 pangoft2.pc |
| pangocairo | `dependency('pangocairo')` | pango/1.50.14.1.1（shared） | 同上，pangocairo.pc |
| glib-2.0 | `dependency('glib-2.0')` | glib/2.84.0.1（shared，传递自 pango，显式声明） | .pc 修复目录提供 glib-2.0.pc |
| gobject-2.0 | `dependency('gobject-2.0')` | glib/2.84.0.1（shared） | 同上，gobject-2.0.pc |

## 编译步骤

```bash
# conan create（host/build 同 ohos-aarch64 profile）
# ⚠️ 设备 shell 默认 LD_LIBRARY_PATH 含空格（chipset-pub-sdk:   <空格>/system/lib64），
# musl 动态链接器解析失败 → ninja 加载 libc++_shared.so 报 rc=127，
# meson 因此报 "Could not detect Ninja v1.8.2 or newer"（gssdp E 系同款实撞）。
# 需重设为无空格路径：
export LD_LIBRARY_PATH="/system/lib64/platformsdk:/system/lib64/chipset-pub-sdk:/system/lib64:/system/lib64/ndk"
conan create archives/p/paps/0.8.0 \
  -pr:h=$HOME/.conan2/profiles/ohos-aarch64 \
  -pr:b=$HOME/.conan2/profiles/ohos-aarch64 \
  --build=missing
```

## 关键适配点

### 1. .pc 解析策略（第 3 轮定稿：标准 PkgConfigDeps 流）

~~早期方案（pc-fix）：复制 glib/pango/fmt 包内 lib/pkgconfig/*.pc 到
build_folder/pc-fix/ 并重写 prefix=，MesonToolchain 的 pkg_config_path
指向该目录。~~ **已废弃**：那些上游 .pc 携带跨包 Requires 链
（glib-2.0.pc → Requires.private: libpcre2-8 >= 10.32 指向 pcre2 包；
gobject-2.0.pc → libffi；pango*.pc → harfbuzz/fribidi/cairo...），
pc-fix 目录里没有这些包的 .pc，pkg-config 严格解析失败：
`Package 'libpcre2-8', required by 'glib-2.0', not found`（第 2 轮
卡点实况）。逐个补又会链式暴露下一个缺失（去掉 pcre2 → 缺 libffi →
缺 harfbuzz...）。

**最终方案**：删掉 pc-fix，回归 conan 标准流——PkgConfigDeps 为整个
可见依赖图生成组件级 .pc（pangoft2.pc/pangocairo.pc/glib-2.0.pc/
gobject-2.0.pc/fmt.pc 全套，prefix 已指向真实包目录，无跨包 Requires
链），MesonToolchain 默认 pkg_config_path 即 generators 目录。实测
pkg-config 在该目录下 --cflags/--libs 全链解析成功（glib 2.84.0.1
包的 glib-2.0.pc 含 Requires.private: libpcre2-8，但 PkgConfigDeps
生成版是干净的无 Requires 版本）。pango 1.50.14.1.1 配方声明了
components（pango/pangoft2/pangocairo 各带 pkg_config_name），组件级
.pc 全套生成。

### 2. wrap_mode=nodownload

上游 subprojects/fmt.wrap 指向 fmt 9.1.0 wrapdb。当 pkg-config 解析
`dependency('fmt')` 成功时 meson 不会用 subproject；显式设
wrap_mode=nodownload 保证即便解析顺序异常也绝不联网下载（构建封闭性）。

### 3. AR/AS/STRIP/NM/RANLIB 坏环境变量

CI worker 导出 llvm-* 名字的工具变量但不在 PATH。generate() 里
os.environ.pop + shutil.which 定位真实 GNU 工具钉绝对路径（复刻
gssdp/glib2/libsoup3 先例）。tc.strip=None：绝不 strip 产物——OHOS
loader 校验 .codesign 哈希。

### 4. fmt 12 移除 fmt::localtime（补丁 fmt12-localtime-gmtime.patch）

上游 src/format_from_dict.cc:57 用 `fmt::localtime(val)` 格式化
header 模板里的 {mtime}/{now}（time_t）。fmt 12 彻底移除 localtime
（chrono.h 中无任何 localtime 符号，FMT_VERSION 120200 实测）。
改用 `fmt::gmtime(val)`（fmt 12 保留，线程安全变体）。语义差异仅
时区（本地时区→UTC），影响 PostScript 页眉时间戳的时区显示，
非功能性。fmt/11.1.3 虽有 localtime，但制品仓只发了 11.1.3 配方
且降版本会连带 pango/harfbuzz 生态重排，patch 一行是最小改动。

### 5. glib 2.78+ const-correctness（补丁 glib-const-g_utf8_next_char.patch）

glib ≥ 2.78 把 g_utf8_skip 声明为 const，`g_utf8_next_char(p)` 宏
展开 `(p) + g_utf8_skip[...]` 返回 const char*。上游
split_text_into_paragraphs 里 `char *next = g_utf8_next_char(p);`
在 clang 15 下报 "assigning to 'char *' from 'const char *' discards
qualifiers"（paps.cc:1118）。next 变量全函数只读使用（1118/1132/
1133/1204/1205/1242/1253 行均为读），改 `const char *next` 零语义
变化。

### 6. libintl 链接（g_libintl_* 未定义符号）

paps.cc include <libintl.h>（第 55 行）+ glib/gstdio.h → glib 包自
带的 libintl.h（proxy-libintl）把 gettext/textdomain 等 #define 重
映射为 g_libintl_* 前缀符号。glib 包的 libglib-2.0.so NEEDED
libintl.so.8（运行时自动解析），但链接期 ld.lld --no-undefined 需要
显式 -lintl——glib recipe 的 package_info 未声明 libintl 组件，
PkgConfigDeps 的 glib-2.0.pc 也不带 -lintl，导致第 5 轮 17 个
g_libintl_* undefined symbol。

修复：generate() 里 tc.extra_ldflags += ["-L<glib_pkg>/lib",
"-lintl", "-Wl,-rpath,<glib_pkg>/lib"]。rpath 必不可少——meson
configure 的 sanity check 会链接并**运行**测试二进制，无 rpath 时
musl loader 找不到 libintl.so.8（不在任何默认搜索路径），configure
直接报 "Executables created by c compiler ... are not runnable"
（第 6 轮实况）。

### 7. 运行时自包含 + 签名链（$ORIGIN 转义陷阱）

paps 可执行文件 NEEDED libfmt.so.12 + pango 全套共享栈。package()
把直接依赖三包（fmt/pango/glib）lib/ 下全部 .so 拷进包内 lib/，
重建 soname symlink 链，patchelf 注入 $ORIGIN/../lib DT_RUNPATH。

**两个铁的坑**：
1. `self.run()` 走 shell，patchelf --set-rpath "$ORIGIN/../lib" 里
   未转义的 $ORIGIN 被双引号展开为空 → RUNPATH 变成 "/../lib"
   （第 7 轮实况，loader 找不到任何库）。必须写 '\\$ORIGIN/../lib'。
2. patchelf 改写 ELF 后 .codesign 段哈希失效 → OHOS loader 拒绝
   执行（"Operation not permitted"）。必须在 rpath 修复后用
   binary-sign-tool 重新自签（llvm-objcopy --remove-section .codesign
   + binary-sign-tool sign -selfSign 1，glib recipe 先例）。

### 8. fontconfig 字体目录（FONTCONFIG_FILE 注入）

第 8 轮发现：转换"成功"但输出空白（8309 字节 PS、0 字形、8 页全空）。
根因：conan fontconfig 包的 etc/fonts/fonts.conf 只列 /usr/share/fonts
等目录，OHOS 设备不存在 → pango 找不到任何字体 → 所有字符静默不渲染。
fontconfig 运行时按 FONTCONFIG_FILE env > FONTCONFIG_PATH env >
编译时默认路径（sysroot /etc/fonts/fonts.conf，不存在）找配置。

修复：package() 在包内 res/ 生成 fonts.conf（\<dir>/system/fonts\</dir>
——OHOS 设备 /system/fonts 有 262 个字体，含全套 Noto + HarmonyOS
Sans + 方正中文），package_info() 的 runenv_info.define_path("FONTCONFIG_FILE",
...) 导出。注入后同一二进制 68504 字节 PS 输出、11 个 Type42 字体
真实嵌入（NotoSansHebrew/NotoSansArabic 等多语言全渲染）。

test_package 断言同步修正：旧断言 grep "BeginFont|/paps|UserFont|Glyph"
匹配的是 paps 老版本（cairo user-font）的输出格式；cairo 1.18 实际
嵌入 Type42（%%BeginResource: font NotoSans...），断言更新为
"BeginFont|BeginResource: font|FontType 42|/paps|UserFont|Glyph"。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson "Could not detect Ninja v1.8.2 or newer" | 平台默认 LD_LIBRARY_PATH 含空格，musl loader 解析失败，ninja 启动 rc=127 | export 无空格 LD_LIBRARY_PATH（含 /system/lib64） |
| 2 | dependency('pangoft2') 解析失败 "Package libpcre2-8 not found"（第 2 轮卡点） | pc-fix 方案的上游 .pc 携带跨包 Requires 链（glib-2.0.pc → pcre2 包的 libpcre2-8），pc-fix 目录无此 .pc | **删除 pc-fix**，回归 PkgConfigDeps 标准 .pc（组件级全链干净，实测全解析） |
| 3 | meson 探测 AR=llvm-ar 等失败 | CI 环境变量指向 PATH 外工具 | generate() pop 坏变量 + which 定位真实工具钉绝对路径 |
| 4 | meson 可能触发 subprojects/fmt.wrap 联网下载 | fmt.wrap 是 fallback | -Dwrap_mode=nodownload（pkg-config 成功解析时本就不用 wrap） |
| 5 | fmt::localtime 编译错误（第 3 轮） | fmt 12 移除 localtime | patch: fmt::localtime → fmt::gmtime（时区语义微变，非功能） |
| 6 | g_utf8_next_char 赋值丢弃 const 限定符（第 3 轮） | glib 2.78+ g_utf8_skip 改 const，宏产出 const char* | patch: char *next → const char *next（全函数只读，零语义变化） |
| 7 | ld.lld 17 个 g_libintl_* undefined symbol（第 4 轮） | glib 包 libintl.h 宏重映射 gettext→g_libintl_*；package_info 未声明 libintl，.pc 不带 -lintl | extra_ldflags += -L\<glib\>/lib -lintl -Wl,-rpath,\<glib\>/lib |
| 8 | meson sanity check "Executables ... not runnable"（第 6 轮） | -lintl 注入后 sanity 二进制 NEEDED libintl.so.8，loader 无 rpath 找不到 | 同 7：链接行附带 -Wl,-rpath 指向 glib 包 lib |
| 9 | 运行时 "Operation not permitted"（第 7 轮） | patchelf 改写 ELF 后 .codesign 哈希失效，OHOS loader 拒绝执行 | rpath 修复后 binary-sign-tool 重新自签（glib 先例） |
| 10 | RUNPATH 变成 "/../lib"（第 7 轮） | self.run 走 shell，"$ORIGIN" 双引号内展开为空 | patchelf 参数写 '\\$ORIGIN/../lib'（转义） |
| 11 | 转换成功但输出空白 8309 字节 0 字形（第 8 轮） | fontconfig 无字体配置（包内 fonts.conf 只列 /usr/share/fonts，OHOS 不存在），pango 静默零渲染 | package() 生成 res/fonts.conf（/system/fonts 262 字体）+ runenv FONTCONFIG_FILE；产出 68504 字节 11 个 Type42 字体 |
| 12 | test 断言 grep BeginFont/UserFont 不命中（第 8 轮） | cairo 1.18 嵌 Type42（%%BeginResource: font），非老版 user-font | 断言模式扩为 BeginFont|BeginResource: font|FontType 42|... |
| 13 | 可执行文件运行期找不到 libfmt/libpango | OHOS musl loader 忽略 LD_LIBRARY_PATH 场景 | 包内 lib/ 拷贝共享库 + patchelf DT_RUNPATH $ORIGIN/../lib；test_package 兜底 conanrun env |

## 补丁说明

两补丁均为对新版依赖（fmt 12 / glib 2.78+）的上游源码兼容性修复，
非平台特化：musl/clang 15 层面无平台问题（langinfo/nl_langinfo/
setlocale/wcwidth 在 musl 均有）。R6 合规：补丁为标准 unified diff，
经 conandata.yml patches 段声明 + apply_conandata_patches 机制应用，
可复现。
---

**编译结束**: 2026-09-05 00:34
**最终状态**: built
