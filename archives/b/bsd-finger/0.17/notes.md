# bsd-finger 0.17 适配笔记

## 编译环境
- 构建系统: autotools（netkit confgen configure + Makefile）
- 编译日期: 2026-09-05
- 编译器: clang/clang++ (LLVM 15.0.4)
- 状态: published

## 编译步骤

1. 上游确认：Distrotech/bsd-finger GitHub 仓库，version.h 声明 `$NetKit: bsd-finger-0.17 $`，即 netkit 官方 bsd-finger-0.17。master 为滚动分支，配方固定 commit `dae7f2836b01d7812a32f9dc189c0862f60edff7`（2013-04-02）保证可复现。
2. configure：`./configure --prefix=/usr --with-c-compiler=clang`（netkit confgen 风格，非 GNU autotools，必须显式指定编译器，因环境中无 `cc` 只有 `clang`）
3. make：顶层 Makefile `SUB = finger fingerd`，子目录分别构建 `finger` 客户端与 `fingerd` 服务端
4. 安装：`in.fingerd`（fingerd 服务端的上游安装名）+ man 手册页
5. 测试：上游无自带测试目标，自研 test_package/test.sh 执行 6 项断言（finger 无参数/未知用户/--help/非法选项/-l 长格式/in.fingerd 可执行）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `finger/lprint.c:340 open() 隐式声明、O_RDONLY 未定义` | 上游依赖 C89 隐式声明，clang 严格模式报错 | 补 `#include <fcntl.h>`（补丁 0001） |
| 2 | `finger/util.c：loff_t 未定义、L_SET 未定义、open()/O_RDONLY 未声明` | glibc 特有 `loff_t` 与 BSD `L_SET` 宏，HarmonyOS musl libc 无 | 改 `off_t` + 标准 `SEEK_SET`，补 `#include <fcntl.h>`（补丁 0002） |
| 3 | conan-verify G2 首次失败：`copy() got unexpected keyword 'rename'` | conan 2 的 copy() 不支持 rename 参数 | 改用 copy 后 `os.rename` 改名 |
| 4 | test 阶段 `in.fingerd not executable in PATH` | fingerd 安装在 `sbin/`，test_package conanrun PATH 只有 `bin/` | package_info `bindirs = ["bin", "sbin"]` |
| 5 | W3 本地 CI 报 `timeout: exec conan: Permission denied` | PATH 命中无执行权限的 pip-global/bin/conan | 运行 finish 时 PATH 前置 `/storage/Users/currentUser/usr/local/bin` |

## 源码修改

- `patches/0001-finger-lprint.c.patch`：lprint.c 补 `<fcntl.h>`（portability）
- `patches/0002-finger-util.c.patch`：util.c 补 `<fcntl.h>`；`loff_t`→`off_t`；`L_SET`→`SEEK_SET`（portability）

两个补丁均为 HarmonyOS musl libc 的头文件/类型合规修改，不改变上游行为逻辑。

## 依赖版本

- 无外部软件依赖（纯 libc C 程序，仅使用系统头文件）

## 验证结果

```bash
# conan create 干净构建（conan-verify G1-G4 + L2/L4/L5 全通过）
$ conan create archives/b/bsd-finger/0.17 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# W3 本地 CI 模拟（setup.sh + build_and_test.sh）通过
# test_package 自研断言 6/6 全部通过：
#   finger 无参数 → "No one logged on."（rc=0）
#   finger 未知用户 → "no such user"
#   finger --help / 非法选项 → usage
#   finger -l 未知用户 → "no such user"
#   in.fingerd 可执行存在
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/finger | finger 客户端（查询用户信息） |
| sbin/in.fingerd | fingerd 远程 finger 守护进程 |
| man/man1/finger.1, man/man8/in.fingerd.8 | man 手册页 |

## 注意事项

- 上游 bsd-finger-0.17 为 netkit 经典版本，2013 年最后更新，无新安全修复（README 声明 bsd-finger-0.16 修复 DoS）；无自带测试，已按质量红线补齐 6 项功能断言
- fingerd 为 inetd 型守护进程，本适配提供可执行二进制；鸿蒙侧集成需自行配置 inetd 服务

---

**编译结束**: 2026-09-05 11:28
**最终状态**: published