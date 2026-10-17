# dr_libs 0.0-git.dfe8377 OHOS PC 适配笔记

## Upstream

- Repository: https://github.com/mackron/dr_libs
- Fixed commit: `dfe8377631000664666519fdb83da193fd8037f4` (master HEAD, git ls-remote verified)
- License: Unlicense OR MIT-0 (LICENSE, dual-license choice, David Reid)
- Language: C89/C99, zero third-party dependencies
- Headers at this snapshot: dr_wav.h 0.14.6, dr_flac.h 0.13.4, dr_mp3.h 0.7.4

Upstream is master-only as a repository: per-header tags exist
(wav-0.14.6 / flac-0.13.4 / mp3-0.7.4) but there is no whole-repo
version tag. The package version `0.0-git.dfe8377` follows the team's
git-snapshot convention (sokol 0.0-git.2e75443 / smaz 0.0-git.2f62584
precedents): `0.0` because the repository declares no aggregate
version, `git` + 7-hex abbreviated commit hash for reproducibility.

## 形态与查重

- Header-only 三合一聚合包：tarball 根目录三头并列（dr_wav.h /
  dr_flac.h / dr_mp3.h），本包交付全部三头到 include/ 根。
- 同仓已有按单头拆分的兄弟包（他人 done 卡）：dr_wav 0.13.17、
  drwav 0.14.5（dr_wav.h 单头）、dr_flac 0.12.39（dr_flac.h 单头）、
  dr_mp3 0.7.2（dr_mp3.h 单头）。包名 dr_libs 与四者精确名不同
  （精确名查重已过）；本包定位为需要整套 dr_libs 的消费者的一次
  依赖入口（与 dr_mp3 归档 notes 中"tarball 三头归属各自包"的
  单头拆分约定互补，聚合形态不含单独编译产物）。
- 三头互相独立（无交叉 include、无符号冲突）：test_package 在
  同一翻译单元同时激活三个 *_IMPLEMENTATION 宏验证可共存编译。

## Build

Header-only：无构建系统消费（上游 CMakeLists.txt 仅用于 tests/）。
配方直接拷贝三头到 include/ 与 LICENSE 到 licenses/，无 lib/ 产物、
无源码补丁（纯可移植 C，OHOS 无平台分支，无需适配 patch——与
dr_wav 0.13.17 / dr_mp3 0.7.2 归档先例一致）。

sha256 本机双实测：ghfast.top 镜像与官方 github.com 两 URL 的
master.tar.gz 内容逐字节一致
（937bf04ab9fb57f0420179d47ebc6515fcc28581f37b5c306ce57f379b74716a）。

## Upstream tests

上游 tests/ 为 CMake 组织的 testvectors 驱动测试（tests/wav|flac|mp3
+ tests/testvectors 数据集，且 testvectors 依赖 git submodule，官方
tarball 不含数据文件，仅 .gitkeep——dr_mp3 0.7.2 归档已记录同一边界）。
本件不在 conan build() 中编译上游测试套件（数据集不可得），功能验证由
test_package 消费者测试真实覆盖：

- test_dr_libs.c 在同一翻译单元编译三个头的实现段（三头共存编译
  验证 + 三头版本号断言）；
- dr_wav 内存写读往返断言（drwav_init_memory_write 写 8kHz/1ch/
  16-bit/440 帧 ramp → drwav_init_memory 读回），纯内存操作、无
  文件系统依赖；
- dr_flac/dr_mp3 以版本号字符串断言覆盖（无测试向量数据集时的
  最大化真实验证边界，与 dr_mp3 0.7.2 归档先例策略一致）。

## 依赖关系

- 编译/运行依赖：无（零依赖库）
- 工具链：OHOS clang（消费者侧编译实现段）
