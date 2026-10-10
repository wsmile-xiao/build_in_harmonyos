# ntfs-3g 2026.7.7 适配笔记

## 任务
- contrib 7273,分支 feat/ntfs-3g-2026.7.7,认领 2026-09-26
- 上游:github tuxera/ntfs-3g tag 2026.7.7(C,autotools)

## 交付物
- lib/libntfs-3g.so(NTFS 读写库)
- bin/ntfsprogs 工具集(mkntfs/ntfsls/ntfsinfo/ntfsclone 等)

## 配方机制
- autotools;**源码包用官方 release tarball(自带 configure),不再 autoreconf**
- FUSE 挂载工具禁用(--disable-ntfs-3g),避免 FUSE 依赖
- --disable-ldconfig --disable-plugins
- mount-helper 不传:--enable-mount-helper 在 configure.ac 里对非 linux* 的
  target_os 默认就是 no(OHOS 走 *),且 --disable-mount-helper 不是合法选项
- umask 077 陷阱修补(buildtorrent 先例);release 包 configure 里有 2 处
- 不做 strip

## CI 失败与修复(2026-09-30,连续两轮 conan-build-test 红)

- **症状**:conan-build-test 41s 失败,`autoreconf --force --install` 报
  `Can't load .../perl/5.42.2/.../auto/Cwd/Cwd.so ... Permission denied`
- **取日志的正确端点**:`GET /buildbot/api/v2/logs/<logid>/raw`。
  之前反复打的 `.../steps/<stepid>/logs/stdio` 是错端点,恒 404/空,
  曾被误判为「日志被 cleanup 永久回收」。
- **根因**:`autoconf/2.72` → `perl/5.42.2` 传递依赖。`perl/5.42.2` 配方只对
  `bin/perl` 做 codesign+chmod,**XS `.so` 既不签名也不 chmod**,OHOS 侧
  dlopen 拒绝。同仓 `perl/5.42.2.3`(commit 854838f0d)已把「codesign 使 XS 模块
  可加载」列为修复项,5.42.2 缺这一条。5.42.2 已发布到 ohpcd 制品仓,
  重发同版本号属 perl 卡责任范围,本卡不能代改。
- **本卡修法**:换官方 release tarball
  (`ntfs-3g_ntfsprogs-2026.7.7.tgz`,自检 sha256 `d67b7690…`,与 GitHub archive
  同源同 sha 校验但**多 22 个 autotools 产物**:configure / Makefile.in /
  aclocal.m4 / ltmain.sh / config.guess / config.sub / install-sh …),
  `build()` 的 `if not os.path.isfile("configure")` 自然为假,整条
  autoreconf → perl XS 依赖链被绕开。配方 build() 逻辑未改。
- 另挂 macports / ipfire 两个字节一致镜像(实测三处 sha256 相同),
  防 worker 单 host 不可达。`download.tuxera.com` 不在 CI 镜像白名单内,
  预下载扫描器不做改写,conan get() 按 URL 列表依次回退。

## CI 失败与修复(第二轮:E007,2026-09-30,head e0dfe9bc)

换 release tarball 后 perl XS 链已绕开,但 conan-build-test 仍在
`autotools.configure()`(build() line 77)失败:

```
config.guess: line 1613: /storage/.../tmp/cgcnmJOn/dummy.c: Permission denied
config.guess: unable to guess system type
UNAME_MACHINE = "aarch64"  UNAME_SYSTEM = "HarmonyOS"
configure: error: cannot guess build type; you must specify one
```

**根因是两步串联,不是单点**:
1. tarball 自带 `config.guess`(`timestamp='2024-07-27'`),主 switch 里
   `uname -s=HarmonyOS` 匹配不到任何 case;
2. → 落到文件末尾的 compile-and-run 探针:第 119 行
   `{ tmp=\`(umask 077 && mktemp -d "$TMPDIR/cgXXXXXX")\` …}`,第 1613 行
   `cat > "$dummy.c"`;
3. → 该临时目录在 **HMDFS 上不可写** → `dummy.c: Permission denied`;
4. → `unable to guess system type` → `cannot guess build type`。

即 **E007(不认 OHOS)触发 + E011(HMDFS 临时目录不可写)放大**。
注意:build() 原有的 `umask 077 → 022` 循环 glob 的是 `'**/configure'`,
**只匹配名为 configure 的文件**,所以那次修补根本没碰到 `config.guess` ——
这解释了为何上一轮没修好。

**修法(知识图谱正路,非 `--build/--host`)**:
- `patches/0001-config-guess-ohos.patch`:`config.guess` 加 `__OHOS__` LIBC 分支 +
  `*:HarmonyOS:*:*` case,直接 `GUESS=${MACHINE}-unknown-linux-ohos`。
- `patches/0002-config-sub-ohos.patch`:`config.sub` 补 `ohos-linux)` 三元组分支
  (该 tarball 的 config.sub 已有 `linux-ohos*` 内核项,但缺 `ohos-linux` 三元组分支,
  0001 输出的三元组无法被规范化)。
- 补丁改为 `patch_type: portability` 注册,并把 `apply_conandata_patches` 从
  `build()` 首行**移到 autoreconf 之后** —— autoreconf 会用系统版本重生成这两个
  文件,先打补丁会被覆盖。
- `build()` 增加落地复核:`config.guess` 不含 `HarmonyOS` 直接抛 `ConanException`,
  避免"补丁没生效"退化成又一次难懂的 configure 失败。

**为什么不用 `--build/--host` 绕过**:那会置 `cross_compiling=yes`,
`AC_RUN_IFELSE` 等运行时检测全部跳过、平台能力全用硬编码默认值、`config.h` 与
实际平台不符——是更糟的**静默失败**。项目 `knowledge/principles.yaml`
`P-AUTOTOOLS-001`(`level: critical`)对此 `auto_reject: true`,E007 的
`rec_priority: 1` 也是 `patch-autotools-script`。设备实测已验证:
打补丁后 `checking whether we are cross compiling... **no**`(原生构建保持)。

**证据(本地 + 设备双侧)**
- 本地:stub `uname` 模拟 OHOS,未打补丁 → `unable to guess system type`(与 CI 逐字同款);
  打补丁 → `aarch64-unknown-linux-ohos`;PATH 只留 stub(无任何编译器)仍成功
  → 证明走 uname 分支而非编译探针,不会误判交叉编译。
- 设备(job nt3027,CI 同源 `build_and_test.sh`):`GATE_RC=0`,Pass rate 100.0% (1/1),
  `L0/L1/L5=pass`,`L1e` 反向验证 `[ok] test genuinely depends on ntfs-3g`,
  日志 `ntfs-3g consumer test OK`。

## 消费者测试的两处真机缺陷(同一轮发现并修)

闸 3 首次跑到 test 阶段后暴露,均为**真机实证**非推测:
1. **`mktemp` 不可用**:`mktemp: inaccessible or not found`(`/tmp` 在 OHOS 只读)。
   改用 `$HOME/tmp` + 显式 `mkdir`。随后又暴露 conan test 的 PATH 不含
   `/system/bin`,`mkdir` 取不到 → 脚本内先补 PATH。
2. **缺 `LD_LIBRARY_PATH`**:`Error loading shared library libntfs-3g.so.90`
   + 一屏 `symbol not found`。包 `lib/` 不在 loader 默认搜索路径,须在
   `test_package/conanfile.py` 内联注入(OHOS 上 conan env 列表不生效,
   2800+ 配方同款做法)。
3. **`mkntfs` 不会创建目标文件**:`ntfs_device_unix_io_open()` 先 `stat()`,
   ENOENT 即 `The device doesn't exist`(mkntfs.c:3492 走 `O_RDWR`,无 `O_CREAT`);
   `-F` 只表示"非块设备也强制格式化"。故须先 `dd if=/dev/zero bs=512 count=4096`
   预造镜像。
4. **工具语义纠正**:`ntfsinfo`/`ntfsls` 的 `-f` 是 `--force` 而非 `--file`;
   卷信息要加 `-m/--mft`。空卷根目录本就没有用户文件,故 `ntfsls` 断言改为
   `-s` 系统元数据文件(`$MFT`/`$Boot`/`$Volume`)。

## 已知门禁告警(非失败,如实记录)

- `L2_RESULT=skip`:12 个 CLI 的 `--version/--help` 探测失败。ntfsprogs 用的是
  `-V/--version`(见 `ntfsls -h` 输出),闸 3 固定用 `--version` → 非零。
  **非阻塞**,且不影响 L1:L1 的 test_package 已真实跑通全链路。
- `L4_RESULT=warn`:**扫描器误报,已核实**。`ci/conan/build_and_test.sh:1469`
  用 `grep -rlE '(strcpy|sprintf|gets|strcat)\b'`,而 POSIX ERE **不支持 `\b`**,
  于是 `0001` 上下文行里的英文单词 `targ`**`ets`** 被 `gets` 规则命中
  (该行是 GNU config.guess 原有的 NetBSD 注释,非新增代码)。
  用带前导/尾随字符类的等价正则复核:`[^a-z_](strcpy|sprintf|gets|strcat)[[:space:]]*\(`
  在两个补丁里命中数均为 **0**,即补丁中**不存在**任何危险函数调用。
  同仓先例:`xapian-core/2.0.0` manifest 记为
  `L4_RESULT=warn(扫描正则缺前导 \b 的误报)`,同一误报模式。

## 上游测试
- 无测试套件(0/0);消费者测试用 ntfsprogs 做文件级全链路操作
  (mkntfs 建卷 → ntfsinfo -m 读卷信息 → ntfsls -s 读系统元数据),真机 3/3 通过。

## 编译结束
