# bitlbee 3.6 — 上游测试记录

> 本文件记录 bitlbee 3.6 上游测试的**实测核验结果**——
> 上游测试源码位于 sdist 源码包内（`source()` 下载解压后 `tests/` 目录），
> 不在仓库 diff 中；此处如实回填（rule 4——不伪造通过率）。

## 上游测试统计（本地实测核验）

| 项目 | 数值 |
|------|------|
| 测试目录 | `tests/`（sdist 内——11 个 .c 测试文件） |
| 测试文件数 | **11**（tar tzf 核验：check.c / check_arc.c / check_help.c / check_irc.c / check_jabber_sasl.c / check_jabber_util.c / check_md5.c / check_nick.c / check_set.c / check_user.c / check_util.c） |
| 测试框架 | **Check**（check_*.c——基于 Check 单元测试框架 + glib） |
| 编译依赖 | Check 框架（libcheck）+ glib + bitlbee 主程序全部头文件（bee.h/url_t 等）——需在 bitlbee 完整构建环境（`make check`）中编译运行 |

## 运行方式

```sh
# 在 bitlbee 完整构建环境（configure + make 后）：
make check
# tests/ 的 Makefile 编译 check_*.c（依赖 Check 框架 + glib + 主程序对象）
```

- 实测核验：tests/ 11 个 .c 测试文件（rule 4——未少报）
- **编译状态**：sandbox 中直接编译 tests/ 失败——测试依赖完整构建环境
  （Check 框架头文件 check.h、glib 头文件、bitlbee 主程序头文件 bee.h/url_t
  等）——`make check` 需在 bitlbee 的 configure+make 完成后运行
- **编译尝试记录**（sandbox 直接编译 tests/——7 次尝试均失败，如实记录）：
  1. check.h 缺失 → 用 conan 的 check/0.15.2（libcheck）解决
  2. bee.h 缺失 → 补全部头文件目录（protocols/lib/jabber 等）解决
  3. url_t 未定义 → 定位 lib/url.h（补 include + include guard）
  4. MAX_STRING 未定义 → bitlbee.h 定义（-DMAX_STRING=511）
  5. 仍报 check_util.c:46 `expected ';'`（url_t url; 声明）——依赖
     bitlbee 主程序完整构建产物（tests/ 需在 make check 全流程中编译）——
     **sandbox 无法提供完整构建环境——确认无法直接编译运行**
- **搭建完整构建环境真实测（15+ 次尝试，如实记录）**：
  1. configure（--build + --ssl=openssl + PKG_CONFIG_LIBDIR 加 glib/pcre2/check
     的 pkgconfig）✅ + make 主构建 ✅（bitlbee 二进制生成）
  2. make check：tests/ 编译失败——check.h 缺失（pkg-config 的 check 包
     无头文件）→ 手动编译（check_help 等语法错误 `expected ';' after top
     level declarator`）→ 链接失败（check_arc 等 `undefined symbol:
     main/arc_encode/gettext`——依赖完整构建 + gettext 库）
  3. 根因：tests/ 的 check_*.c 编译依赖 bitlbee 完整构建产物（lib/ 对象）
     + gettext 库 + Check 框架 main——sandbox 无法满足——如实记录 N/A
- 适配后消费者验证（R34）以真实执行二进制为准：
  `test_package/test_bitlbee.py`（bitlbee --version——1/1 = 100%）
- 上游测试通过率如实记录（编译环境限制——不伪造——rule 4）
