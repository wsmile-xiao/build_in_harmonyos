# bwt 2.1.2 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-08-24
- 编译器: clang/clang++ (llvm 15.0.4)
- 状态: built

## 编译步骤

1. 下载官方源码: bwt (MichaelDipperstein/bwt) + optlist (MichaelDipperstein/optlist) 两个 GitHub 仓库
2. 编译 optlist: 在 optlist/ 目录 `make` 生成 liboptlist.a
3. 编译 bwt 库: `make` 通过 Makefile 生成 libbwt.a + sample
4. 测试: encode/decode roundtrip 通过（含/不含 MTF）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 原始站点不可用 | waterlan.home.xs4all.nl 已下线；bwt.org 域名被占用 | 使用 GitHub 上 MichaelDipperstein/bwt 仓库作为官方源码 |
| 2 | conan 进程无法 exec clang-15 | conan 脚本 shebang 指向用户 python（SELinux adhoc_bin 域），该域无法执行大体积 hnp_file 二进制 | conan 改用 HNP python（/data/service/hnp/bin/python3）运行，进入 hishell_hap 域后 clang-15 正常执行 |
| 3 | /tmp 只读 | 鸿蒙系统限制 | test_package 使用 TMPDIR/HOME 环境变量路径 |
| 4 | setUp.sh 的 dirname 不可用 | W3 模拟运行的 PATH 缺少 /usr/bin | 运行 finish 时 PATH 前置 /usr/bin |
| 5 | L0k 要求 commands.json | R38: 构建产物含可执行文件 sample | 添加 archives/b/bwt/commands.json |
| 6 | optlist is git submodule | GitHub tarball 不含 submodule 内容 | conandata.yml 采用双 source（bwt + optlist），source() 分别下载 |

## 验证结果

```bash
# BWT encode/decode roundtrip (without MTF)
$ ./sample -c -i input.txt -o encoded.bin
$ ./sample -d -i encoded.bin -o decoded.txt
$ diff input.txt decoded.txt  # 一致

# BWT encode/decode roundtrip (with MTF)
$ ./sample -c -m -i input.txt -o encoded_mtf.bin
$ ./sample -d -m -i encoded_mtf.bin -o decoded_mtf.txt
$ diff input.txt decoded_mtf.txt  # 一致
```

## 交付物

| 文件 | 说明 |
|------|------|
| libbwt.a | BWT 变换静态库 |
| bwxform.h | BWT 库头文件 |
| sample | BWT 命令行演示工具（encode/decode，含/不含 MTF） |

## 版本与源码说明

- bwt/optlist 上游均无 release tag（GitHub tags/releases 为空）。bwt master 最新 commit `2449456c`（2026-04-13 "Make optlist a submodule"），本配方使用 `refs/heads/master.tar.gz` 并固定 sha256，上游变更时校验会响亮失败，不会静默引入内容变化。
- 版本号 2.1.2 沿用任务指定版本；上游源码无对应 tag，以 master 分支内容 + sha256 锁定交付。

## 注意事项

- optlist 是 git submodule，需从独立 GitHub 仓库获取（conandata.yml 双 source）
- conan 需使用 HNP python 运行，确保在 hishell_hap SELinux 域（否则无法 exec clang-15）
## 结束

bwt 2.1.2 适配完成（最终状态：built）。conan-verify 全门禁通过，W3 本地 CI 模拟通过，本地产物与测试完整。
