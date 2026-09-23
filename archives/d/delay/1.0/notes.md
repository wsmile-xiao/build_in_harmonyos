# delay 1.0 适配笔记

## 编译环境
- 构建系统: make（普通 Makefile，非 autotools）
- 编译日期: 2026-09-10
- 编译器: clang（CI ohos-aarch64 profile）/ gcc（本地 Linux 验证）
- 状态: built（本地验证通过，待远程 CI）

## 上游信息
- 上游项目: delay — a constant delay generator（Romain Vimont）
- 上游仓库: https://github.com/rom1v/delay
- 版本说明: 上游无 release/tag（仅 master 分支）；Debian 将同一仓库打包为 delay 1.0
  （https://sources.debian.org/src/delay/，Homepage 即本仓库）。积分赛任务版本字段为 "1"，
  但 Conan 版本正则 `^[a-z0-9_][a-z0-9_+.-]{1,100}$` 要求版本至少 2 字符，单字符 "1" 在
  conan export 时报 Invalid package version，故包版本采用合法的 "1.0"，任务分支对应
  feat/delay-1.0（同仓库 disktype 9→9.0 先例，!2224 合并 feat/disktype-9.0）。
  源码采用固定 commit 0a430a05d1be6ef9153c0817ed7084af4f1e6ffa（2019-05-31，PR #9 合并后快照）
- 源码 URL: https://github.com/rom1v/delay/archive/0a430a05d1be6ef9153c0817ed7084af4f1e6ffa.tar.gz
  （用 github archive 形式、以 .tar.gz 结尾；不用 codeload /tar.gz/<sha>，后者无后缀会被 Conan 当 zip 解压报 BadZipFile；两者下载字节完全一致）
- SHA256: 20f06e6adc216e670756ad5ab6758c0165f2ab9a044968e1c82d0a12cc9a45a4
- 许可证: MIT（仓库 LICENSE；注：Debian copyright 曾记 GPL-3，以仓库实际 LICENSE 为准）
- 语言: C（100% C；main.c/dtbuf.c/time_ms.c + dtbuf.h/time_ms.h）

## 编译步骤

```bash
make -j1 CC=<clang>     # 上游默认目标 release 构建 ./delay
```

产物（1 个命令行工具，安装到 bin/）:
- delay — 在 stdin 与 stdout 之间引入恒定延时的管道工具：
  `command_A | delay 5s | command_B`；支持 -b 缓冲区大小（k/m/g）
  与延时单位（s/m/h），数据经环形缓冲（dtbuf）按时间戳写出。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 无源码层问题 | 上游代码为纯 C 标准库 + POSIX（poll/gettimeofday/read/write），OHOS libc 均提供，无平台特定代码 | 无需 patch |
| 2 | CI L0n(R40)：feat/delay-1 不包含 delay-1.0 | 包版本 1.0 与任务默认分支后缀 delay-1 不一致 | 任务分支改为与包版本一致的 feat/delay-1.0（R40 要求分支以 包名-版本号 结尾） |
| 3 | conan export 报 `Invalid package version '1'` | Conan 版本正则要求至少 2 字符，单字符 "1" 非法（refs.py validate_ref） | 包版本采用 "1.0"（对齐 Debian 上游版本，同 disktype 9.0 先例），不使用单字符 "1" |
| 4 | conan source() 报 `BadZipFile: File is not a zip file` | codeload URL `codeload.github.com/<repo>/tar.gz/<sha>` 以哈希结尾、无 .tar.gz 后缀，Conan get() 无法识别压缩格式，默认按 zip 解压 | 改用 `github.com/<org>/<repo>/archive/<sha>.tar.gz`（以 .tar.gz 结尾，Conan 正确走 untargz；两者下载字节一致、sha256 不变），同 abootimg 等无 tag 库先例 |

## 依赖版本

无外部依赖（仅 libc + POSIX 头文件）。

## 上游测试清点

- 上游 Makefile 仅有 `release`/`install`/`clean`/`fmt` 目标，**无 check/test 目标**，
  仓库无 tests 目录
- 上游测试用例数: **0**
- 适配后补全: test_package 冒烟测试 4 项（数据透传 / 空输入 / 时间单位后缀 / 缓冲区参数），
  断言数 4（按独立检查项计数，见 MANIFEST.yml）

## 验证结果

```bash
# 本地 Linux 验证（gcc）
make -j1 CC=gcc
printf 'hello delay' | ./delay 100        # 约 100ms 后输出 'hello delay', exit 0
printf '' | ./delay 100                   # 空输入直接退出, exit 0
printf 'x' | ./delay 1s                   # 后缀解析: 1s=1000ms, 输出 'x'
printf 'x' | ./delay -b 4k 200            # 缓冲区参数解析, 输出 'x'

# conan create（本地 Linux profile 验证配方逻辑；远程 CI 用 ohos-aarch64 交叉编译）
conan create . -pr:h=<profile> -pr:b=<profile>   # 构建 + test_package 冒烟测试通过
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（make + CC 注入） |
| conandata.yml | 源码 URL（固定 commit）+ SHA256 |
| test_package/ | 4 项二进制冒烟测试 |
| commands.json（软件级） | delay 命令行工具声明（R38） |

## 注意事项

- 远程 HarmonyOS CI 使用 ohos-aarch64 profile（clang + aarch64-linux-ohos triplet），为本包最终门禁
- delay 无参数运行时默认 delay=5000ms 并阻塞等待 stdin（stdout 无数据时不退出），
  测试必须通过管道喂入数据触发 EOF 才能正常退出
- 上游 `make install` 写死 $(DESTDIR)/usr/bin，配方 package() 直接 copy 构建产物到 bin/（同 desproxy）
- 未 strip 二进制（上游无 strip 环节；OHOS MAC 对 stripped 二进制敏感，保持原样最稳妥）
---

**编译结束**: 2026-09-10
**最终状态**: built
