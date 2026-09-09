# dropbear 2025.88 适配笔记（2026-09-06 设备单端完整适配）

> 本笔记取代 2026-06-02 的旧流程笔记（旧流程为预编译 tar.gz 交付，非 Conan 配方；
> 其中 getpass/getspnam/HMDFS 结论经本轮实测复核后保留在对应小节）。

## 概览

- 软件: dropbear 2025.88（轻量级 SSH2 服务器/客户端; C 语言，任务卡标 C++ 属平台标签,
  lang-preflight 判定 c 与任务族兼容）
- 源码: https://matt.ucc.asn.au/dropbear/releases/dropbear-2025.88.tar.bz2
  sha256=783f50ea27b17c16da89578fafdb6decfa44bb8f6590e5698a4e4d3672dc53d4（设备自验）
- 构建系统: autotools（configure 由 autoconf 2.73 预生成; 自包含 libtomcrypt/libtommath）
- 产物: 应用包（dropbear、dbclient、dropbearkey、dropbearconvert + 4 个 man 页）
- 状态: built

## 适配决策与实测依据

### 1. configure 临时目录 umask 077（HMDFS）

- 现象: 首次 configure 走到 `config.status: creating Makefile` 时报
  `./config.status[709]: can't create ./confEwSVkN/subs1.awk: Permission denied`。
- 根因: autoconf 2.73 m4sh AS_TMPDIR 硬编码 `(umask 077 && mktemp -d ./confXXXXXX)`
  （configure:9548/9553 两处）。HMDFS 上 0700（组位缺失, 实测目录位为
  `drwx--S---`）目录拒绝本属主创建文件; umask 022 产生的组位目录可写。
  精确复现: `umask 077 && mktemp -d ./confXXXXXX` 后写文件必失败;
  022/默认 umask 全部成功。知识 E011/E136/E206（btparse 同款补丁先例）。
- 修复: 补丁 0003-configure-umask.patch 将两处 umask 077 改为 022。
  回滚风险核对: 本包 Makefile.in 无 configure 再生成 maintainer 规则
  （grep 无 configure.ac/autoconf 规则），config.status 由已补丁 configure
  生成，补丁不会在 make 阶段被静默回滚，故未做 os.utime 时间戳钉死。

### 2. config.guess 无法识别系统

- 现象: 首次 configure 在 `checking build system type` 报
  `./src/config.guess[1733]: can't create .../cgjHv1fQ/dummy.c: Permission denied`
  → "unable to guess system type"。
- 根因: config.guess 的 mktemp -d + dummy.c 编译探针在 HMDFS 上被拒（同 1 的
  目录权限语义），并非版本过旧。
- 修复: 显式 `--build/--host=aarch64-unknown-linux-musl` 跳过探测（configure
  自身错误提示的标准做法）。自带 config.sub (2023-08-22) 实测接受该写法、
  拒收 `*-linux-ohos`，故不用 ohos 三元组。

### 3. OHOS libc 无 getpass()/getspnam()

- 实测证据: configure 输出 `checking for getpass... no`、`checking for getspnam... no`;
  sysroot 头文件有 shadow.h 且定义 struct spwd，但 sysroot 头文件无两个函数声明、
  libc 动态符号表中无导出。
- 影响: cli-auth.c `getpass_or_cancel()` 无条件调用 getpass()（上游 configure
  948 行的缺失提示只打印 notice 不改编译路径）; common-session.c 在
  HAVE_SHADOW_H 成立时调用 getspnam()，实测编译报
  `implicit declaration of 'getspnam'` / int→指针转换错误。
- 修复: 补丁 0001/0002 按 configure 的 AC_CHECK_FUNCS 结果做特性条件编译
  （HAVE_GETPASS/HAVE_GETSPNAM），无 `__OHOS__` 平台条件编译（R8 合规）:
  - getpass 缺失时 getpass_or_cancel 从 /dev/tty 逐行读取并去除换行，
    保持密码/键盘交互认证可用;
  - getspnam 缺失时按上游"无有效 shadow 条目"同款处理（`passwd_crypt = "!!"`，
    认证必然失败但编译完整、行为安全）。

### 4. zlib 显式关闭

- 实测: 默认 configure auto 探测启用 zlib（sysroot 同时有 zlib.h 与 libz.so），
  链接行出现 `-lz`、产物 NEEDED 含 libz.so（未声明的系统依赖）。
- 决策: `--disable-zlib`。关闭后四个产物 NEEDED 仅 libc.so（完全自包含）。
  SSH 压缩为可选特性，禁用属上游支持选项; 两个历史适配同样选择无外部依赖。

## 设备原生验证（阶段 E）

- 原生构建: `CC=clang ./configure --prefix=... --disable-zlib
  --build/--host=aarch64-unknown-linux-musl && make -j1` → rc=0;
  DESTDIR staging 安装 4 二进制 + 4 man 页。
- 产物检查: 四个产物 `readelf -d` NEEDED 仅 libc.so; PIE（Type: DYN+FLAGS_1 PIE）、
  NX（GNU_STACK 无 RWE）、BIND_NOW（FLAGS BIND_NOW / FLAGS_1 NOW）齐全
  （configure 硬化_flags 自动启用）。hnp clang 产物自带链接器签名，
  未做任何重签。
- 运行冒烟: dropbear -h / dropbearkey ed25519 生成与公钥导出 /
  dropbearconvert dropbear↔openssh 往返逐字节一致（cmp）/ 传输层端到端:
  dbclient 完成协议握手与 KEX 后进入认证阶段（服务端日志 "Login attempt ..."
  在 KEX 之后出现），符合第 5 节平台限制下的预期行为。

## 上游测试（阶段 E，硬门禁逐类归因）

上游 make check = lint + make -C test（pytest, 需 venv）。两段均以等价方式
在设备真实执行:

- lint: 发布 tarball 的 Makefile.in:290 引用顶层 `./dropbear_lint.sh` 而脚本
  实际在 `src/` 下（上游打包缺陷，逐字 make check 的 lint 段必然失败）。
  等价执行 `cd src && sh dropbear_lint.sh` → rc=0（通过）。
- pytest: test/Makefile 的 venv 目标在 HMDFS 上卡死（2026-06 与本轮实测一致），
  使用全局 python3 3.12.8 + pytest 9.1.1 + asyncssh 2.17.0（经许可 pip 安装,
  上游 requirements.txt 固定版本）+ psutil 6.1.1 等价直跑，并与上游 CI 对齐
  预置 ~/.ssh 密钥组（build.yml "keys" 步骤同款）。

统计（单位: pytest 用例/参数化实例; 取数: -v 日志 grep 分列计数）:

```text
TOTAL=52  PASS=9  FAIL=39  SKIP=3  XFAIL=1  NOT_RUN=0
```

| 类别 | 数量 | 根因（附证据） |
| --- | --- | --- |
| PASS | 9 | dropbearconvert test_roundtrip 7/7（含逐字节往返比较）+ test_roundtrip[0]/test_read_pty[0]（空数据连接级用例，本机仅覆盖连接建立/断开路径，认证不可达，如实注明） |
| FAIL | 25 | 认证会话平台性不可行: 当前 uid 20020084 不在 /etc/passwd（getpwuid 失败 → dbclient "failed to identify current user" → 用户名 unknown → 服务端 "Login attempt for nonexistent user"）; /etc/passwd 全部条目 pw_dir 为空且 shell 为 /bin/false; 非 root dropbear 仅允许 pw_uid == euid 登录（src/svr-auth.c checkusername）; 普通权限无法补充用户条目。覆盖 test_channels 23 + test_aslr 1 + test_concurrent 1 |
| FAIL | 14 | test_dropbearconvert::test_from_openssh 全部参数化: 上游断言比较整行公钥含 comment（上游源码注释自认 "since it currently matches" 属附带比较）; getpwuid 失败使两个工具 fallback 分叉: ssh-keygen 写 `100@localhost`（uid 派生值）而 dropbearkey -y 的 fallback（src/dropbearkey.c:411 getpwuid 失败 → 空用户名）写 `@localhost`。密钥本体转换正确: 断言 diff 中 base64 完全一致、fingerprint 一致、7/7 roundtrip 通过。知识草稿 E547 |
| SKIP | 3 | test_svrauth test_pubkeyinfo* 上游框架自身条件（DBTEST_IN_ACTION 仅上游 CI 设置，普通 make check 同样跳过） |
| XFAIL | 1 | test_channels::test_signal 上游标记 strict "Not yet implemented" |

附带记录（非本包缺陷）: test_channels 的 test_netcat/test_tcpflushout 在连续
参数化间还会出现 3344 端口 "Address in use"（上游 HandleTcp.__exit__ 只
shutdown 不 server_close, 监听 socket 释放滞后; 在本机用 socketserver 复现:
连续 bind 同端口 5 轮全失败, 加 server_close 后 5 轮全通过）。因认证不可行
该问题在本机无独立观测路径，仅记录不修改上游测试。

## test_package（消费者验证）

test_dropbear.sh 在设备真实执行打包产物: 四命令存在性、dropbearkey ed25519
生成与公钥导出、dropbearconvert 双向转换往返逐字节一致、三个工具 usage 退出码。
共 10 处断言，全部通过（env="conanrun" 直跑; 临时文件在 build_folder，不污染
包源目录）。

## 交付物

| 文件 | 说明 |
| --- | --- |
| conanfile.py | autotools 配方（无外部依赖; --disable-zlib; OHOS 显式三元组） |
| conandata.yml | 官方源 URL + sha256; 3 个补丁（列表式） |
| patches/0001-0003 | getpass 条件编译 / getspnam 条件编译 / configure umask |
| test_package/ | conanfile.py + test_dropbear.sh + MANIFEST.yml |
| commands.json | 软件级 CLI 声明（4 个命令） |
| manifest.yaml | 包级 + 版本级（版本级按当前模板重写, status=built） |

## 遗留与风险

1. 认证类上游测试在本机平台性不可行（见上游测试表），待具备用户数据库
   可写条件的验证环境后可补跑; 功能等价性由往返转换/传输层握手/密钥生成
   等替代验证覆盖。
2. zlib 已禁用，需要 SSH 压缩的下游应显式声明 zlib 依赖并移除该配置项重编译。
3. dropbear 服务器在 OHOS 上的长期运行（多用户登录）受平台用户数据库限制，
   单用户（同 uid）场景可用。
