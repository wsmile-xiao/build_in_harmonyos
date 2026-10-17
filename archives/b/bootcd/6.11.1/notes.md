# bootcd 6.11.1 适配笔记

## 编译环境
- 构建系统: custom（纯 Shell 脚本工具集，无编译）
- 编译日期: 2026-09-06
- 编译器: 无（纯脚本）
- 状态: built

## 编译步骤

```bash
# conan create 内部（conanfile.py）：
# 1. source(): Git.clone（salsa.debian.org/debian/bootcd.git，--depth 1 +
#    checkout 6b494344 = 6.11.1）——git 独立 ssl，CI Python 无 SSL 模块时可下载
# 2. build(): apply_conandata_patches（无补丁，G1 完整性要求调用）——空操作
# 3. package(): 复制主脚本到 bin/（bootcd/bootcdflopcp/bootcdinitramfshook/
#    bootcdmodprobe/bootcdoverlayfs/bootcdproberoot/bootcdrst/runbootcdmodprobe/
#    runbootcdproberoot/src2conf）+ *.lib 到 share/bootcd/ + 文档
# 4. test_package: test_bootcd.py 断言主脚本存在 + /system/bin/sh -n 语法可解析
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Debian pool/sources.debian.org/snapshot 的 tarball 下载 404 | bootcd 上游无独立 release tarball，源码在 salsa.debian.org git | 改 Git.clone 下载（master HEAD = 6.11.1，changelog 确认）；git 独立 ssl 也解决 CI Python 无 SSL 的 E372 场景 |
| 2 | G1 FAIL：conandata.yml 缺少 sources 段 | 最初只用 git_url/git_commit 字段，G1 要求 sources 段 | conandata.yml 加 sources 段（url+commit+type=git），git_url/git_commit 保留供 Git.clone 用 |
| 3 | test_package 断言 bootcdbackup 缺失 | 凭工具名臆造脚本清单（bootcdbackup/bootcdmkinitramfs 实际不存在） | 以源码实际可执行脚本为准：bootcd/bootcdflopcp/bootcdinitramfshook/bootcdmodprobe/bootcdoverlayfs/bootcdproberoot/bootcdrst/runbootcdmodprobe/runbootcdproberoot/src2conf |
| 4 | test_package 运行需路径加引号 | 工作目录名含括号 "build_in_harmonyos-main (1)"，/system/bin/sh 解析未加引号的 (1) 报 syntax error | python3 执行 + 路径单引号包裹（参考 boom-completion 同款修复） |

## 源码修改

无外部补丁文件（patches/ 为空）；仅 conanfile.py 的 package() 复制主脚本与
.lib 到惯例目录（bin/ + share/bootcd/）。

## 依赖版本

无 conan 库依赖（纯 Shell 脚本工具集）。运行时依赖系统工具（busybox/
xorriso/genisoimage/cpio 等），在 ohpcd 仅 busybox/1.36.1 有包，其余为
Linux 发行版生态工具、非 conan 库依赖。

## 验证结果

```bash
# conan-verify bootcd 6.11.1 → 全门禁 PASS
# G1 配方完整性 / G0 知识图谱 / G2 conan create / G3 R26 隔离 /
# G4 产物完整性 / L2 smoke / L4 checksec / L5 基线对比 全部 PASS

# test_package R34：bin/ 主脚本存在 + /system/bin/sh -n 语法可解析 +
# share/bootcd/*.lib 已打包（脚本存在性校验；核心功能——复制系统成可启动
# ISO——需完整 Debian 系统环境，OHOS 无，按 rule 1.2 声明平台限制）

# 上游测试实测（rule 4，2026-09-07）：
# 上游 bootcdmk2diskconf.tst1-7 共 7 个测试，逐个 sh 运行实测：
#   0 通过 / 7 失败（0/7）
# 失败原因具体：OHOS 缺 shellia（/usr/share/shellia/ia 不存在），
# bootcdmk2diskconf 工具无法运行致输出为空、与期望 diff 全失败（非跳过；
# 通过率口径 passed/(passed+failed+errors) = 0/7 = 0%）。N=7 与 review
# 实测一致，无少报。
```
