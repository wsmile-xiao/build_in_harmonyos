# udfclient 0.8.21 适配笔记

## 编译环境
- 构建系统: autotools（configure + Makefile.in；上游 configure 由 autoconf 2.72 生成）
- 编译日期: 2026-09-27
- 编译器: clang 15.0.4（OHOS SDK；C 项目未用到 clang++）
- 目标平台: HarmonyOS PC (OHOS) aarch64（conan profile: ohos-aarch64）
- 状态: built（conan-verify G0-G4 通过，尚未 CI release 上传）

## 编译步骤

1. 官方源码: `https://www.13thmonkey.org/udfclient/releases/UDFclient.0.8.21.tgz`
   （上游作者 Reinoud Zandijk 的官方发布目录；sha256 = 83deab4d...，见 conandata.yml）
2. `ohc-run.py init-build udfclient 0.8.21 --url=<上述URL>` → `$TMPDIR/builds/udfclient-0.8.21.{orig,work}`
3. `ohc-run.py lang-preflight` → task=cpp / detected=c（C/C++ 兼容族），通过
4. 探索编译（.work）:
   ```bash
   ./configure --prefix=$DEFAULT_PREFIX && make -j1
   ```
   成功后产出 6 个可执行文件: udfclient、udfdump、newfs_udf、cd_sessions、cd_disect、mmc_format
5. `ohc-run.py conan-init` + `refresh-patch --auto` → 生成 4 个补丁（见下）
6. `ohc-run.py conan-verify udfclient 0.8.21 --profile ohos-aarch64-device` → G0-G4 PASS

## 上游测试清点（R51）

- tarball 内无 `tests/` / `test/` 目录（`tar tzf UDFclient.0.8.21.tgz` 无测试路径）
- `Makefile.in` 无 `check`/`test` 目标（仅 all/install/depend/clean/cleandir 与
  libudf.a / libuscsi.a / 程序链接规则）
- `configure.ac` 无 `AC_CONFIG_TESTDIR` 等测试注册
- 结论: 上游 N=0，无可运行上游测试；按 R51 以消费者端到端测试补偿（test_package/test.sh）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure: error: cannot guess build type` | 2018 版 config.guess 无 HarmonyOS 分支（`uname -s` = HarmonyOS 不匹配已知系统） | 补丁 0002：在 uname 大 case 首部增加 `*:HarmonyOS:*:*)` 分支（aarch64/arm/x86_64/i686 → `-unknown-linux-ohos`）。注意该版本分支需自行 `echo`+`exit`；框架 `patch-autotools-ohos.pl` 仅适配新式结构未命中，按实际结构手写（E007/E160） |
| 2 | conan autotools 传 `--host=aarch64-linux-ohos` 时 config.sub 报 `system 'ohos' not recognized` | 2018 版 config.sub 的 KERNEL-OS 白名单无 `linux-ohos` | 补丁 0003：`maybe_os` 判定分支与 Basic OS 列表两处增加 `linux-ohos*`（与 aalib 同款最小修改，E205） |
| 3 | `config.status: ./confXXXXXX/subs1.awk: Permission denied` | HMDFS 强制目录 setgid；`umask 077 && mktemp -d` 生成的 `drwx--S---` 目录属主亦不可写（E114） | 补丁 0004：移除 configure 中 config.status 临时目录创建的 `umask 077`（aaphoto 同款方案） |
| 4 | `make: jobserver mkfifo: ... Operation not permitted`（-j>1） | GNU make 在 HMDFS/TMPDIR 创建 jobserver fifo 被拒（E074） | conanfile 中 `autotools.make(args=["-j1"])` |
| 5 | GNU make 无法构建（符号 `$(.TARGET)` 为空） | 上游 Makefile.in 为 BSD make 语法（bmake/pmake；Debian 亦用 `--buildsystem=bmake`） | 补丁 0001：两条链接规则改为 GNU make 静态模式规则 `targets: %: %.o ...` + `$@.o` |

## 源码修改（补丁）

| 补丁 | 修改内容 |
|------|----------|
| 0001-Makefile.in.patch | `$(SCSI_APPS)`/`$(APPS)` 链接规则：BSD `.TARGET` → GNU make 静态模式规则（`$@.o`） |
| 0002-config.guess.patch | 新增 `*:HarmonyOS:*:*)` 分支（aarch64/arm/x86_64/i686 → `-unknown-linux-ohos`，echo+exit） |
| 0003-config.sub.patch | `maybe_os` 分支与 Basic OS 列表增加 `linux-ohos*` |
| 0004-configure.patch | config.status 临时目录创建移除 `umask 077`（E114） |

## 依赖版本

| 依赖 | 版本 | 来源 | 说明 |
|------|------|------|------|
| libc | OHOS SDK 自带 | — | strlcpy/endian.h/struct stat st_atim 等均可用 |
| pthread | libc 内置 | — | configure `-lpthread` 探测通过 |
| scsi/sg.h | OHOS SDK 自带 | — | Linux SCSI 后端（`-DUSCSI_LINUX_SCSI`），启用 cd_disect/mmc_format |
| 第三方库 | 无 | — | W0 依赖检查：resolve-deps 为空，无需 `conan download` |

## 验证结果

```bash
# conan-verify（G0-G4；本地设备用 ohos-aarch64-device profile）
python3 scripts/ohc-run.py conan-verify udfclient 0.8.21 --profile ohos-aarch64-device
# → G0-G4 PASS；test_package 消费者测试 13 项断言全部通过

# 手工端到端（设备，.work 构建产物）
newfs_udf -L TESTVOL -b 2048 -s 8192 test.udf    # 创建 16 MiB UDF 镜像
udfdump -S test.udf                               # 描述符扫描（含卷标 TESTVOL）
udfdump -b 2048 -t test.udf                       # 卷集信息 + 目录树
printf 'ls\nexit\n' | udfclient -b 2048 test.udf  # 只读挂载并列出文件集
```

## 注意事项

- 文件型 UDF 镜像需显式 `-b 2048`（工具默认按光盘介质推断扇区大小）。
- 上游 configure.ac 的 `AC_INIT` 版本串仍是 0.8.12（上游未随 tarball 更新），
  与本适配版本 0.8.21 无关；未改动上游版本串。
- 镜像文件上的写命令（mkdir/put）返回 `Can't determine directory ...`，
  属上游对镜像文件写支持的限制（真实光盘介质不受影响）；本次验证覆盖
  创建/只读路径，写路径未纳入测试断言。
- 本地验证使用 `ohos-aarch64-device` profile（复制自共享 `ohos-aarch64`，
  工具链指向 Harmonybrew clang；CI 使用仓库内 `ci/conan/profiles/ohos-aarch64`）。
---

**编译结束**: 2026-09-27 15:22
**最终状态**: built
