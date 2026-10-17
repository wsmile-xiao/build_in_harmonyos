# console-cyrillic 0.9 适配笔记（OHOS）

## 概述

console-cyrillic 是 Debian 西里尔语系控制台数据包（纯数据 + 脚本，无 C 编译）：
120 个 kmap 键盘映射（12 布局 × 10 编码）、44 个 PSF 控制台字体、8 个 sfm +
9 个 acm 字符映射表、8 个 screenmap、9 个 trans、fallback 回退、6 个工具脚本
（cyr/displayfont/dumppsf/makeacm/raw2psf/mkvgafont）与 man/doc。

Debian 3.0(quilt) 包，**orig 与 debian 两个 tarball 合并**为源根——kmap 生成
管线（makeenc 2844 行 bash+内嵌 perl + unicodesyms + 7 个布局 cpp + kazakh
子包）、option-kmap、screenmap、trans、fallback、binary 字体、cyr 脚本、5 个
quilt 补丁**全在 debian 树**；orig 只有 BDF 字体源 + 5 个工具脚本 + windows/
x-window 文档。

## 构建管线（conan build() 逐条复刻 debian/rules L42-89）

```
makeenc <enc> < unicodesyms | cat - <cpp>
  | clang-cpp [-DIO] -iquote . -iquote - -P   # OHOS: clang-cpp 替代 cpp
  | sed 's/+ *U+/U+/g' | grep '[^ ]'  >  <prefix>-<enc>.kmap
```

- **工作目录 keymap/**：rules 在包根以 `-iquote keymap/` 解析 `macros.inc`；
  本配方 cd 到 keymap/ 后 `-iquote .` 等价锚定。4 个 cpp（ua/ua_ms/mk/mn）
  `#include "macros.inc"`，该头在 keymap/ 下。
- **kaz_alt 额外 `-DIO`**（kazakh 变体开关，rules L88 专属）。
- **makeenc tmpfile**：上游 L2580 硬编码 `/tmp/csrec.$$`——OHOS /tmp 只读，
  改 `${TMPDIR:-.}/csrec.$$`，构建时 `export TMPDIR=$source_folder`。
- **clang-cpp 替代 cpp**：`-P`（预编译，去 #line 行标记）+ 双 `-iquote`。
  12 布局 × 10 编码 = 120 文件，每个断言 `keycode` 行数 ≥ 100。

## 黄金文件校验（强于抽样断言的可复现性证据）

解包官方 .deb（console-cyrillic_0.9-18_all.deb），120 个生成 kmap 与 .deb
黄金逐文件 diff——**0 差异**（归一化构建日期/姓名/时间戳行）。字体/字符映射/
screenmap/trans/fallback 直接拷贝，与 .deb bit 级一致（gzip -9 重压缩后 magic
一致）。落位计数断言：136 kmap / 44 psf / 8 sfm.gz / 9 acm.gz / 8 screenmap /
9 trans / 2 fallback.gz / 6 man1.gz / 6 bin。

## OHOS 适配点

1. **perl shebang**：`#!/usr/bin/perl`（4）+ `#!/usr/bin/perl -w`（displayfont）
   → `#!/usr/bin/env perl`。**-w 必须丢弃**——OHOS `env` 不支持解释器后带参，
   `env perl -w` 实测 `exec perl -w: No such file or directory`。-w 仅开警告，
   无副作用。
2. **/tmp 只读**：makeenc tmpfile 重定向 + test 临时文件落 `$PWD`。
3. **iconv 缺 4 编码**（ibm866/mac-cyrillic/pt154/mik）：windows 文档改用
   python3 codecs（覆盖 6 字节编码 + utf-8）；**pt154/mik 黄金 135B 静态字节
   嵌入配方目录**——debian 的 `pt154.acm` 是哈萨克变体（0x80→Җ 西里尔字母），
   与 .deb 黄金 windows/pt154 的字符集不符，acm 反查不可靠。
4. **cyrillic-graph.fallback**：rules L91-93 组合 = 头注释 + cyrillic.fallback +
   console-data 的 graph.fallback。console-data 尚无 conan 包——graph.fallback
   84 行从 .deb 黄金反解归档于配方目录，组合结果与 .deb bit 级一致。
5. **Pod::Man**：hnp perl 含 Pod::Man 模块（实测 OK），4 个 man 从 pod 源生成，
   等效 `pod2man -s 1`；2 个（cyr/mkvgafont）为 debian 预渲染 roff 直接落位。

## 上游测试

**0 个**。tarball 全树（orig + debian）核对：无 test/ 目录、debian/rules 无
check/override_dh_auto_test、无 Makefile check 目标、无 t/ 目录。R34 功能测试
由 test_package 承担。

## 边界（未适配 / graceful 降级）

| 项 | 状态 | 原因 |
|----|------|------|
| cyr 交互路径 | 降级 | 读 /etc/console/cyr + 调 kbd-config/loadkeys/dumpkeys（kbd 已声明，console-common 未合入）；无 Linux VT |
| displayfont | 降级 | 探测 /dev/console 与 vt 状态 graceful 退出（无参 RC=0 实测） |
| mkvgafont | 不可用 | 依赖 bdftopcf/compress（X tools，OHOS 无）——无参 RC=1 用法提示 |
| makeacm | 不可用 | 依赖 perl Unicode::String 模块（hnp perl 未含） |
| windows/pt154+mik | 黄金嵌入 | OHOS 无 pt154/mik 编码器，.deb 黄金 135B 字节嵌入 |
| graph.fallback 段 | 黄金嵌入 | console-data 尚无 conan 包，84 行黄金字节嵌入 |

## 脚本行为基线（OHOS 真机实测，无管道）

| 脚本 | 无参/帮助 RC | 说明 |
|------|-------------|------|
| cyr --help | 2 | 用法提示 |
| cyr 无参 | 2 | 用法提示 |
| displayfont | 0 | VT 探测 graceful 退出 |
| dumppsf | 2 | 用法提示 |
| makeacm | 2 | 缺 Unicode::String |
| mkvgafont | 1 | 用法提示 |
| raw2psf | 0 | 功能正常，输出 PSF1（魔数 36 04） |

## 依赖

- **kbd/2.9.0**（self.requires）：cyr 运行期消费 loadkeys/dumpkeys。
- console-common 尚未合入（cyr 调 kbd-config）——脚本对缺失工具 graceful 降级。
- 系统基础（不声明）：gzip/sed/awk/grep/perl(hnp)/iconv。
