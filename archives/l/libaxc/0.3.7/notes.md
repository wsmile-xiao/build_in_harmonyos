# libaxc 0.3.7 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-09-19
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. source() 取上游 axc v0.3.7 tarball，另取 libsignal-protocol-c v2.3.3 填入 lib/libsignal-protocol-c（上游 tarball 子模块目录为空）。
2. 先编译 vendored libsignal 静态库（cmake -DBUILD_SHARED_LIBS=OFF -DCMAKE_POSITION_INDEPENDENT_CODE=ON）。
3. make -j1 all 编译 libaxc.a/libaxc.so，依赖 sqlite/libgcrypt 由 Conan 提供（PkgConfigDeps）。
4. make test 运行上游 49 个 cmocka 单测（test_store 36 + test_client 13，经源码 main 数组逐项清点）。
5. package() 直接铺包（lib/ + include/axc/ + signal 头文件），供 test_package 消费。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 tarball 缺 libsignal 源码 | v0.3.7 将 libsignal 作为 git submodule，GitHub tag tarball 不含子模块 | conandata 增加 libsignal 来源（signalapp v2.3.3 官方 tag），source() 双 get 后编译 |
| 2 | libsignal-protocol-c 无可用 Conan 依赖 | 仓内无该包配方，直接 requires 会触发 PF4 阻断 | 本配方内 vendored 静态编译（-DBUILD_SHARED_LIBS=OFF -DCMAKE_POSITION_INDEPENDENT_CODE=ON），不声明 conan requires |
| 3 | 真机无 pkg-config 且内嵌 cmake 缺 POLICY | 上游 Makefile 经 pkg-config 探测依赖并用 cmake -DCMAKE_BUILD_TYPE=Debug 构建 vendored signal，CMake 4.x 拒收 cmake_minimum_required(2.8.4) | 预编译 signal 到 signal-build 后用 make 命令行覆盖 REQPKG/SIGNAL_*/SQLITE3_*/LIBGCRYPT_*/GLIB_* 走系统分支跳过内嵌 cmake，同时跳过全部 shell pkg-config 探测 |
| 4 | 真机 src/axc.c 报 glib.h 缺失 | 上游 axc.c 依赖 glib（g_strndup/g_get_real_time），配方初版未声明 glib 且 GLIB_* 覆盖为空 | 新增 glib/2.88.0 requires，GLIB_* 改为 _dep_cflags/_dep_ldflags 实值（含 pcre2/zlib 传递头库），_dep_* 聚合 components，package_info 增加 glib::glib-2.0 |
| 5 | SIGNAL_CFLAGS 未含 signal 头目录 | 覆盖只指向 libsignal 根，头文件实际在 lib/libsignal-protocol-c/src | SIGNAL_CFLAGS 补加 src 子目录（保留根目录兼容） |
| 6 | make test 报 cmocka.h 缺失 | 上游 test 目标 TESTFLAGS 经 PKGCFG_C 传入，无独立 CMOCKA 变量且编译行不含 CPPFLAGS | 把 test_requires cmocka 头路径搭载到 GLIB_CFLAGS 上（仅加 -I；链接仍走 -lcmocka + LDFLAGS -L 注入） |
| 7 | make install 在 package 阶段失败 | install 成功后 ln -s 报 No such file，且 install 每次重展 pkg-config 探测 | package() 绕开 make install，直接拷贝 build/libaxc.a/.so/.pc 与 src/*.h 到 lib/、include/axc/，.so 三个名字用实文件拷贝代替软链接 |

## 依赖版本

- sqlite/3.53.3
- libgcrypt/1.12.2
- glib/2.88.0
- cmocka/2.0.2（test_requires）
- libsignal-protocol-c v2.3.3（vendored，随配方编译）

## 验证结果

待真机预检回填：conan create 日志中的 make test 与 test_package 输出。

## 注意事项

- 本轮未 commit/push，不创建 PR，等待 HMBS 真机全部门禁。
- Windows 环境无法完整检出 main（gama 目录有非法文件名），本机采用稀疏检出；后续推送由 HMBS 在 Linux 后端完成。

