# mbr 1.2.2 适配笔记

## 编译环境
- 构建系统: autotools（自带 configure / Makefile.in，无需 autoreconf）
- 编译日期: 2026-10-01
- 编译器: clang（OHOS SDK 26.0.0.18 / aarch64-unknown-linux-ohos）
- 构建期工具: dev86/0.16.21（as86 / ld86）、xxd/9.1.0（均经 `tool_requires` 注入，CI 自带）
- 状态: built

## 编译步骤

Conan 驱动构建（`conan create`），`AutotoolsToolchain` 注入 CC/CFLAGS（R33），`VirtualBuildEnv` 把
tool_requires 的 bindir（as86、xxd）挂到构建 PATH；补丁经 `apply_conandata_patches` 应用后：

```
./configure --prefix=/ ... --sbindir=${prefix}/bin --host=aarch64-unknown-linux-gnu
make -j1
make install DESTDIR=<package_folder>
```

上游的构建是「8086 汇编 → 裸镜像 → C 数组 → aarch64 宿主程序」三段式：

```
mbr.S86 --clang -E -xc--> mbr.i86 --as86 -0 -b--> mbr.b --xxd -i | clang -c--> install-mbr
```

`sbin_PROGRAMS = install-mbr`，Conan 生成的 `--sbindir=${prefix}/bin` 使其落在 `bin/install-mbr`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | as86 报 87 处 `unbound label`、`make` 失败（rc=2） | HMDFS 大小写不敏感：make 检查中间产物 `mbr.s86` 时被同名源文件 `mbr.S86` 满足（stat 解析到同一文件），预处理配方 `%.s86: %.S86` 被跳过，as86 直接汇编未预处理的源码；源文件本身未被改动 | `patches/0001` 把中间后缀 `.s86` 改为 `.i86`（同步 `Makefile.am` 与 CI 实际使用的 `Makefile.in`），产物字节不变 |
| 2 | `make -j` 报 `jobserver mkfifo: Operation not permitted` | HMDFS 上 mkfifo 受限（与 E074 同源） | `autotools.make(args=["-j1"])` 串行构建 |
| 3 | 构建期无 as86 / xxd（系统与 OHOS SDK 只带 llvm-objcopy） | 上游构建依赖 bin86(as86) 与 xxd | `tool_requires("dev86/0.16.21")` + `tool_requires("xxd/9.1.0")`（制品仓均有预编译包，CI 无需从源码构建工具） |
| 4 | `install-mbr <零镜像>` 拒绝安装 | 目标必须已有 0x55AA 引导签名，否则需 `--force`（上游安全检查，非缺陷） | 消费者测试据此构造镜像：510 字节零 + `55 AA`；另用 `--force` 覆盖零镜像路径 |

## 源码修改

- `patches/0001-case-distinct-intermediate-suffix.patch`：`Makefile.am`（9 处）与 `Makefile.in`（10 处）
  把预处理中间后缀 `.s86` 改为 `.i86`（含 `SUFFIXES` / `.SUFFIXES`、`CLEANFILES`、`y2k`/`testdisk`
  显式规则）。补丁由原始 tarball 与改动后副本 `diff -u` 生成，`patch -p1` 干净应用。
  未改动任何 `.c` / `.S86` 源码，`mbr.b` / `y2k.b` / `testdisk.b` 产物字节与上游一致。
- `conanfile.py`：`tool_requires` 注入构建期工具；`make -j1`；`package_info().bindirs = ["bin"]`。

## 依赖版本

- 运行期库依赖: 无（仅 libc）
- 构建期工具（tool_requires）: dev86/0.16.21、xxd/9.1.0

## 验证结果

- 干净源码树 + `patch -p1`（用本 PR 的补丁）：`configure rc=0`、`make rc=0`（预处理配方执行 3 次、
  0 处 as86 报错）；产物 `mbr.b` 512B、`testdisk.b` 512B、`y2k.o` 1480B、`install-mbr` 39296B；
  `mbr.S86` 未被改动（与 tarball 原文件 `cmp` 一致）。
- 未打补丁的对照：同一构建 `make rc=2`，as86 报 87 处 `unbound label`，预处理配方执行 0 次。
  两阶段端到端复现见 `knowledge-extension/reproduce.sh`（rc=0）与 `reports/test-report.md` §3.4。
- `install-mbr --version` → `install-mbr 1.2.1`（上游版本串未随 1.2.2 更新），`--help` 正常列出选项。
- 上游 `make check` 6 个注册用例：4 PASS（inst-4/6/7/8），2 FAIL（inst-1/inst-3，均为上游测试陈旧的
  旧磁盘布局断言，任何平台都失败）。21 个 tests/ 脚本的清点与逐项结果见 `reports/test-report.md`。
- Conan 侧 `conan create`（含 test_package 10 项消费者断言）结果见本文件末尾复验记录与
  `reports/test-report.md`。

## 注意事项

- 上游 `tests/` 中 `mbr-1..6`、`testdisk-1..6` 需 DOS VM86 harness（`harness/harness`），本构建下
  wraptest 以 exit 77 跳过；`inst-2`、`inst-5`、`version` 需 RCS `co` 从 `historic,v` 生成历史镜像，
  上游未注册进 `TESTS`。以上均非适配引入。
- `debian/` 目录保留在源码中原样未用（Debian 打包元数据）；本配方直接从源码构建，
  `debian/rules` 不参与，且其本身也不跑 `make check`。
- 源码 URL 使用 Debian pool 官方源：mbr 是 Debian 原生维护包（历史作者页
  chiark.greenend.org.uk/~neilt/mbr 已停更，debian/copyright 亦声明 "current source code is
  available directly from Debian"）。

## 编译结束

最终状态: built
COMPLETED
