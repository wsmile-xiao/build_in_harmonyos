# libgdsii 0.2-ds.1 适配笔记

## 编译环境
- 构建系统: autotools（GitHub tag 0.2 归档，无生成物 configure，需 autoreconf 自举）
- 编译日期: 2026-09-17
- 编译器: clang 15（OHOS aarch64）
- 状态: built

## 编译步骤
1. 上游核验：github.com/HomerReid/libGDSII tag 0.2；codeload tarball
   sha256=aec488d12a0d6a29a1ecfe61b66f96d05bf15b41546c0c6052939ae3a04375f7
   （任务版本 0.2-ds.1，配方/目录/分支三处版本串一致）。
2. W0：零运行时依赖（纯 C++ 标准库）；tool_requires 仅 automake/1.18 +
   libtool/2.5.4.1（CI 沙箱缺 automake/aclocal/libtoolize，argp-standalone 先例）。
3. 源码预检（~/tmp/uc2/libgdsii-0.2-ds.1/libGDSII-0.2）：autoreconf -fi 实测
   EXIT=0（仅 AM_CONFIG_HEADER/AC_HELP_STRING 废弃告警，兼容层可过）。

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | tag 归档无 configure | 上游只提交 configure.ac，发布未跑 autoreconf | 配方 build() 以 autoreconf -fi（conanbuild env + SH 前缀）自举；tool_requires automake/libtool |
| 2 | automake 1.18 严格模式报 `required file './ChangeLog' not found` | 上游树缺 ChangeLog（AM_INIT_AUTOMAKE 未用 foreign 模式） | 补丁 0001-am-init-automake-foreign.patch：AM_INIT_AUTOMAKE 加 [foreign] |
| 3 | configure 的 umask 077 mktemp 探针（E011/E114） | HMDFS 使 config.status 临时目录不可写 | autoreconf 后 replace_in_file 放宽为 umask 002 |
| 4 | hnp bash getcwd 损坏（E386 家族） | OHOS profile 的 SHELL/CONFIG_SHELL 指向它 | configure/make/install 以 env -u CONFIG_SHELL SHELL=/bin/sh 前缀 |
| 5 | config.sub 不识别 linux-ohos | 2019 年代 config.sub | --build/--host 均传 aarch64-unknown-linux-gnu（direvent/units 先例） |
| 6 | tarball 内 COPYING/INSTALL 为指向打包者本机的死链接 | 上游打包粗糙 | autoreconf/构建不受影响（实测）；产物不包含这两个文件，无需补丁 |
| 7 | configure.ac 的 AC_DISABLE_SHARED 在 libtool 2.5.4 再生成组合下未生效（实测包内出现 .so，消费者链接动态库后运行期 relocation 失败） | libtool 版本组合行为差异 | configure 显式 --disable-shared --enable-static --with-pic，package() 剥离 .so/.la，仅交付 libGDSII.a（实测消费者静态链接+运行通过） |

## CI checkout 兼容性处置（2026-09-17）

PR #10483 的 CI 连续 3 次（不同 worker）失败于 checkout-pr 步骤拉取
`pull/10483.diff` 超时，同期其他 PR 正常——差异点是本 PR diff 含 604 字节
二进制资产 bend-flux.gds。处置：资产以 C 字节数组（bend_flux_gds.h）内嵌，
消费者测试运行时写出后解析，归档恢复纯文本；资产内容不变（604 字节，
上游 examples/bend-flux/bend-flux.gds 原件）。

## 上游测试四维账本
- 上游静态声明总数：**0**（无 tests/ 目录；顶层 Makefile.am 无 TESTS/check-TESTS
  注册；lib/applications/examples 均无测试源）
- 实际执行：0（上游无可执行测试）
- 通过/失败/跳过：0/0/0（上游无自动化测试，如实申报）
- 新增消费者测试：1 个程序（test_package/test_libgdsii.cpp，CMake 消费者：
  find_package(libgdsii) + 链接 libgdsii::libgdsii，解析上游示例资产
  examples/bend-flux/bend-flux.gds，4 处断言：GetLayers 非空 / GetPolygons(-1)
  非空且首多边形坐标数 >= 6 / GetPolygons(layer) 非空 / GetTextStrings 可调用；
  任一失败退出码 1）

## 路径 A/B 判断
路径 A（基础适配）。判断依据：常规小型库适配，问题 1-5 均为已有知识库条目
（E011/E114/E386、autoreconf 自举、ohos triplet）的复用，无新的跨仓库可复用
知识增量，不满足路径 B 证据门槛（无新错误签名、无新解法）。
