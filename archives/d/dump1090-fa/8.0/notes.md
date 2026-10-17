# dump1090-fa 8.0 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile，无 configure 脚本）
- 编译日期: 2026-08-16
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤

```bash
# 源码：https://github.com/flightaware/dump1090/archive/refs/tags/v8.0.tar.gz
# SHA256: 082d09c10d40d0b9675555b9d496280d057f30872f79beda35b1391779f72965
make -j1 CC=clang CPPFLAGS="-I<ncurses-include>" LDFLAGS="-L<ncurses-lib>" \
     LIBS_CURSES="-lncursesw" DUMP1090_VERSION=8.0
# 产物：dump1090 / view1090 / faup1090 / starch-benchmark
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `interactive.c: fatal error: 'curses.h' file not found` | dump1090 交互模式无条件 `#include <curses.h>`，OHOS 系统无 ncurses 头文件 | 依赖制品仓已发布的 `ncurses/6.5` 静态包（R36 满足），配方显式传入 ncurses include/lib 路径 |
| 2 | 链接缺少 curses 符号 | OHOS `uname` 返回 HarmonyOS，Makefile 的 Linux 分支不生效，`LIBS_CURSES` 为空 | 配方显式传 `LIBS_CURSES="-lncursesw"`（ncurses 6.5 为宽字符静态包） |
| 3 | `-lrt` 未链接 | 同上，Linux 分支未生效 | OHOS libc 已提供相关符号，编译/链接/运行验证无需 `-lrt` |
| 4 | GitHub 直连超时 | 网络限制 | 本地通过 gh-proxy.com 镜像下载 tarball 并核验 SHA256 一致 |

## 源码修改

无（未修改任何上游源码，无需补丁；patches/ 为空）

## 依赖版本

- ncurses/6.5（制品仓已发布，静态宽字符包）

## 验证结果

```bash
# 上游测试：make test → cprtests（CPR 解码器测试）
#   cprGlobalAirborneTests: 2 用例
#   cprGlobalSurfaceTests:  23 用例
#   cprRelativeTests:       30 用例
#   合计 55 用例，全部 PASS（详见报告）
# 消费者测试：test_package/test_dump1090.sh（8 断言，见报告）
# conan create + conan-verify 门禁（见报告）
```

## 注意事项

- 产物为命令行工具（R38），软件级目录已创建 `commands.json`，声明 dump1090/view1090/faup1090/starch-benchmark
- OHOS 下 Makefile 不进入 Linux 分支，`CPUFEATURES` 默认 no → `STARCH_MIX=generic`，无需处理 cpu_features
- SDR 前端（rtlsdr/bladerf/hackrf/limesdr）均未在制品仓/系统出现，自动降级为 no，仅保留文件回放（--ifile）能力
---

**编译结束**: 2026-08-16 09:19
**最终状态**: built
