# pixd 1.0.0 适配笔记

## 编译环境
- 构建系统: makefile（上游纯 Makefile，无 configure 脚本；init 默认误判 autotools 已更正）
- 编译日期: 2026-09-03
- 编译器: clang（aarch64-unknown-linux-ohos, LLVM 15.0.4）/ llvm-ar / llvm-ranlib
- 状态: built

## 编译步骤

pixd 1.0.0 是单文件 C CLI 工具（pixd.c，约 7KB），无外部三方库依赖，仅用标准 C 库
（ctype.h / err.h / inttypes.h / stdint.h / stdio.h / stdlib.h / string.h / unistd.h）。

```bash
# 在 OHOS aarch64 本机直接以 clang 编译（本机 target = aarch64-unknown-linux-ohos）
make          # clang -fPIC -O2 -Wall -std=c11 -o pixd pixd.c ; gzip -k pixd.1

# DESTDIR 隔离安装（本机 PATH 缺 coreutils install，用 busybox shim 验证，见注意事项）
PATH=<shim-with-install>:$PATH make install DESTDIR=$TEST_PREFIX

# 运行验证（安全弹窗检查通过，二进制可直接执行）
printf 'OpenHarmony' | <DESTDIR>/usr/local/bin/pixd   # 输出 24-bit SGR 色块
pixd <file>                                            # 文件模式
```

产物：`bin/pixd`（arm64 OHOS ELF 可执行文件）+ `share/man/man1/pixd.1.gz`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 本机 PATH 无 coreutils `install` 命令，`make install` 报 "install: No such file" | OHOS 环境裁剪了 coreutils install | 仅本地验证用 busybox install 做 shim；conan 配方 package() 直接 copy 产物，不依赖 `install` |
| 2 | init-build 将 pixd 构建系统误判为 autotools | 无 manifest 时 _guess_build_system 默认返回 autotools | 更正 version manifest `build.build_system: makefile`（上游仅 Makefile） |

## 源码修改

- `0001-pixd.c.patch`：在 main() 增加 `--version`/`--help` 处理。上游 pixd 两者皆无，
  getopt 收到未知选项返回 1，导致 Conan L2 冒烟门禁（依次试 --version/--help）失败；
  补丁为最小功能性增强（非平台专用、无平台宏），与 aa3d 配方同款做法。
  补丁由 `refresh-patch --auto` 从 .orig 对比 .work 生成。

## 依赖版本

- 无外部 requires / tool_requires（仅 libc + clang 工具链，OHOS 系统自带）

## 验证结果

```bash
# 冒烟：stdin 输入 → 输出颜色块（SGR 序列）exit 0
printf 'OpenHarmony' | pixd >/dev/null; echo $?    # 0
# 文件模式
pixd LICENSE >/dev/null; echo $?                    # 0
# make check：上游无 check 目标（已如实记录，非跳过）
make check    # make: *** No rule to make target 'check'
```

## 注意事项

- pixd 是 CLI 工具（R38），需在软件级目录创建 commands.json。
- 上游无测试套件；test_package 将实际执行 pixd 二进制并对样例输入断言输出（R34）。
- 版本号 1.0.0 为上游原版；若后续修复适配需递增后缀 1.0.0.1（R37）。
- conanfile.py 中编译器须从 tools.build:compiler_executables 获取（R33），不得裸用 ${CC}。
---

**编译结束**: 2026-09-03 23:51
**最终状态**: built
