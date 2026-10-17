# pce 0.2.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-15
- 编译器: clang/clang++ (HarmonyOS PC aarch64, clang 15, libc++)
- 状态: built（待真机 conan create 验证）

## 编译步骤

上游为经典 Autotools 工程（configure.in + Makefile.in + Makefile.inc.in）：

```bash
./configure --without-x --without-sdl --disable-readline --disable-tun --disable-sound-oss --prefix=/
make -j1
make install DESTDIR=<package_folder>
```

Conan 侧由 `AutotoolsToolchain` 生成工具链参数，`Autotools` 助手执行 configure/make/install。
OHOS 下追加 `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu` 做原生构建；
`extra_cflags` 追加 `-fcommon` 解决 e68000 目标的多重定义。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 官方源码站仅提供 http 链接 | hampa.ch 未提供 https，CI 下载可能不稳定 | conandata.yml 用 url 列表：https 的 NetBSD pkgsrc 镜像在前，官方 http 作为回退，sha256 保持一致 |
| 2 | 旧 config.sub 是否识别 OHOS | 2013 版 config.sub 不认识 linux-ohos | 改用标准 aarch64-unknown-linux-gnu triplet 做原生构建，无需补丁，host_os 仍判为 Linux 族 |
| 3 | SDL/X11/readline 在 OHOS 缺失 | 默认 configure 会探测 sdl-config 与 X，制品仓无 SDL | 显式 `--without-x --without-sdl --disable-readline`，做到零依赖 |
| 4 | e68000 链接报 multiple definition of e68_ea_tab | 上游 tentative definitions 与 clang 15 默认 -fno-common 冲突 | `tc.extra_cflags` 追加 `-fcommon`（Homebrew 同款处理） |
| 5 | 上游无 make check 目标 | 源码树无 tests/ 目录、无 check 接线 | 不在 build() 中调用 make check，按 no_tests 口径在 MANIFEST.yml 审计并在 test_package 复发标记 |

## 源码修改

无补丁。`patches_applied` 为空，`conandata.yml` 无 patches 段。

## 依赖版本

无 Conan 依赖。构建仅需系统 clang/make，NASM 仅在 `--enable-ibmpc-rom/--enable-macplus-rom` 时需要，本配方保持默认关闭。

## 验证结果

待 HMBS 真机预检（conan create）：

```bash
conan create archives/p/pce/0.2.2 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

预期产物：`bin/pce-ibmpc`、`bin/pce-macplus`、`bin/pce-rc759`、`bin/pce-sim405`、`bin/pce-sim6502`、`bin/pce-simarm`、`bin/pce-sims32`。
消费者测试对 7 个二进制各做版本断言（ibmpc/macplus/rc759 用 `-V`，sim 系列回退 `--version`）与 `--help` 两项断言，共 14 用例。

## 交付物

| 文件 | 说明 |
|------|------|
| archives/p/pce/0.2.2/conanfile.py | Autotools 配方（application） |
| archives/p/pce/0.2.2/conandata.yml | 双 URL + sha256 |
| archives/p/pce/0.2.2/test_package/ | 7 二进制版本/帮助冒烟测试 |
| archives/p/pce/commands.json | tool 声明 |
| archives/p/pce/manifest.yaml | 软件级索引 |
| archives/p/pce/README.md | 软件说明 |

## 注意事项

- 本机为 Windows，无 OHOS 工具链；切勿在本机运行 conan，真机验证由 HMBS 后台执行。
- 上游 ROM/磁盘镜像为二进制附件，不随配方发布；仿真器启动仍需用户自备 ROM/镜像。
- SDL/X 支持被编译关闭，图形终端仅保留 null/stdio，适合 CI 冒烟与版本验证，不做交互仿真。
