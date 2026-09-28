# git 2.45.2 适配笔记

## 编译环境
- 构建系统: autotools（上游随发布 tarball 自带 configure）
- 编译日期: 2026-09-25
- 编译器: clang 15.0.4（aarch64，OHOS SDK native 工具链）
- 状态: built（本地 W3 后转 published）

## 编译步骤

1. 下载 `https://mirrors.edge.kernel.org/pub/software/scm/git/git-2.45.2.tar.gz`（官方源，R39）
2. 依赖准备：conan full_deploy zlib/1.3.1.1、openssl/3.5.6.1、curl/8.15.0.1、expat/2.8.4 到私有目录（版本由 curl 8.15.0.1 的依赖锁定关系决定；gettext 不作为链接依赖，走 NO_GETTEXT）
3. 干净 configure（关键点：`ac_cv_header_libintl_h=no` 消除 -lintl 链接污染，见问题#1）：
   ```bash
   ac_cv_header_libintl_h=no ./configure --prefix=$DEFAULT_PREFIX \
     --with-openssl --with-curl --with-expat \
     CPPFLAGS="<四个依赖的 include 路径>" LDFLAGS="<四个依赖的 lib 路径>"
   ```
4. 覆盖文件 config.mak（非源码补丁，构建配置；与配方 conanfile.py 的 CONFIG_MAK 一致）：
   ```make
   HAVE_DEV_TTY=YesPlease
   NO_PERL=YesPlease
   NO_TCLTK=YesPlease
   NO_PTHREADS=YesPlease
   CURL_LDFLAGS=-lcurl
   # OHOS 无独立 install(1)，/system/bin 提供 busybox applet
   INSTALL=/system/bin/install
   RUNTIME_PREFIX=YesPlease
   ```
5. `make -j4` → `PATH=/system/bin:$PATH make install DESTDIR=$TEST_PREFIX`（平台无独立 install 命令，/system/bin 有；CI 配方层通过 config.mak `INSTALL=/system/bin/install` 显式指定）
6. 包内写入 `etc/gitconfig`（`safe.directory = *`）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 探测 pthread/setenv/IPv6 全部误判 no，NO_CURL/NO_OPENSSL/NO_EXPAT 连锁出现 | SDK sysroot 自带 libintl.h → 头文件检查通过 → configure.ac 向 LIBS 追加 `-lintl`，而 bionic 无 libintl → 后续所有链接型 conftest 失败 | 传 `ac_cv_header_libintl_h=no` 强制走 NO_GETTEXT=YesPlease 路线（官方开关，无 i18n，避免 gettext 链接依赖） |
| 2 | compat/terminal.c 编译错误：getpass 未声明 | HAVE_DEV_TTY 被 config.mak.autogen 空值覆盖（uname 分支设置在前、autogen 空值在后），走到 bionic 不存在的 getpass 回退 | config.mak 显式 `HAVE_DEV_TTY=YesPlease`（config.mak 包含顺序在 autogen 之后，覆盖生效） |
| 3 | 链接失败：undefined symbol pthread_setcancelstate | OHOS musl libc 未导出该符号（SDK libc.so 动态符号表实测无），git atfork 路径使用 | config.mak `NO_PTHREADS=YesPlease`，走官方 sigprocmask 回退分支（run-command.c 有 #ifdef NO_PTHREADS 分支，无补丁） |
| 4 | 链接失败：undefined symbol curl_easy_setopt 等 | curl-config 不在 PATH，Makefile 推导 CURL_LDFLAGS 为空 | config.mak 显式 `CURL_LDFLAGS=-lcurl`（库路径已由 LDFLAGS 提供） |
| 5 | `make install` 报 `install: No such file or directory` | 平台无独立 install 工具 | install 阶段 PATH 前置 /system/bin（含 install applet）；配方层由 conan autotools 注入，不受影响 |
| 6 | 上游 t/ 测试套默认模式报 `line 1640: 3: Bad file descriptor`（test-lib.sh fd3 重定向到 /dev/null 后失效） | 平台 bash/devfs 环境下非 TTY fd 继承差异 | 以 `--verbose-log` 模式运行（fd3 指向真实文件），t0000/t1300 全绿验证可行 |
| 7 | t0001 用例 28 失败（init umask vs shared） | ~~依赖 setfacl~~（初判有误：`setfacl -k … \|\| true` 带 `\|\| true` 守卫，缺 setfacl 不致失败）。真因：测试树建在 HMDFS 上，mode-bit 语义异常（umask 002 下前导目录得 `drwxrws--x`，第 8 位 r→-，断言 `drwxrwsr-x` 落空）——E046 家族 | 测试框架官方 `--root=<原生FS>`（test-lib.sh:205）把 trash 目录指到原生语义 FS：/data/storage/el2/base/cache 探针实测断言 3/3 全过；CI 同款打包二进制 `--root` 重跑 t0001 **69/69 全过** |

## 源码修改

唯一入库补丁：`patches/0001-configure-umask-022-for-hmdfs.patch`（configure 内两处 `umask 077`→`022`，HMDFS 场景，知识 E011，portability 类，无平台宏）。其余适配全部通过构建开关（config.mak / configure 缓存变量）实现，零 `__OHOS__` 平台宏。

## 依赖版本

- zlib/1.3.1.1（curl 8.15.0.1 锁定）
- openssl/3.5.6.1（curl 8.15.0.1 锁定）
- curl/8.15.0.1（HTTPS/HTTP transport）
- expat/2.8.4（git-http-push push URL 解析）
- gettext：不作为链接依赖（NO_GETTEXT，bionic 无 libintl.so；libintl.h 为 SDK sysroot 头）

## R51 上游测试三步法申报表

**清点**（t/ 目录）：
- 测试脚本 1007 个（t0000-basic.sh … t9999-*.sh）
- 注册用例（test_expect_success/failure）约 17866 个
- 单元测试（t/unit-tests/）6 个 C 文件（t-ctype、t-prio-queue、t-reftable-* 等，编译产物已随 make 生成）

**实测**（本机 aarch64 真机环境，bash 5.3，`--verbose-log` 模式绕开问题#6）：

| 测试脚本 | 用例数 | 通过 | 失败 | 说明 |
|---|---|---|---|---|
| t0000-basic.sh | 92 | 92 | 0 | 100%（test-lib 框架自检 + 基础命令） |
| t0001-init.sh | 69 | 69 | 0 | 100%（`--root` 指到原生 FS 后全过，见问题#7 更正） |
| t1300-config.sh | 236 | 236 | 0 | 100%（配置读写全路径；`PERL_PATH` 指向设备 perl 后 nul_to_q 用例全过） |
| 合计 | 397 | 397 | 0 | **通过率 100%**（CI #61347+ 复跑日志为准） |

**未全量运行的具体技术原因**：全量 1007 脚本含网络类（t55xx 需 HTTP daemon）、perl 类（t9xxx 需要 perl 完整模块环境）、交互终端类用例；本平台 test-lib fd 行为要求逐脚本 `--verbose-log` 改造且部分守护进程用例受设备端口/权限限制。核心链路（框架自检/init/config）已实跑覆盖，git 二进制冒烟（--version/init/clone）通过。

## 验证结果

```bash
git --version        # git version 2.45.2 ✅
# staging 包含 share/git-core/templates/（branches/description/hooks/info）✅
# staging 包含 etc/gitconfig（safe.directory = *）✅
```

## 注意事项

- 配方依赖版本必须与 curl/8.15.0.1 锁定关系一致（openssl/3.5.6.1、zlib/1.3.1.1），否则 conan 图冲突
- NO_GETTEXT 路线下不得让 configure 见到可链接的 libintl（配方中用 ac_cv_header_libintl_h=no 固化）
- NO_PTHREADS、HAVE_DEV_TTY、CURL_LDFLAGS 必须显式写入配方 build 覆盖，不能依赖 uname/autogen 默认值
- git 为 CLI 工具 → 软件级 commands.json 必需（R38）
---

**编译结束**: 2026-09-25 20:10
**最终状态**: published
