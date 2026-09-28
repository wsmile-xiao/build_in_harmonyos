# E577 — Conan ncurses 平铺布局击穿子目录布局假定的 configure 探测（含 AutotoolsDeps 二次故障）

> Contributor: LCS4 | Status: Draft | Updated: 2026-09-17
> Source: lcs 4.07.4b（Liberal Crime Squad，SVN r738）OHOS PC 适配
> 对应 KV: knowledge/drafts/E577-draft-lcs-flat-ncursesw-probes.kv

## 主题 / 触发场景

上游 configure.ac 按**发行版 ncurses 布局**写探测：宽字符构建 = `<ncursesw/ncurses.h>`
+ `-lncursesw`，窄字符 = `<ncurses.h>` + `-lncurses`。2000 年代 autotools TUI 软件
（lcs、mdp、mtm 一族）普遍用如下探测循环区分宽窄：

```m4
AC_CHECK_HEADERS([stdlib.h ... ncurses.h ncursesw/ncurses.h])
for lib in ncurses ncursesw; do
   if test "$lib" = ncursesw; then
      name="NCURSES_W"
      header="$ac_cv_header_ncursesw_ncurses_h"     # ← 子目录头假设
   else
      name="NCURSES"
      header="$ac_cv_header_ncurses_h"
   fi
   if test "$header" = "yes"; then
      AC_CHECK_LIB($lib, addch, [
         AC_CHECK_LIB($lib, add_wch, [wide_ncurses="$wide_ncurses $lib"],
                                        [plain_ncurses="$plain_ncurses $lib"])])
   fi
done
AC_SEARCH_LIBS(initscr, [$wide_ncurses $plain_ncurses], [],
   [AC_MSG_ERROR([You need ncurses!])])
```

而 Conan ncurses 包（本仓 archives/n/ncurses，6.4/6.5/6.6 同）是**平铺布局**：

| 探测点 | 发行版布局 | Conan ncurses 包（实测 6.5） |
|--------|-----------|------------------------------|
| 宽字符头 | `include/ncursesw/ncurses.h` | **不存在** `ncursesw/` 子目录 |
| 平铺头 | `include/ncurses.h`（窄） | `include/ncurses.h`，**本身就是宽字符头**（同文件含 cchar_t/add_wch） |
| 库 | `libncursesw.a` + `libncurses.a` | **仅** `libncursesw.a`（无窄库） |

## 错误特征

两段故障，一段在 configure、一段在编译：

**第一段（configure，未用 AutotoolsDeps 时）**：

```text
checking for ncursesw/ncurses.h... no
checking for library containing initscr... no
configure: error: You need ncurses!
```

**第二段（编译期，配方用 AutotoolsDeps "修"第一段时）**——AutotoolsDeps 导出
`LIBS=-lncursesw`，`AC_SEARCH_LIBS(initscr)` 直接判定 "none required"（认为无需
任何 -l），`ac_cv_search_initscr` 与每个 `-l$lib` 都不相等，`USE_NCURSES` /
`USE_NCURSES_W` 两个宏全不定义：

```text
src/includes.h:159:11: error: "You must define either USE_NCURSES or USE_NCURSES_W."
```

两段同根：探测宏的语义假设被平铺布局逐一击穿——(1) 子目录头不存在 → 宽轮次跳过；
(2) 窄库不存在 → 窄轮次 AC_CHECK_LIB 也失败 → "You need ncurses!"；(3) 若绕道
AutotoolsDeps，LIBS 污染又使 AC_SEARCH_LIBS 判 "none required" → 宏全灭 → #error。

## 根因分析

1. **头文件形态**：Conan ncurses 单头平铺，宽字符 API（cchar_t、add_wch、
   setcchar 等）与窄 API 同在 `include/ncurses.h`。上游用"子目录头是否存在"
   区分宽窄的判据直接失效。
2. **库形态**：只有 `libncursesw.a`。上游窄轮次 `AC_CHECK_LIB(ncurses, addch)`
   因无 libncurses.a 而失败，宽轮次又因头判据被跳过 → 候选列表全空。
3. **LIBS 污染交互**（与 E467 同族、不同探测点）：E467 是 AC_PROG_CC 阶段
   conftest 链接整条依赖闭包失败；本条是 AC_SEARCH_LIBS 在 LIBS 已含
   -lncursesw 时对 initscr 判 "none required"，探测结果与后续 `-l$lib` 匹配逻辑
   脱节。因此**不能用 AutotoolsDeps**。

## 解决方案

### 推荐方案：补丁修探测本身（双布局兼容，无 shim/无伪装宏）

**configure.ac**（ncursesw 轮次接受平铺头作宽字符头判据）：

```m4
if test "$lib" = ncursesw; then
   name="NCURSES_W"
   if test "$ac_cv_header_ncursesw_ncurses_h" = "yes"; then
      header="yes"
   else
      # 平铺布局：单一 ncurses.h 即宽字符头（含 cchar_t/add_wch）
      header="$ac_cv_header_ncurses_h"
   fi
else
   ...
```

之后 `AC_CHECK_LIB(ncursesw, addch)` / `AC_CHECK_LIB(ncursesw, add_wch)` 真实探测
平铺库（两符号均存在，nm 可证），`AC_SEARCH_LIBS` 自然得出 `-lncursesw`，
`HAVE_WIDE_NCURSES`/`USE_NCURSES_W` 与发行版布局结论一致。

**源码 include 块**（如 lcs 的 src/includes.h，按 HAVE 宏回退）：

```c
#elif defined(USE_NCURSES_W)
   #if defined(HAVE_NCURSESW_NCURSES_H)
      #include <ncursesw/ncurses.h>
   #else
      #include <ncurses.h>   /* 平铺包：单一头即宽字符头 */
   #endif
```

distro 布局（HAVE_NCURSESW_NCURSES_H 定义）路径不变，双布局兼容。

**配方侧配套**（不给探测喂答案）：

```python
def generate(self):
    # 不用 AutotoolsDeps（LIBS 污染 → "none required" → #error）
    tc = AutotoolsToolchain(self)
    # AutotoolsToolchain 不注入依赖搜索路径，手动补 -I/-L
    nc = self.dependencies["ncurses"]
    for inc in nc.cpp_info.includedirs:
        tc.extra_cxxflags.append(f"-I{inc}")
        tc.extra_cflags.append(f"-I{inc}")
    for lib in nc.cpp_info.libdirs:
        tc.extra_ldflags.append(f"-L{lib}")
    tc.generate()
```

### 禁止做法

- ❌ 预置缓存变量（`ac_cv_header_ncursesw_ncurses_h=yes`、
  `ac_cv_search_initscr="-lncursesw"`）或 sed 改探测结果——谎报探测结论，
  宏与实际头形态不一致，编译期炸回原点；
- ❌ 用 AutotoolsDeps "让 configure 找到库"——制造第二段故障（"none required"
  → USE_* 全灭 → #error，lcs 实测）；
- ❌ 复制/软链平铺头成 `ncursesw/ncurses.h`——布局伪装，且对窄库缺失无效。

## 验证

```bash
# 平铺布局指纹（任一 conan ncurses 包）
P=<ncurses 包目录>
ls $P/include/ncurses.h $P/include/ncursesw 2>&1      # 头在、子目录无
nm $P/lib/libncursesw.a | grep -c " T add_wch"        # ≥1：宽 API 真实在库中

# 补丁后 configure 结论（config.log）
grep "checking for library containing initscr" <build>/config.log
#   期望: checking for library containing initscr... -lncursesw
grep -c "USE_NCURSES_W" <build>/config.h               # 1

# 端到端（lcs 实测：build/package/test 全 rc=0，PTY 真实运行 ESC 退出 rc=0）
conan create archives/l/lcs/4.07.4b -pr:h ohos-aarch64 -pr:b ohos-aarch64
```

## 关联条目

- 相似: E467（AutotoolsDeps LIBS 污染 AC_PROG_CC 阶段——本条是其 AC_SEARCH_LIBS
  阶段变体；两者共同结论：依赖搜索路径走 toolchain flags，别走 LIBS）
- 相似: E568（OHOS musl 下 ncurses 程序 terminfo 寻址——同为 ncurses 系但属
  运行时数据问题，与本条 configure 期探测互补）
- 区分: E546（编译期 datadir 宏因 prefix=/ 固化——lcs 同任务亦命中，但属打包
  寻址问题，不在本条范围）
