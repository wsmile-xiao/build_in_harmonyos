# udunits 2.2.28.1 适配笔记（conan 配方）

## 编译环境
- 构建系统: autotools + libtool
- 编译日期: 2026-09-09
- 编译器: clang 15.0.4 (OHOS arm64)
- 状态: built（conan 配方适配）

## Conan 配方要点

- 源码 URL: https://github.com/unidata/UDUNITS-2/archive/refs/tags/v2.2.28.tar.gz
- 依赖: expat/2.8.2.1（configure 硬依赖，AC_SEARCH_LIBS XML_StopParser）
- tool_requires: autoconf/2.72 automake/1.18 libtool/2.5.4

### 构建流程（build() 内）

release tarball 只有 configure.ac 无预生成 configure，配方显式重建：

1. `libtoolize --copy --force`（configure.ac 用 LT_INIT，生成 build-aux/ltmain.sh）
2. `aclocal --force -I m4`
3. `autoconf --force`
4. `autoheader --force`
5. `automake --add-missing --copy --force-missing`
6. configure 前删除 tarball 自带旧 aclocal.m4（避免 automake 版本不匹配）
7. E129 umask 修复：configure/config.status 中 `umask 077` → `umask 022`（HMDFS setgid）

## 平台适配关键问题

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | autoreconf 链中 perl 报 `Can't load Cwd.so: Permission denied` | Conan perl 包 XS 模块无法在 HMDFS dlopen（属主 20001006 vs 进程 uid 20020179，770 权限） | 用原生 OHOS perl（/data/service/hnp/bin/perl）+ PERL5LIB 仅指向 automake share 纯 perl 模块（ding-libs 0.7.0 先例）；显式分步 aclocal/autoconf/autoheader/automake 替代 autoreconf |
| 2 | automake wrapper 报 `//share/automake-1.18` 路径错误 | HMDFS getcwd 失效，wrapper 的 `cd $(dirname $0) && pwd` 推算 libdir 失败 | 命令前缀发布逻辑 PWD（POSIX pwd -L 用 $PWD 免 getcwd） |
| 3 | configure conftest 报 `cannot run C compiled programs` | conftest 链接 -lexpat 后运行时找不到 libexpat.so.1（conanbuild 环境 LD_LIBRARY_PATH 未含 expat lib） | Environment 注入 expat lib 到 LD_LIBRARY_PATH |
| 4 | makeinfo 缺失 | CI 无 texinfo | MAKEINFO=true 跳过 .info 文档生成（非链接接口） |
| 5 | conan-verify E017 注入 ghfast.top 镜像下载源码超时 | ghfast.top 镜像当前不可达（HTTP 000） | 官方源 github.com 可直连；W3 build_and_test.sh 用 gh-proxy.com（可达）验证通过 |

## 测试情况

- 上游 make check：lib 目录 0 注册用例（CUnit 未检测到），prog/ 下 udunits2 smoke test 启动正常、XML 数据库加载成功
- test_package 自研 20 项断言（14 CHECK + 6 near_eq）全部通过（test.c：XML 加载/单位查找/转换器/数值转换/反向/温度换算/不兼容拒绝/可转换性）

## 产物

- libudunits2.a / libudunits2.so.0.1.0
- 头文件: udunits2.h, converter.h, udunits.h
- udunits2 CLI 工具 + XML 单位数据库（share/udunits/）

---
**编译结束**: 2026-09-09
**最终状态**: built
