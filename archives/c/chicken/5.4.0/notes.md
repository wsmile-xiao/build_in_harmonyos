# chicken 5.4.0 适配笔记（HarmonyOS PC aarch64）

## 编译环境
- 构建系统: custom (Makefile.linux, 无 configure 脚本)
- 编译日期: 2026-08-03
- 编译器: clang 15.0.4 (OHOS SDK 26.0.0.18)
- 平台: HarmonyOS PC aarch64 (os=OHOS, arch=armv8)
- 状态: built

## 编译步骤

```bash
# 1. 源码下载（官方源，sha256 校验）
#    https://code.call-cc.org/releases/5.4.0/chicken-5.4.0.tar.gz
#    sha256: 3c5d4aa61c1167bf6d9bf9eaf891da7630ba9f5f3c15bf09515a7039bfcdec5f

# 2. 编译（无 configure，直接 make）
make PLATFORM=linux PREFIX=<prefix> C_COMPILER=clang -j1

# 3. 安装（需 install wrapper, 见问题1）
make install PLATFORM=linux PREFIX=<prefix> C_COMPILER=clang INSTALL_PROGRAM=<install-wrapper> -j1

# 4. 测试
make PLATFORM=linux PREFIX=<prefix> C_COMPILER=clang check
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `install: inaccessible or not found` (E098/E174) | HarmonyOS toybox 不包含 GNU coreutils 的 install 命令 | 编写 cp+chmod 语义的 install wrapper 脚本，通过 make 参数 INSTALL_PROGRAM 注入 |
| 2 | posix-tests.scm:116 file-permissions 断言失败 (E046) | SELinux/HMDFS 限制 chmod 不生效，期望权限 0666(438) 无法设置 | 记录为平台限制，不阻塞编译 |
| 3 | conan conf API 使用错误 (tools.build:compiler_executables:c) | profile conf 是 dict 类型，不能直接取子键 | 改用 `self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)` 再取 ["c"] (R33) |
| 4 | test_package 导入 (chicken version) 失败 | chicken 5.4.0 中无 `(chicken version)` 模块，chicken-version 在 `(chicken platform)` | 修正 test_hello.scm import (chicken platform) |
| 5 | 下载 SSL 证书验证失败 | 鸿蒙 CA 证书不完整 (E034/E185) | 正式流程：先 `check-env` 安装 CA 证书（自动安装 119 个根证书），再用 HTTPS 下载并校验 tarball SHA256 与官方一致 |

## 源码修改
- 无源码修改，补丁数 0

## 依赖版本
- 无外部依赖（chicken 自包含，仅链接系统库 -lm -ldl）

## 验证结果

```bash
# conan create 真实执行并成功
# test_package 实质调用:
$ csi -version
CHICKEN 5.4.0 (rev 1a1d1495) linux-unix-clang-arm64
$ csc -o test_hello test_hello.scm && ./test_hello
Hello from CHICKEN 5.4.0
fact(10) = 3628800
conan test_package: chicken toolchain OK

# make check: 6377 PASS, 1 FAIL (posix file-permissions, E046)
```

## 结束

- 编译结束时间: 2026-08-03
- 最终状态: built (conan-verify 8 道门禁通过，未 upload)
- 归档关闭: 是
- W4 独立审计: pass (P0=0, P1=0)
