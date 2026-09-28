# libx86emu 3.7 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile，无 configure）
- 编译日期: 2026-09-28
- 编译器: clang 15.0.4（aarch64-linux-ohos，ohos-aarch64 profile）
- 状态: built

## 编译步骤

1. `init-build libx86emu 3.7 --url=https://github.com/wfeldt/libx86emu/archive/refs/tags/3.7.tar.gz`
   （3.7 tag commit ce81129c57fdfbf690bebc210a8db97d926cc5e7，官方 tag 已核验；
   sha256=03754aede79530baa0e862e1aad5527e9c1bd3371736b1ab5a2bc769e4a3d680）
2. `echo 3.7 > VERSION`（tarball 缺 VERSION，上游由 git2log 生成）
3. `make shared CC=clang -j1` → libx86emu.so.3.7（含 soname 软链）
4. staging 安装：`$TEST_PREFIX/usr/lib/libx86emu.so.3.7` + `include/x86emu.h`
5. 上游测试：`perl prepare_test *.tst` + `./x86test *.init`（60 例）
6. `conan-init` → 手写配方（纯 Makefile 直建）+ `conan-verify`（G0-G4/L2/L4/L5 PASS）
7. `finish`（W2 结构 + R36 依赖 + W3 本地 CI，.ci-result.json exit_code=0）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | tarball 无 VERSION，.so 命名错乱 | 上游 git2log 从 git 历史生成 VERSION，发布 tarball 不含 | build() 构建前 `echo 3.7 > VERSION` |
| 2 | `./git2log: No such file or directory`（文件存在） | 随包分发的 git2log 是 x86_64 预编译 ELF，aarch64 缺解释器 | build() `mv git2log git2log.upstream`，Makefile -x 探测回退 true |
| 3 | prepare_test `mktemp /tmp/...` 失败（/tmp 只读，E002） | 测试 harness 硬编码 /tmp | 补丁等价替换 `$ENV{TMPDIR} \|\| "/tmp"` |
| 4 | `make install` 报 `install: No such file or directory` | 本机/CI 缺 coreutils install（E108 同族） | conan package() 用 copy + ln -s 手工落位 |
| 5 | conan-init 按 autotools 模板生成无效配方 | 纯 Makefile 工程被误判构建系统 | 手写配方：build() 直接 `make shared CC=clang`，不套 autotools |

## 源码修改

- `patches/0001-test-prepare_test.patch`：test/prepare_test 的 mktemp 模板改为
  `$ENV{TMPDIR} || "/tmp"`（本地 /tmp 只读 + CI /tmp 可写两态兼容，无平台宏）。

## 依赖版本

- 上游运行时依赖：无（纯 C 库，仅 libc）
- 上游测试工具：nasm/2.16.03（ohpcd 制品仓，仅测试期使用，非配方依赖）

## 验证结果

```bash
# 上游测试（R51）：60 例 .tst，42/42 有 .done 期望输出用例全部 ok，0 失败，
# 18 例上游未提供 .done 属 unchecked
make -C test CC=clang test   # 42 ok / 0 F / 18 unchecked
# conan create（ohos-aarch64）G2 通过；test_package 功能测试 1/1：
#   mov ax,0x1234; hlt -> R_AX=0x1234 PASS
conan create archives/l/libx86emu/3.7 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# W3 本地 CI：build_and_test.sh L0-L5 全 pass，100% (1/1)
```

## 交付物

- 库包（libx86emu.so.3.7 + x86emu.h + LICENSE）经 Conan 配方随 PR 交付，无独立打包产物。

## 注意事项

- 上游无 release，版本标识以 tag `3.7`（ce81129c57fdfbf690bebc210a8db97d926cc5e7）为准。
- 本地 /tmp 只读与缺失 install 命令为本机环境差异；配方已做两态兼容（$TMPDIR || /tmp、
  手工打包），CI 无需额外依赖。
