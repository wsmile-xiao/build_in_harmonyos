# cramfsswap 1.4.5 OHOS 移植笔记

## 上游事实

- cramfsswap（Juliane Holzt 原作，2004-2006；Debian native 包）。
- 1.4.5（2025-09-25，Syed Shahrukh Hussain 接管维护，新增 autopkgtest）。
- 源码：单编译单元 `cramfsswap.c`（365 行）+ 手写 Makefile + man page +
  debian/。无 autotools/cmake，无配置头，无代码生成。
- 源 URL：`https://deb.debian.org/debian/pool/main/c/cramfsswap/cramfsswap_1.4.5.tar.xz`
  sha256 `7905f134178981654577d232b6eedfa2e3b552623d4448c9b1878498f737ad91`
  （与 `cramfsswap_1.4.5.dsc` 的 Checksums-Sha256 声明逐字符一致；salsa tag
  `debian/1.4.5` 同源验证）。GitHub 无官方仓（github.com/sshock/cramfsswap
  不可达），以 Debian 官方渠道为准。

## W0 依赖判定

- debian/control `Build-Depends: debhelper-compat (= 13), zlib1g-dev`；
  debhelper 是 Debian 打包层（不进 conan），真实依赖仅 zlib（zlib.h 的
  crc32 + 链接 -lz）→ conan `zlib/1.3.1.1`（ohpcd 已发布，OHOS armv8 缓存
  为静态 `libz.a`）。
- `linux/cramfs_fs.h`（struct cramfs_inode：mode:16/uid:16、size:24/gid:8、
  namelen:6/offset:26）与 `byteswap.h`（bswap_16/32）由 OHOS NDK sysroot
  （ohos-sdk 26.0.0.18 native/sysroot）直接提供，无缺失。
- 版本可得性三面验证：①Debian pool 实取 tarball + sha256；②`.dsc` 声明值
  逐字符比对；③`git ls-remote --tags salsa` 命中 `debian/1.4.5`。

## 探索期实测（设备 clang 15.0.4，target aarch64-unknown-linux-ohos）

- 原样编译：4 处 `-Wimplicit-function-declaration`（read/write/lseek/close，
  缺 `<unistd.h>`）——仅告警不报错，但属老式 Makefile 典型欠账，补丁显式
  包含。
- 裸 `cramfsswap`（argc!=3）打 Usage 退出 1；无任何版本/帮助探针 → CI L2
  冒烟四项（--version/--help/-V/-h）全 rc!=0 必判 FAIL → 补丁新增
  `--version`/`-V`/`--help`/`-h`（argc==2 运行时分支，rc=0，自报
  CRAMFSSWAP_VERSION）。
- 默认 clang 产物即满足 L4：DYN（PIE）+ GNU_STACK RW（NX）+ GNU_RELRO +
  BIND_NOW，无需额外 flags。
- **上游 Makefile 的 `all: cramfsswap strip` 在 OHOS 上不可用**：hnp clang
  产物自带 `.codesign` 链接签名（readelf -S 可见 section [37] .codesign），
  `strip` 重排 ELF 后签名与内容不再一致，内核拒绝 exec——报
  `Operation not permitted`（rc=126），文案极易误读为权限/HMDFS 问题。
  本任务对照实测：同一源文件 `clang -O2` 产物可执行，`cp && strip` 后即
  EPERM（两份文件属主/权限位完全相同，唯一差异是 strip）。修复：配方
  `make` 直指 `cramfsswap` 目标（跳过 `strip` 目标），不改上游源码。
- sysroot `libz.so` 与 conan 缓存 `libz.a` 都可链接；取 conan zlib（静态）
  ——产物 DT_NEEDED 仅 libc.so，干净环境下可直接执行（无 LD 注入需求）。

## 夹具设计（test_package）

上游 autopkgtest test-cmd 依赖 util-linux 的 mkfs.cramfs（OHOS CI 无此工具；
设备 .harmonybrew 有但 CI worker PATH 不含 harmonybrew，不得依赖）。夹具改为
确定性 Python 字节构造（4192B：root 目录 + 1 个 4096B 普通文件 + 1 个块
指针），要点：

- flags=0x3（FSID_VERSION_2|SORTED_DIRS）：cramfsswap 要求 bit0 且拒绝
  flags & 0xFFFFFFFC，故 flags 只能取 0x1/0x2/0x3。
- inode 位域按 LE LSB 先排（mode:16|uid:16、size:24|gid:8、namelen:6|
  offset:26），与 aarch64 LE 设备上 struct cramfs_inode 的内存布局一致。
- fsid.crc 预填 crc32(crc 字段清零的镜像)——与 cramfsswap 输出侧重算口径
  一致，保证「再换复原」断言逐字节成立（否则复原镜像与原镜像差 crc 字段）。
- 块指针值 = 数据块结束字节偏移（4192），单块文件 nblocks=1。

等价性增证（不入库，设备本机）：util-linux 2.42.3 `mkfs.cramfs -E` 生成真实
镜像 → 交换/复原断言同过（swp2 与 org `cmp` 一致，CRC 重算
0x4315ac1c/0xefb7a662）。

## 测试统计口径

- 上游 N=1（autopkgtest test-cmd，1 个测试；上游无其他测试套件——无 tests/、
  Makefile 无 check 目标）。其内部 2 个退出码断言（首换须不同、再换须复原）
  在 test_package 以同名语义断言执行。
- test_package 断言 11 项（其中鸿蒙/适配特有 3 项），夹具 2 件运行期生成，
  无二进制入库。
