# 1.3.7 原生适配记录

从权威 Debian orig 构建全部原始生产源，直接使用 release configure，不修改生成文件或强制 --host/--build。
config.guess 的 tuple 来自实际 Clang -dumpmachine；config.sub 支持 linux-ohos。原生 configure 确認 libssh、readline、OpenSSL Base64、IPv6 能力。
gettext/NLS、Kerberos 等保持上游自动探测，当前未找到。没有为通过而显式关闭功能。

r1：合法空值 `HAVE_LIBSSH /**/` 被后置正则误判。根据实际配置头修检查器，接受已证明的空值、1、空注释，仍拒绝 undef/0。
r2：生产编译和安装通过，版本/帮助通过，真实会话初始化 SIGSEGV。只读目标诊断确认 UID 20020084 无 passwd 记录；guard NULL，USER/LOGNAME 仅作为显示/默认用户名，缺失则数值 UID 标签。显式远端 FTP 凭据不受影响。HOME 缺失/非绝对时回退到已验证 cwd；cwd 获取失败明确退出，不伪造路径或账户。
r3：FTP 登录成功，目录缓存 libc tmpfile EACCES，尽管有可写 TMPDIR。用应用内 mkstemp+unlink+fdopen w+b，保留 seek/rewind 和自动删除语义，设置 CLOEXEC，失败返回真实 errno；不 LD_PRELOAD、不写系统临时目录。
r4：Conan create RC0、make check 原始入口执行、FTP 消费者 6/6、W3 12 阶段与 release/postrelease PASS。文件传输不是只查进程返回码，而是逐字节核对 65792 bytes payload。

Release 未注册 TESTS/check_PROGRAMS，原始分母 N=0；6 组消费者单列，不伪造上游分母。
SFTP 构建入口仍保留，但尚未执行 SFTP 业务消费者。FTP 成功不能代替 SFTP、平台 CI、审核或发布。
E12242 提炼跨 Autoconf 软件的能力宏观察器语义；不是重复 E338/E272 的运行时说明。
