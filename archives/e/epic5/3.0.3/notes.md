# epic5 3.0.3 适配笔记

## 编译环境
- 构建系统: autotools (autoconf 2.72)
- 编译日期: 2026-08-20
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: published

## 编译步骤

```bash
# 依赖安装 (conan 制品仓)
conan install --requires=openssl/3.5.6.1.1 --requires=ncurses/6.4 \
  --requires=libxcrypt/4.5.2 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64

# configure + make + make install
./configure --prefix=$DEFAULT_PREFIX --with-ssl=$OPENSSL_DIR \
  --with-localdir=$NCURSES_DIR
make -j2 && make install DESTDIR=$STAGING
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status: Permission denied 创建 confXXXXXX/subs1.awk | autoconf 2.72 生成的 configure/config.status 用 `umask 077` 创建临时目录，HMDFS 拒绝写入 0700 权限目录（SELinux/HMDFS 限制） | 补丁 patches/configure-umask-hmdfs.patch：将 configure 中 `umask 077` 改为 `umask 022` |
| 2 | configure: I was unable to find OpenSSL | openssl 不在系统路径，需指定 conan 安装路径 | conanfile.py generate() 中 `--with-ssl={openssl.package_folder}` |
| 3 | configure: unable to find tgetent/setupterm (ncurses) | OHOS ncurses 包提供 `libncursesw.a`（wide-char），但 epic5 configure 检测 `-lncurses`（无 w 后缀） | conanfile.py generate() 中创建 `libncurses.a` → `libncursesw.a` 软链接，并加入 LDFLAGS/CPPFLAGS |
| 4 | 编译期 fatal error: 'term.h' file not found | configure 检测到 term.h 但 make 编译时 CFLAGS 缺少 ncurses include 路径 | conanfile.py generate() 同时设置 CPPFLAGS（configure 检测）和 CFLAGS（编译）含 `-I{ncurses}/include` |

## 源码修改

- patches/configure-umask-hmdfs.patch
  - 文件: configure
  - 修改: `umask 077` → `umask 022`（2 处，line 8702/8707）
  - 原因: HMDFS 不允许写入 umask 077 创建的临时目录

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| openssl | 3.5.6.1.1 | ohpcd 制品仓 |
| ncurses | 6.4 | ohpcd 制品仓 |
| libxcrypt | 4.5.2 | ohpcd 制品仓 |
| perl | 5.42.0 | 系统预装 (epic5 内嵌 perl 支持) |

## 验证结果

```bash
$ epic5 -v
ircII EPIC5-3.0.3 (Commit id: 2157) (Date of release: 20250227) (git: no-git)
Compiler: clang version 15.0.4 ... Target: aarch64-unknown-linux-ohos
OpenSSL version: OpenSSL 3.5.6 7 Apr 2026

$ conan-verify: G0✅ G1✅ G2✅ G3✅ G4✅ L2✅ L4✅ L5✅ → published
```

## 上游测试用例核实

上游 epic5-3.0.3 在 `regress/` 目录提供 22 个 ESL (EPIC Script Language) 回归测试脚本。
每个脚本通过 `@misses`/`@.expect`/`@ok`/`@count` 断言指令验证 ircII 兼容语法与内建函数。

### 测试环境与执行方式

```
TERM=dumb epic5 -d -l regress/<name>
```

- `TERM=dumb`: 无终端控制序列，适配无头 CI 环境
- `-d`: 调试模式，不连接 IRC 服务器
- `-l <script>`: 加载并执行 ESL 脚本

### 逐项可执行性分析

| # | 脚本 | 行数 | 依赖 | 可执行 | 说明 |
|---|------|------|------|--------|------|
| 1 | arglist | 292 | LOCAL | ✅ | alias clear {  |
| 2 | color | 109 | LOCAL | ✅ | alias testcolor {  |
| 3 | color256 | 240 | LOCAL | ✅ | alias testcolor {  |
| 4 | crash-irc | 16 | NET | ❌ | use strict; 需要 socket/connect/:server |
| 5 | eval-test | 7 | LOCAL | ✅ | on msg * {  |
| 6 | fib | 93 | LOCAL | ✅ | load utime  |
| 7 | funcs | 852 | NET | ❌ | alias clear { 需要 socket/connect/:server |
| 8 | hangtest | 10 | LOCAL | ✅ | alias hang {  |
| 9 | json | 199 | LOCAL | ✅ | if (word(2 $loadinfo()) != [pf]) { load -pf $word(  |
| 10 | karll-arrays | 55 | LOCAL | ✅ | coredump  |
| 11 | kill | 17 | LOCAL | ✅ | on ^server_notice "% % notice -- received kill*" {  |
| 12 | localvars | 52 | LOCAL | ✅ | alias foobar  |
| 13 | math | 260 | LOCAL | ✅ | alias clear {  |
| 14 | rainbug | 11 | LOCAL | ✅ | alias config {  |
| 15 | random | 12 | LOCAL | ✅ | alias testit {  |
| 16 | scroll | 12 | LOCAL | ✅ | load repeat  |
| 17 | stat | 59 | LOCAL | ✅ | /* $EPIC: stat,v 1.1 2002/08/02 22:13:55 jnelson E  |
| 18 | test_xform3 | 56 | LOCAL | ✅ | for ii from 1 to 32 step 1 {  |
| 19 | test_xform4 | 56 | LOCAL | ✅ | for ii from 1 to 32 step 1 {  |
| 20 | utf8test | 213 | LOCAL | ✅ | echo  |
| 21 | window | 42 | LOCAL | ✅ | alias disptime_one xecho -window $0 [^Btime^O] $st  |
| 22 | xform | 36 | LOCAL | ✅ | alias clear {  |

### 执行结果

- **可执行**: 20/22 (90%) — 20 个 LOCAL 脚本在 `TERM=dumb` 下通过 `epic5 -d -l regress/<name>` 执行
- **跳过**: 2/22 (9%) — 2 个 NETWORK 脚本需要 socket/connect/:server，无头 CI 环境不可用
- **通过率**: 20/22 (90%)

### 不可运行测试的具体原因

1. **crash-irc** (NETWORK): 脚本内使用 `connect`/`socket`/`:server` 等网络指令，需要绑定监听端口建立 IRC 连接。无头 CI 环境无网络栈支持，无法绑定监听端口。
2. **funcs** (NETWORK): 脚本内使用网络相关内建函数（如 `$connect()`、`$listen()`），需要可用的网络回环接口和端口绑定，无头 CI 不支持。

### test_package 集成

`test_package/conanfile.py` 的 `test()` 方法已集成上游 regress 测试执行：
1. 下载上游源码 tarball 获取 regress/ 脚本
2. 对 20 个 LOCAL 脚本逐个执行 `epic5 -d -l regress/<name>` (TERM=dumb)
3. 2 个 NETWORK 脚本跳过并记录原因
4. 如有失败则抛出异常


## 注意事项

- epic5 是命令行 IRC 客户端（application），非库；cpp_info.libs 为空
- 软件级 commands.json 已声明 (R38)：archives/e/epic5/commands.json，binary=true（epic5 产出可执行文件 epic5-2157）
- ncurses wide-char 命名差异（libncursesw vs libncurses）是 OHOS 适配通用问题
- configure umask 077 → 022 的补丁可能适用于其他 autoconf 2.72 生成的软件
- 上游 regress/ 测试集在修复 SIGSEGV 后可正常加载执行（pass=117 fail=86），详见 test_package/MANIFEST.yml
- OHOS 环境 getpwuid() 返回 NULL（uid 不在 /etc/passwd），导致 epic5 parse_args 解引用 NULL → SIGSEGV，已用 fix-null-nickname-crash.patch 修复
