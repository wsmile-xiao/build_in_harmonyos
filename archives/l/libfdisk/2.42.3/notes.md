# libfdisk 2.42.3 适配笔记

## 编译环境
- 构建系统: autotools (configure + make)
- 编译日期: 2026-09-25
- 编译器: clang/clang++
- 状态: built（待真机 rule4 预检后由 HMBS 提交）

## 上游信息
- 名称: libfdisk（util-linux 套件中的分区表操作库）
- 版本: 2.42.3（2026-09-02 发布）
- 仓库: https://github.com/util-linux/util-linux
- 归档: https://cdn.kernel.org/pub/linux/utils/util-linux/v2.42/util-linux-2.42.3.tar.xz
- sha256: 66ac7c0e725278eb2b039e3104f2c91119341d941b41bac7a285c695f940bd57（官方 sha256sums.asc）
- 许可证: LGPL-2.1-or-later（库部分）

## 编译步骤

配方裁剪（library view，只编库）：
```bash
configure --host=aarch64-unknown-linux-ohos --build=aarch64-unknown-linux-ohos \
  --disable-all-programs \
  --enable-libfdisk --enable-libuuid \
  --disable-libblkid --disable-libmount --disable-libsmartcols --disable-liblastlog2 \
  --disable-pam --disable-libudev \
  --without-systemd --without-selinux --without-audit --without-utempter \
  --disable-bash-completion --disable-nls \
  --disable-makeinstall-chown --disable-makeinstall-setuid \
  --enable-static --disable-shared   # shared=False 时
make -j1
make test_fdisk_ask test_fdisk_gpt test_fdisk_script \
  test_fdisk_utils test_fdisk_version test_fdisk_item  # 只构建本包 own 的 6 个单元二进制（作用域构建，不用顶层 make check：后者连带 lib/test_netlink 在 OHOS sysroot 下报 sockaddr_storage 重定义）
# 6 个二进制必须带 TEST_PROGRAM 子命令（裸执行按设计打印 Usage 并 exit 1，见 libfdisk/src/test.c:fdisk_run_test）：
test_fdisk_ask --ranges
test_fdisk_version --print
test_fdisk_utils --partnames /dev/sda
test_fdisk_script --tokens "a,b,c"
# gpt/item 需 GPT 标签：TMPDIR 建 10MB 文件 + mk_gpt 小助手（刚构建的
静态库编译：fdisk_new_script_from_file + fdisk_apply_script +
fdisk_write_disklabel，单分区脚本 `start=2048, size=8192,
type=0FC63DAF-...`）写入含 1 个 Linux 分区的真 GPT 后再测
（test_fdisk_script --apply 从不落盘：libfdisk/src/script.c test_apply
尾部 `/*fdisk_write_disklabel(cxt);*/` 被注释，不能做 fixture）：
./mk_gpt /tmp/gpt.img /tmp/gpt.script
./test_fdisk_gpt --getattr /tmp/gpt.img 1
./test_fdisk_item --list-items /tmp/gpt.img
make install
```

OHOS 适配沿用 util-linux 2.42 同款（同 tarball 家族）：
1. `config/config.guess` + `config/config.sub` 增加 ohos 识别（2026 新版格式）。
2. `configure` 首行注入 `umask 000` 并替换 `umask 077 && mktemp`（E011 hmdfs）。
3. `TMPDIR` 真实写入探测后选择（优先 HMBS 注入的任务 tmpdir，可写才用；
   回退 `build_folder/.tmp`；coinor-vol 教训：硬编码不存在/不可写目录
   会导致首个 conftest 报 `C compiler cannot create executables`，
   Error 77），并同步导出 `TMP`/`TEMP`。
4. `include/getusershell.h` 兼容头 + `lib/shells.c` 包含（OHOS 无 /etc/shells API）。
5. `include/versionsort.h` 兼容头（musl 无 GNU 扩展）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | libfdisk 需要 libuuid，裁剪后能否独立构建 | configure.ac `UL_REQUIRES_BUILD([libfdisk],[libuuid])` | 同时 `--enable-libuuid`，产出的 libuuid 随包捆绑，package_info 声明 `libs=["fdisk","uuid"]` |
| 2 | `make check` 是否跑 ts/fdisk 需要的 fdisk 程序 | ts 套件需完整工具集，本包已禁用全部程序 | 库视图只 own 6 个单元二进制（Makemodule.am check_PROGRAMS），ts/fdisk 16 + ts/sfdisk 7 归工具包，不重复计数 |
| 3 | Windows 检出主干遇到 `gama` 坏文件名与 `libXext/libxext` 大小写冲突 | 上游历史归档缺陷，与本包无关 | `core.protectNTFS=false` + skip-worktree 绕过坏文件；大小写冲突保持未修改，由 HMBS Linux 端处理 |
| 4 | 真机 `checking whether the C compiler works... no`，Error 77（CC 已解析为 `/data/service/hnp/bin/clang`，非缺编译器） | 首轮怀疑配方硬编码 `TMPDIR=build_folder` 不存在/不可写 | 新增 `_pick_writable_tmpdir()` 真实写入探测：优先 HMBS 注入的任务 TMPDIR，可写才用，回退 `build_folder/.tmp`；generate/build 双处生效并同步 `TMP`/`TEMP`。复测：TMPDIR 已正确（runtime/.../tmp）但仍 Error 77，且进程 `CC=''`——证伪 TMPDIR 主因，见 5 |
| 5 | 同上复现（第 2 次同指纹失败）：TMPDIR 正确、进程 CC 为空，真实链接错误被 configure 汇总行掩盖 | 进程 env 无 CC（仅 toolchain 脚本内解析），聚合顺序存疑；且无 config.log 真实错误，下轮无法定位 | （与上轮不同策略）新增 `_resolve_ohos_compiler()`：按 conf→env CC/CXX→PATH clang 顺序存在性校验，仅导出 CC/CXX（不动 flags/sysroot，libe131 适配）；generate 落盘 conanbuild 脚本 + build 写入 live env；`autotools.configure()` 失败时转储 config.log 尾部 60 行及 error/cannot 行，仅诊断不伪造 |
| 6 | 顶层 `make check` 在 `lib/test_netlink-netlink.o` 失败：`linux/socket.h` vs `sys/socket.h` 的 `sockaddr_storage` 重定义（OHOS sysroot 双头文件均定义该结构体，glibc 守卫在 musl/OHOS 不生效），`make[3] check-am → check-recursive → check` 连锁 Error 2 | 本包 library view 只 own libfdisk 6 个单元二进制；`make check` 构建全树 check_PROGRAMS，连带与本包无关的 `lib/` 套件测试 | 作用域构建：`build()` 改为按显式目标名逐个 `make test_fdisk_*`（6 个），不再调用顶层 `make check`；MANIFEST/notes 同步更新命令口径。不改 OHOS sysroot 头文件，不跳过本包任何自有测试 |
| 7 | 真机上游 0/6 全败，每项 `rc=1 tail='Usage: test_fdisk_item <test> [testoptions] Tests: --list-items <disk> list items'`（2026-09-25 预检） | 配方把 6 个 `-DTEST_PROGRAM` 二进制当自包含单元测试裸执行；`libfdisk/src/test.c:fdisk_run_test()` 无参数/--help 时按设计打印 Usage 并返回 EXIT_FAILURE，各二进制必须带子命令（version.c `--print`、ask.c `--ranges`、utils.c `--partnames <disk>`、script.c `--tokens <str>`、gpt/item 需磁盘镜像） | 按上游源码逐个修正调用：ask `--ranges`、version `--print`、utils `--partnames /dev/sda`（纯字符串格式化，无需真实设备）、script `--tokens "a,b,c"`；gpt `--getattr` 与 item `--list-items` 需 GPT 标签，在探测可写 TMPDIR 内建 10MB 稀疏文件并用刚构建的 `test_fdisk_script --apply`（`label: gpt` 脚本）写入空 GPT 后再测；空二进制/空输出仍大声失败，不做 stdout 字符串数数，计数唯一来源为进程退出码 |
| 8 | 真机 source() 下载中断：三个国内镜像对 v2.42.3 均 404，随后 cdn.kernel.org 下载 10.7MB 到 38%（4.1MB）时 `Connection closed by remote host`（2026-09-25 预检，compile 阶段） | 国内镜像对新版本同步缺口（404），单靠 cdn 直连大包长下载无后备，抖动即致命；`www.kernel.org/pub/.../v2.42/` 官方目录确认 2.42.3 存在 | conandata.yml 在国内三镜像后插入同源官方端点 `mirrors.edge.kernel.org` + `www.kernel.org`（与 sibling util-linux/2.42、util-linux-login/2.42.2 同源链一致，同归档同 sha256 不变，cdn 仍最后回退）；conanfile.py `source()` 改逐 URL try/except 重试（单源超时/中断 warn 后落到下一源），py_compile 已验证 |
| 9 | 19:08 轮复现：国内三镜像仍 404，但 `mirrors.edge.kernel.org` 已成功完成 10.7MB 下载（Sources correctly downloaded），configure 成功，make 至 `CC lib/libcommon_la-mangle.lo` 时 `Connection closed by remote host` | 下载链已可用（edge 成功），剩余失败在编译阶段 SSH 链路抖动；但国内 404 仍排在前面造成 3 次无效探测、拉长下载窗口 | conandata.yml 重排序：已验证成功的 `mirrors.edge.kernel.org` + `www.kernel.org` 置顶直达，国内三镜像降为中间回退（待同步后可用），`cdn.kernel.org` 仍最后官方回退；sha256 不变，复用 ci/conan/build_and_test.sh kernel.org 映射，不引入 GitHub 等异源归档 |
| 10 | 真机上游 4/6：`test_fdisk_gpt --getattr <img> 1` rc=1 `FAILED [rc=1]`、`test_fdisk_item --list-items <img>` rc=1 `FAILED [rc=-22]`（2026-09-25 23:17 预检，fixture `--apply` rc=0） | fixture 误用：`libfdisk/src/script.c:test_apply()` 尾部 `/*fdisk_write_disklabel(cxt);*/` 被注释，`--apply` 只做内存应用+列表从不落盘，10MB 文件仍全零故 GPT 探测失败（getattr 非 GPT→EXIT_FAILURE；list-items 无标签→EINVAL=-22）；且空 `label: gpt` 脚本零分区，`--getattr 1` 本就无分区可查 | 新增 `_build_gpt_image()`：TMPDIR 写单分区脚本（`label: gpt/unit: sectors/start=2048, size=8192, type=0FC63DAF-...`），用刚构建的 libfdisk.a+libuuid.a 现场编译 mk_gpt 小助手（new_script_from_file+apply+write），运行落盘后校验 LBA1 `EFI PART` + MBR `55AA` 双签名；单分区保证 `--getattr 1` 有对象。不删断言不跳过，计数仍唯一来自退出码 |
| 11 | 真机 package() 在 `install-man3` 报 Error 64（2026-09-26 预检；build/make 及上游 6/6 已通过，`install -c -m 644 <15 个 uuid man> .../share/man/man3` 失败） | HMBS install shim 只接受单文件双参（`[ $# -eq 2 ] \|\| exit 64`，EX_USAGE），automake install-man3 把全部 man 页合并成一次多文件调用；能力表 `install_shim:true + chmod:0` 佐证，与 lzop/1.04 同指纹 | package() 前写入多文件 install wrapper（SRC... DEST 逐个 cp，吞掉 -c/-m/-o/-g/-D，chmod 失败容错；os.open 0o755 创建以 surviving HMFS chmod=0），递归改写 build_folder 下全部 Makefile 的 INSTALL/INSTALL_DATA/INSTALL_PROGRAM/INSTALL_SCRIPT 指向 wrapper（out-of-source build-release 含在内），再 autotools.install()。man 页经 cp 安装，库与头文件同语义不受影响；不跳过安装、不删 man（lzop/1.04 + xylib/1.6 先例） |
| 12 | 真机 test_package 非法标记 `passedCount:12/discovered:8` 且 `rc=1 passed 12/8 lines`（2026-09-26 预检；上游 6/6 已通过） | 双重错误：① C 文件实际 14 个 CHECK 但 `TEST_CHECKS=8` 声明过期，`passedCount(12) > discovered(8)` 触发门禁；② 两个 CHECK 误判上游返回值语义——`fdisk_get_library_version` 返回版本码（2423，见 version.c `return fdisk_parse_version_string(lib_version)`）却判 `==0`，`fdisk_get_library_features` 返回特性数（1-2，见 version.c `return ARRAY_SIZE-1`）却判 `==0`，故 14 中恰 2 失败、12 通过、rc=1 | test_libfdisk.c 修正两处判定（version `>0` + 非空串；features `>=0` + 指针非空，均引 version.c 为据），`TEST_CHECKS` 8→14 并同步 MANIFEST `assertion_count`/notes/pr-body 草稿描述；不删断言不跳过，计数仍唯一来自 `PASS:`/`FAIL:` 行与退出码 |

## 源码修改

无 patches/（`patches: {}`）。所有 OHOS 适配通过 recipe 内代码生成
（兼容头写入 + configure/config.guess 原地补丁），不引入补丁文件，
避免 R18 手工补丁与平台宏争议。

## 依赖版本

无外部 Conan 依赖（requires: []）。libuuid 随包内建，不依赖外部包。
工具链由真机提供（clang 15 + /data/service/hnp + conan 2.30，同官方 CI）。

## 验证结果

待 HMBS 真机预检（本轮只完成未提交工作树，不伪造数字）：
- 上游 6 个单元二进制：以退出码计数，`HMBS_UPSTREAM_TEST_RESULT` 为准。
- test_package `test_libfdisk` 14 个 CHECK：以 `PASS:` 行计数，
  `HMBS_TEST_PACKAGE_RESULT` 为准。
- 证伪要点：测试二进制非空、fixture 非空；`make check` 构建产物逐个执行，
  不做 stdout 字符串数数或减法推导。

## 交付物

| 文件 | 说明 |
|------|------|
| archives/l/libfdisk/2.42.3/conanfile.py | 主配方（autotools + 6 单元测试驱动 + 双通道标记） |
| archives/l/libfdisk/2.42.3/conandata.yml | 官方源 + sha256（cdn/mirrors.edge/www 三官方端点） |
| archives/l/libfdisk/2.42.3/test_package/ | 消费者测试（14 CHECK 真实 API）+ MANIFEST.yml |
| archives/l/libfdisk/2.42.3/manifest.yaml | 版本级 manifest（status=built） |
| archives/l/libfdisk/README.md + manifest.yaml | 软件级描述 |

## 注意事项

- 本包与 `util-linux/2.42`（blkid/uuid/mount 视图）同源但视图正交：
  本包 own 6 个 libfdisk 单元测试，不声明 ts 套件总数，避免跨包重复计数。
- 默认静态（shared=False）：OHOS 系统库同名风险低，但保持静态可直接链接，
  与 util-linux 家族一致。
- 真机 `binary-sign-tool` 签名逻辑已按 libfdt 最新模式接入（OHOS 可执行挂载限制）。
