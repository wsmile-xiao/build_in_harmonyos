# ciwiki 3.0.5 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-09
- 编译器: clang 15.0.4 (aarch64-linux-ohos)
- 状态: built
- 架构: OHOS aarch64 (armv8)

## 编译步骤

1. `init-build` 下载源码包 `ciwiki-3.0.5.tar.gz`（SourceForge 官方源，sha256=290aee7fe2efc8f1c2612b6aff2bb832d3c8129e6fd9dd9e6adbdb02d1f19aef，与 Alpine APKBUILD 记录一致）。
2. 源码为 autotools 项目，`./configure --prefix=$DEFAULT_PREFIX --host=aarch64-linux-ohos` + `make -j1` + `make install DESTDIR=$TEST_PREFIX`。
3. 产物：`bin/ciwiki`（ELF 64-bit aarch64 可执行）、`libexec/notifynewuser.sh`、`share/man/man1/ciwiki.1`。
4. `conan-verify` 8 道门禁（G0-G4 + L2/L4/L5）全部通过；finish W3 本地 CI 通过。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status 报 `can't create ./confXXXXXX/subs1.awk: Permission denied` | HMDFS 上 `mktemp -d` 创建 `drwx--S---`(2700+setgid) 临时目录，owner 也无法写入，chmod 无效（E114 平台限制） | conanfile.py `build()` 内置绕过：在 build_folder 预创建固定临时目录并 sed 替换 configure/config.status 中 `ac_tmp=$tmp` 指向该目录 |
| 2 | `ci.c:181: cannot assign to variable 'stdin' with const-qualified type` | musl/OHOS 将 `stdin` 声明为 `FILE *const`（glibc 可赋值），上游 `stdin = freopen(NULL,"r",stdin)` 依赖 glibc 行为 | 补丁 `0001-src-ci.c.patch`：改为可移植的循环消费残留输入 `while ((_c = getchar()) != '\n' && _c != EOF);`，全平台有效 |
| 3 | configure 报 `source directory already configured; run make distclean` | 上游 tarball 打包前已跑过 `./configure`，自带 config.status/config.log/config.h/stamp-h1/Makefile 残留产物 | conanfile.py `source()` 解压后递归删除这些残留产物，由 configure 重新生成 |
| 4 | `Autotools.configure()` 在 build 目录找不到 configure | 上游 tarball 顶层目录（ciwiki-3.0.5/）在个别解压路径下 strip_root 未生效；且 `get(keep_permissions=False)` 丢失脚本可执行位（E490） | conanfile.py `source()` 加固：若 configure 不在根目录则上移顶层目录内容；并 `chmod +x` configure/config.guess/config.sub/install-sh/missing/depcomp |
| 5 | conan-verify 首轮补丁未生效 | conandata.yml patches 误写为 dict（以补丁文件名为 key），不符合 conan `apply_conandata_patches` 期望的 list 格式 | 修正为 `patches: [{patch_file, patch_description, patch_type}]` list 格式 |

## 源码修改

- `patches/0001-src-ci.c.patch`：`ci.c` 中 `stdin = freopen(NULL,"r",stdin)` 改为循环消费残留输入的可移植写法（无平台宏，全平台有效）。

## 依赖版本

- 无第三方依赖（仅使用 C 标准库函数：asprintf/socket/select/strdup/strncasecmp 等）。

## 验证结果

```bash
# 上游测试（R51 穷尽检索）：源码包 + GitHub 仓库树(90文件) + 构建文件 + 文档均无独立测试套件，
# make check 注册 0 用例；唯一 scripts/check_public_ip.sh 为运维辅助脚本，非测试。
# 自研 test_package 断言（conan-verify G2 实测全部通过，7 项）：
$ src/ciwiki --version    # → CiWiki - version 3.0.5
$ src/ciwiki --help       # → Usage: ciwiki [options]（含 --port/--listen/--home 等）
# HTTP 往返：临时 home + 随机端口启动服务器，curl GET / 返回 HTML ✅
# conan-verify: G0/G1/G2/G3/G4 + L2/L4/L5 全部 PASS
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| conanfile.py | 4.6KB | Conan 配方（autotools，含 E114/E490/残留清理内置绕过） |
| conandata.yml | 0.4KB | 源码声明 + sha256 + patches |
| patches/0001-src-ci.c.patch | 0.9KB | stdin 可移植修复 |
| test_package/ | — | 自研消费者测试（conanfile.py + test.sh + MANIFEST.yml，7 项断言） |
| commands.json | 0.3KB | CLI 工具声明（软件级，R38） |

## 注意事项

1. 上游 tarball 自带 configure 产物（config.status 等），任何二次 configure 前必须清理。
2. `ciwiki --help` 中 `-d/--debug` 为从 stdin 读请求的调试模式，测试/日常使用 HTTP 服务时不得传 `-d`。
3. E114（HMDFS mktemp）绕过依赖固定临时目录路径，仅用于 configure/config.status 阶段。

---

**编译结束**: 2026-09-09 12:59
**最终状态**: built
