# yazpp 1.9.2 适配笔记

## 编译环境
- 构建系统: autotools（tarball 自带 configure）
- 编译日期: 2026-09-21
- 编译器: clang/clang++（OHOS SDK aarch64）
- 状态: built

## 编译步骤
1. W0：唯一依赖 yaz/5.37.3（制品仓二进制已发布，含 bin/yaz-config 与
   lib/pkgconfig/yaz.pc）。
2. 语言预检 lang-preflight：cpp PASS。
3. 探索构建（真机 -j1）：configure（--with-yaz=shim）→ make → install
   DESTDIR → `make -C src check`（LD_LIBRARY_PATH 指向依赖 lib）全绿。
4. 配方：conan-init 骨架 + 手工改写（library 型 + 私有 yaz-config shim +
   直接编译式消费者测试）；conan-verify 8 门禁全过。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 官方源 ftp.indexdata.com 不可达（443 屏蔽，80 端口 301 循环） | 官方下载点已迁移 download.indexdata.com，且设备侧一度整体不可达 | 网络恢复后从官方 https://download.indexdata.com 下载；conandata 用该官方 URL |
| 2 | configure 报 cannot guess build type | config.guess(2024) 无 HarmonyOS 分支（E007） | 官方 patch-autotools-ohos.pl 直接生效（2024 新式脚本，Score 4/5），产物 aarch64-unknown-linux-ohos |
| 3 | config.status 临时目录 Permission denied | configure `umask 077 && mktemp -d` 在 HMDFS 不可写（E011 家族） | 补丁 umask 077→022（0003-configure.patch） |
| 4 | 编译期 yaz/log.h not found | yaz 包内 yaz-config 把 prefix 烤死为 "/"（`-I//include`），libxml2 路径指向陈旧 .conan2 home（E355 同族：`-I//include`/prefix=/） | 实测 yaz-config `--prefix=` 运行时覆盖无效；配方在私有 build_folder 生成修正版 yaz-config shim（路径取自依赖 cpp_info，R49），configure 传 `--with-yaz=<shim>` |
| 5 | 测试运行期 libxml2.so.16 无法加载 | 探索期未挂依赖库路径 | 配方内按 yaz 先例以 VirtualRunEnv 执行 make check（LD_LIBRARY_PATH 自动注入） |

## 源码修改

- `patches/0001-config-config.guess.patch`（+12 行）：config.guess 加
  HarmonyOS 分支（官方脚本风格）。
- `patches/0002-config-config.sub.patch`（+4 行）：config.sub 认 ohos 三元组。
- `patches/0003-configure.patch`（2 处）：临时目录 umask 077→022。
- 配方内（非补丁）：`-std=c++14`（消费者/库同源，头文件含 2003 年代写法）。
- 无 `__OHOS__` 平台宏，无源码文件改动。

## 依赖版本

- yaz/5.37.3（静态；其 transitive：libxml2/2.15.3、zlib）

## 上游测试五维账本

| 维度 | 数量 | 说明 |
|---|---|---|
| N_static | 2 | src/Makefile.am：`check_PROGRAMS = test_query test_gdu` + `TESTS = $(check_PROGRAMS)`（automake 注册入口计数） |
| N_registered | 2 | 与 N_static 同（无条件跳过项） |
| N_executed | 2 | `make -C src check`（配方 build() 内真实执行），PASS: 2 / FAIL: 0 |
| 未执行分类 | 2 处 | ①zlint/、zoom/ 为样例程序（noinst，无 TESTS 注册）；②doc/ 无测试——均为上游自身定义 |
| N_consumer | 1 | consumer_test：链接静态 libyazpp.a+libyaz.a，调用 Yaz_Z_Query 解析/拷贝/回印 3 组断言（@and a b / x / 空查询），签名后真机运行退出码 0 |

## 验证结果

```bash
# 探索构建（真机）
./configure --prefix=... --with-yaz=<yaz-config shim> --enable-static --disable-shared
make -j1 && make install DESTDIR=...   # MAKE_RC=0 / INSTALL_RC=0
LD_LIBRARY_PATH=<依赖lib> make -C src check   # CHECK_RC=0（TOTAL 2 / PASS 2）

# conan 门禁（ohc-run.py conan-verify yazpp 1.9.2）
# G0-G4 + L2/L4/L5 全 PASS；consumer_test: yazpp query round-trips OK
```

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libyazpp.a | 静态库（--disable-shared） |
| include/yazpp/*.h | 公共头文件（query/gdu/socket-manager 等） |
| bin/yazpp-config | 下游探测脚本（⚠️ 其同样烤死 prefix=/，下游请按本配方式样生成 shim 或自行 sed） |
| lib/pkgconfig/yazpp.pc | pkg-config 元数据（prefix 同样为构建期值） |

## 注意事项
- 下游消费者若走 CMake：包名无连字符（yazpp）可正常使用 CMakeDeps。
- 静态链接序：`-lyazpp -lyaz -lxml2 -lm -lpthread`。
- yazpp-config/yazpp.pc 的 prefix 陷阱会传导给下游（本配方的 B 草稿主题）。
---

**编译结束**: 2026-09-21 16:13
**最终状态**: built
