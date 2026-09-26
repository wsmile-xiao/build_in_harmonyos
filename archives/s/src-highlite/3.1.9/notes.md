# src-highlite 3.1.9 适配笔记

## 编译环境
- 构建系统: autotools（tarball 自带 configure，2019 生成）
- 编译日期: 2026-09-21
- 编译器: clang/clang++（OHOS SDK aarch64，`tools.build:compiler_executables`）
- 状态: built

## 编译步骤
1. W0：唯一依赖 boost::regex 为 configure 硬依赖（AX_BOOST_BASE/AX_BOOST_REGEX）。
   制品仓实测（conan install --build=never）：boost/1.90.0.3 等新版本发布二进制
   **不含 libboost_regex**；boost/1.85.0（手动编译 filesystem/regex/
   program_options/iostreams 四库的变体）发布二进制含 `libboost_regex.a` →
   配方钉 `boost/1.85.0`。
2. 语言预检 lang-preflight：cpp（126/165 源文件，76%）PASS。
3. 探索构建（真机 -j1，memcap 预算内）：configure → make → install DESTDIR →
   `make -C tests check` 全绿（CHECK_RC=0）。
4. 配方：`conan-init` 骨架 + 手工改写（application 型 + commands.json +
   直接编译式消费者测试）；conan-verify 8 门禁全过。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess(2017-08-08) 报 unable to guess | 2017 老版脚本不识别 HarmonyOS（E007） | 见下第 2 条，补丁一并修 |
| 2 | `patch-autotools-ohos.pl` 打补丁后**仍**报 unable to guess | 脚本插入的是新式 `GUESS=` 分支（依赖 2018+ 的统一回显）；旧式脚本每 arm 自己 echo+exit，赋值后滑落到兜底 | 改写为旧式分支 `echo ${MACHINE}-unknown-linux-ohos; exit ;;`；沉淀草稿 DRAFT-src-highlite-3.1.9-config-guess-oldstyle-arm |
| 3 | configure 校验三元组时 config.sub(2019) 报 Invalid configuration | OS 表/kernel 表无 ohos | config.sub kernel 表加 `linux-ohos*`、OS 表加 `-linux-ohos*`（规范化输出 aarch64-unknown-linux-gnu-ohos，`$host_os` 仍以 linux* 匹配） |
| 4 | config.status 建临时目录后写文件 Permission denied | configure `umask 077 && mktemp -d` 在 HMDFS 上产生不可写目录（E011 家族） | 补丁把两处 umask 077 → 022（同 yaz 0001 补丁口径） |
| 5 | `pthread_setcancelstate` undeclared（boost 头） | OHOS sysroot pthread.h 无该声明（E507 机制）；boost ≥1.85 宏名已改为 `BOOST_SP_NO_PTHREAD_SETCANCELSTATE` | `-std=c++14` 之外追加 `-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE`（boost/1.85.0 配方也已通过 boost_headers 组件下发该 define） |
| 6 | `throw(X)` 动态异常规范在 cppstd=17 硬错 | 2015 年代 C++（检查清单 #14） | extra_cxxflags 追加 `-std=c++14`（在 profile 的 -std 之后，clang 取后值） |
| 7 | 消费者测试 `srchilite/sourcehighlight.h not found` | 包名带连字符（src-highlite）时 CMakeDeps 生成的 config 引用非法 CMake 变量 `${src-highlite_*}`，include/lib 路径全空 | test_package 改直接编译（clang++ + dependencies cpp_info 路径），同 libodb-pgsql 2.4.0 先例 |
| 8 | consumer_test 断言失败（output lacks expected markup） | 断言写错：默认 html.outlang 产物是 `<font color=…>`/`<pre>`，不是 `<span>` | 断言改为 main/comment 正文 + `<font` + `<pre>` |

## 源码修改

- `patches/0001-config-scripts-ohos.patch`（31 行）：build-aux/config.guess
  插入旧式 HarmonyOS 分支；build-aux/config.sub 补 linux-ohos kernel/OS 表项。
- `patches/0002-configure-hmdfs-umask.patch`（17 行）：configure 临时目录
  umask 077→022（HMDFS 兼容）。
- 配方内（非补丁）：`-std=c++14`、`-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE`
  （仅 OHOS 分支）。
- 无 `__OHOS__` 平台宏，无源码文件改动。

## 依赖版本

- boost/1.85.0（静态 libboost_regex.a；transitive: zlib/1.3.1 走 iostreams）

## 上游测试五维账本

| 维度 | 数量 | 说明 |
|---|---|---|
| N_static | 170 | tests/Makefile.am 默认 check 目标（`check: check-produced-output`，98 个 check_* 子目标）展开为 168 组"生成文件 vs 期望输出"diff 对比 + output_dir 子目标 2 组；按 Makefile.am 注册入口与运行日志双重计数 |
| N_registered | 170 | 与 N_static 同（默认 check 目标无条件跳过项） |
| N_executed | 170 | `make -C tests check -j1`（探索构建与 conan create 内各跑一遍），CHECK_RC=0 全过 |
| 未执行分类 | 3 类 | ①错误类 5 目标（check_wrong/check_missing/check_wrong_lineranges/check_wrong_regexranges/check_wrong_syntaxmode）= 上游 `if MAINTAINER_MODE` 条件注册，上游默认 make check 亦不执行；②src/ 的 `--check-lang/--check-outlang` 循环（~25 个语言定义合法性自检，无输出断言）；③doc/ 的 11 个示例文档生成（无断言）。三类均为上游自身定义，非本适配删减 |
| N_consumer | 1 | test_package 消费者程序 consumer_test（断言 4 项：产物可读 + main/comment 正文 + `<font`/`<pre>` 高亮标记），真实编译+链接静态库+签名+运行，退出码判定 |

## 验证结果

```bash
# 探索构建（真机）
./configure --prefix=... --with-boost=<conan boost prefix> --enable-static --disable-shared
make -j1 && make install DESTDIR=...   # MAKE_RC=0 / INSTALL_RC=0
make -C tests check                     # CHECK_RC=0（170/170）

# conan 门禁（ohc-run.py conan-verify src-highlite 3.1.9）
# G0/G1/G2/G3 + L2/L4/L5 全 PASS；消费者输出: consumer_test: highlighted 478 bytes OK
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/source-highlight | 主 CLI（静态链接 libsource-highlight.a + libboost_regex.a） |
| bin/chklang、bin/check-regexp 等工具 | 随 install 产生的命令行工具（commands.json 已声明） |
| lib/libsource-highlight.a | 静态库（默认 --disable-shared） |
| include/srchilite/*.h | 公共头文件 |
| share/source-highlight/ | 语言定义数据目录（消费者测试经 setDataDir 使用） |

## 注意事项
- 下游消费者若走 CMake：包名含连字符时 CMakeDeps 变量名非法，参考
  libodb-pgsql 2.4.0 的直接编译式消费者写法。
- boost 选型必须钉 1.85.0：1.90.0.x 制品无 regex（本 notes 上文）。
- 头文件含 `throw(X)`：消费者编译需 `-std=c++14`（或等效）。
- 消费者链接静态 libsource-highlight.a 时需同链 libboost_regex.a
  （链接序 `-lsrchilite -lboost_regex`）。
---

**编译结束**: 2026-09-21 14:59
**最终状态**: built
