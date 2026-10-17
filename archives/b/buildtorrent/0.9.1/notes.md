# buildtorrent 0.9.1 适配笔记 (OHOS / aarch64)

- 适配日期: 2026-09-06
- 设备目标: HarmonyOS PC (aarch64)，clang 15
- 源: https://mathr.co.uk/web/buildtorrent/buildtorrent-0.9.1.tar.gz
  sha256 = ca7b2315dbfdb098f608af556eb80de88f989aeae18e49f105adb5b0f6b72937
  （与 PureOS/Debian 记录的 0.9.1.orig.tar.gz 一致，官方包直连下载实测 145623 字节同值）

## 探索过程（每项修改的依据）

1. 解包官方 tarball：顶层 26 文件，`configure.ac` + `Makefile.am` + 预生成 configure/Makefile.in，
   确认为 Autotools 工具型项目（`bin_PROGRAMS = buildtorrent`）。
2. 读 `Makefile.am`：仅 bin_PROGRAMS/man_MANS，无 TESTS/check_PROGRAMS；全包 grep 无 tests/、
   test/ 目录与 *test* 源文件，判定上游无测试套件（审计明细见 test_package/MANIFEST.yml）。
3. 读 `buildtorrent.c`：`versionsort` 调用处已有 `#ifdef _GNU_SOURCE` 守卫并回退 `alphasort`；
   `scandir`/`alphasort` 为 POSIX 接口，无需移植补丁。
4. 查 config.guess/config.sub：2022-01 版（早于 HarmonyOS，但已支持 aarch64）；
   参照 barcode 0.99 的 CI 验证写法，OHOS 下用 portable GNU triplets 过平台识别，
   不打 config 补丁。
5. HMDFS 可执行位剥离为本仓库高频问题（E050 系），build() 内先 chmod 恢复再 configure。

## 补丁清单

无（零补丁适配）。

## 上游测试（审计结论）

- `make check`：上游未提供 check 目标（Makefile.am 无 TESTS 定义），不执行。
- Debian 打包 rules 同样未运行任何上游测试，佐证无可接入套件。
- 证伪：`make -n check` 仅 automake 空桩；断言口径 TOTAL=0。

## test_package 设计（5 项内容级验证）

1. `--version` 报告 0.9.1（防空壳：必须 grep 到版本号）。
2. `--help` 输出 usage 且含 announce 选项。
3. 单文件 torrent 生成：`-a/-D/-B` 生成 .torrent，要求文件非空且含 announce/info/pieces
   三个 bencode 关键字（空文件比空文件无法通过）。
4. 确定性复现：相同 `-d 0 -b` 两次生成逐字节一致（cmp）且含 creator 标记。
5. `-M` 输出 magnet: 链接。

## 产物

- bin/buildtorrent（NEEDED 仅 libc）
- share/man/man1/buildtorrent.1
- licenses/COPYING

## 其他说明

- 零依赖：`requirements()` 为空，无需 W0 依赖发布检查的前置依赖项。
- 工具型包：`package_type = "application"`，`package_info()` 仅声明 `bindirs = ["bin"]`。
