# dict 1.13.3 适配笔记

## 编译环境
- 构建系统: autotools（tarball 自带 configure，无需 autoreconf；构建期需 flex/bison/awk）
- 编译日期: 2026-09-16
- 编译器: clang 15.0.4 / clang++ (libc++)
- 状态: built

## 编译步骤

```bash
# 1. 依赖准备（cmd-pkgs 预编译包）
#    libmaa 1.4.7（vendored 静态构建，见 conanfile.py _build_vendored_libmaa）
#    zlib 1.3.1（本机验证用；配方依赖 zlib/1.3.2 静态）
#    libtool 2.4.7（本机验证用；配方 tool_requires libtool/2.5.4）
# 2. 补丁：config.guess/config.sub 增加 HarmonyOS 识别（2021 版脚本无 aarch64:HarmonyOS 分支）
# 3. configure / make / make test / 归档
./configure --prefix=$DEFAULT_PREFIX \
    LDFLAGS="-L/storage/Users/currentUser/usr/local/lib" \
    CPPFLAGS="-I/storage/Users/currentUser/usr/local/include"
make -j1
make test        # 上游测试入口（非 make check）
```

> **OHOS 关键对策**（与先例 dictd/1.13.3 一致）：
> 1. HMDFS 上 config.status/mktemp 临时目录权限语义不可靠 → 构建移至 `/data/storage/el2/base`
>    tmpfs（conanfile `_prepare_ohos_workdir` 复制源码到 tmpfs 构建）
> 2. 设备 bash 启动时 getcwd() 在 HMDFS 路径失败 → 每个 self.run 以 `cd '<workdir>' &&` 前缀
>    重建工作目录；configure 用 bash + export PWD，make/libtool 用 CONFIG_SHELL=/bin/sh
> 3. AC_PROG_LEX(yywrap) 无 -lfl 时把 LEX 降级为 ':'（静默不生成 scanner）→ conanfile
>    `_pregenerate_scanners` 按上游命令行预生成 4 个 scanner/parser 文件
> 4. libtool 在设备镜像无二进制 → tool_requires libtool/2.5.4

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `config.guess: unable to guess system type` | 2021-06-03 版 GNU config 脚本无 HarmonyOS 分支 | patches/0001-config.guess.patch（aarch64:HarmonyOS → aarch64-unknown-linux-ohos）、0002-config.sub.patch（ohos 识别） |
| 2 | `config.status: can't create ./confOGoOgM/subs1.awk: Permission denied` | HMDFS umask 077 临时目录权限语义（E011 族） | 构建目录移到 tmpfs `/data/storage/el2/base`，TMPDIR/TMP/TEMP 指向 tmpfs 下 0700 目录 |
| 3 | `Libmaa not found`（configure 硬查 -lmaa） | dict 硬依赖 libmaa，仓内无 Conan recipe | conanfile source() 拉取官方 libmaa-1.4.7 归档，build() 内 vendored 静态构建（clang 直编 maa/*.c，mkc 特性宏命令行提供，arggram.c 用 awk 预生成） |
| 4 | `libmaa.so: undefined reference: tim_start/tim_stop` | cmd-pkgs 预编译 libmaa 排除了 timer.c，但 maa.c 引用 tim_* 符号 | 重建 libmaa 时保留 timer.c（-DHAVE_HEADER_SYS_RESOURCE_H=1，musl 提供 struct rusage）；与先例 dictd 纠正结论一致 |
| 5 | `make: [Makefile:174: servscan.c] Error 1`（LEX=: 静默） | AC_PROG_LEX 找不到 yywrap 提供库 | `_pregenerate_scanners`：flex servscan.l / bison -tdv servparse.y 等 4 个文件预生成 |
| 6 | libtool 报 `sed: inaccessible` | cmd-pkgs libtool 2.4.7 脚本内 SED 绝对路径错误 | 本机验证期修复 usr/local/bin/libtool 的 SED=/usr/bin/sed；配方侧用 tool_requires libtool/2.5.4（CI 干净环境） |

## 源码修改

- `patches/0001-config.guess.patch`：config.guess 增加 `aarch64:HarmonyOS:*:*)` 分支与
  `#elif defined(__OHOS__)` LIBC 探针（R8 许可的平台探测，非空 stub）
- `patches/0002-config.sub.patch`：config.sub OS 列表与 kernel-os 校验增加 ohos/linux-ohos
- 其余为配方/构建配置修改（conanfile.py），上游源码无其他改动

## 依赖版本

- zlib/1.3.2（Conan requires，静态链接）
- libtool/2.5.4（tool_requires，构建工具）
- libmaa 1.4.7（vendored 静态构建，源归档固定于 conandata.yml，SHA-256 4e01a9eb...）
- flex 2.6.4 / bison（scanner/parser 预生成）、gawk（arggram2c）

## 验证结果

```bash
# conan-verify（8 道门禁）：G0-G4 + L2/L4/L5 全部 PASS（reports/conan-verify-report.md）
# 上游测试 make test：47/47 通过（DICTFMT 21 + DICTD 17 + DICTZIP 9）
#   reports/upstream-test-ledger.md + reports/conan-create.log（40 个 passed 标记）
# test_package 消费者冒烟：SMOKE_OK（dict/dictd 版本 banner、dictzip 往返、
#   dictfmt+dictd --stdin2stdout 协议应答）→ reports/conan-create.log
# W3 本地 CI：通过（reports/w3-local-ci.log + .ci-result.json exit_code=0）
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | application 配方：vendored libmaa + zlib + libtool，OHOS tmpfs 构建 |
| conandata.yml | 官方 SourceForge URL + sha256（dictd-1.13.3.tar.gz、libmaa-1.4.7.tar.gz） |
| patches/ | config.guess/config.sub HarmonyOS 识别补丁 × 2 |
| test_package/ | 消费者冒烟（test.sh + conanfile.py + MANIFEST.yml） |
| commands.json | 软件级 CLI 声明（R38，dict 产出可执行文件集） |
| reports/ | conan-verify-report / test-report / upstream-test-ledger / knowledge-candidate-ledger / w3-local-ci.log |

## 注意事项

1. 上游不产出独立 `dictunzip`：dictzip.c 按 argv[0] 分派解压模式，安装时以
   dictunzip→dictzip 链接提供（同先例 dictd）
2. `make check` 不存在，上游测试入口为 `make test`
3. 知识侧：与仓内 dictd/1.13.3（同一上游同一 tarball）完全重复，七轴查重均为
   重复/覆盖（reuse_existing），未新建草稿（见 reports/knowledge-candidate-ledger.md）
4. manifest.yaml configure_options 的 `--prefix=<pkg>` 中 `<pkg>` 即 Conan package_folder
---

**编译结束**: 2026-09-16 20:15
**最终状态**: built
