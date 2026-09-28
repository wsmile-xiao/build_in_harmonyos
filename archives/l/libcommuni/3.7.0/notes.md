# libcommuni 3.7.0 适配笔记

## 编译环境
- 构建系统: qmake（libcommuni.pro，经上游 ./configure 包装）
- 编译日期: 2026-09-21
- 编译器: clang/clang++ 15.0.4（OHOS SDK native toolchain）
- 状态: published（conan-verify G0-G4 + L2/L4/L5 全绿）

## 依赖
- qt5-qtbase/5.15.2.2（制品仓已发布，含 OHOS 适配的 qmake/mkspecs）

## 关键适配

### 1. qmake 宿主环境（E189 同类）
qtbase 包内 qmake 内嵌的 QT_HOST_DATA 指向 conan 构建缓存路径，
CI 环境下必然失效。对策：配方 generate() 把 qtbase 全量拷贝到
build_folder 私有 prefix（R49），并写入 qt.conf 覆盖烘焙路径
（HostData=. 关键——填 mkspecs 会双层嵌套导致 spec 查找失败）。

### 2. mkspec 选择
qmake 找不到 OHOS 专属 spec，显式传 `--spec linux-clang-libc++`
（qtbase 包 mkspecs 自带，匹配 profile 的 clang+libc++）。

### 3. 安装阶段
qmake Makefile 无 DESTDIR 支持，`make install` 直接装入 configure
指定的 --prefix（build_folder/inst），package() 从该目录拷贝。

### 4. shared 构建在 OHOS 运行时不可用（本包核心发现）
- 动态库编译、链接全部成功，但测试二进制运行时报
  `Error loading shared library libIrcCore.so.3`；
- 实测排除：LD_LIBRARY_PATH 手动注入无效、包目录非 HMDFS 亦无效、
  DT_RPATH/RUNPATH（含 --disable-new-dtags）均无效——
  OHOS musl 加载器对用户态目录的版本化 .so 搜索受限；
- 静态构建（shared=False）的 test_package 实测通过（`test libcommuni 3.7.0: OK`）；
- 故 default_options.shared=False。

## 上游测试（R51 三步法申报；2026-09-23 本机实测更新）
- 清点：tests/auto/ 下 16 个 QtTest 模块（irc/ircconnection/irccommand/
  ircmessage/ircnetwork/ircbuffer/ircbuffermodel/ircchannel/ircuser/
  ircusermodel/irccommandparser/irccommandqueue/irccompleter/irclagtimer/
  ircpalette/irctextformat），命令 `cd tests && make check`；
- 真实执行：本机 OHOS aarch64（同 CI 工具链 clang 15 + qt5-qtbase 5.15.2.2，
  QT_QPA_PLATFORM=offscreen）qmake 构建 tests/auto 并逐模块运行，
  16/16 模块全部运行，939 个测试函数 937 通过、2 失败：
  - 失败用例：ircconnection::testClone（tst_ircconnection.cpp:2031）、
    ircconnection::testSaveRestore（tst_ircconnection.cpp:2074）；
  - 失败原因：qt5-qtbase 5.15.2.2 制品未编入 openssl 后端，
    `IrcConnection::setSecure()` 打印 "the Qt build does not support SSL"
    后 `isSecure()` 返回 false——依赖特性限制，非 libcommuni 代码缺陷；
  - 含 TCP 回环（QTcpServer::listen）的 ircconnection 网络用例全部通过；
  - 勘误：此前"OHOS 沙箱禁止文件式 UDS bind 导致上游测试无法运行"的结论
    有误——上游测试共享库 tst_ircclientserver 基于 QTcpServer（TCP 回环），
    并非 Unix 域套接字，本机实测可正常 listen/运行，该结论予以撤回；
- 逐模块实测结果（完整原始输出留档于构建机本地，不入库——*.log 属项目
  审查规则禁入文件）：

  | 模块 | 结果 | 模块 | 结果 |
  |------|------|------|------|
  | irc | 30/30 | irclagtimer | 6/6 |
  | ircbuffer | 11/11 | ircmessage | 265/265 |
  | ircbuffermodel | 16/16 | ircnetwork | 17/17 |
  | ircchannel | 5/5 | ircpalette | 20/20 |
  | irccommand | 177/177 | irctextformat | 90/90 |
  | irccommandparser | 48/48 | ircuser | 5/5 |
  | irccommandqueue | 9/9 | ircusermodel | 14/14 |
  | irccompleter | 20/20 | ircconnection | 204/206 |

- 配方保持 -nomake tests（testlib 产物不随包分发、且 2 例 SSL 用例会卡死
  CI 的 make check 门禁），上游测试以本机实测 + 摘要入档方式申报；
- test_package 实测：1/1 通过。

## 验证结果
- conan create: PASS（静态）
- test_package: test_libcommuni OK
- 上游测试（本机实测）: 16/16 模块运行，937/939 函数通过（2 例 SSL 后端缺失，见上）
- conan-verify: G0-G4 + L2/L4/L5 全部 PASS
---

**编译结束**: 2026-09-21 11:37
**最终状态**: built
