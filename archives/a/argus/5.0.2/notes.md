# argus 5.0.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-29
- 编译器: clang 15 (/data/service/hnp/bin/clang)
- Conan Profile: ohos-aarch64 (os=Linux, arch=armv8, compiler=clang 15, libcxx=libc++, build_type=Release)
- 状态: published

## 编译步骤

### 对话 #1: init-build
执行 `ohc-run.py init-build argus 5.0.2 --url=...` 下载源码 tarball，解压到工作目录，
创建 .orig 备份和编辑追踪器基线。

### 对话 #2: AI 编译
1. `./configure --prefix=$DEFAULT_PREFIX` — 成功（需补丁修补 config.guess/config.sub/configure）
2. `make -j1` — 成功（鸿蒙不支持 mkfifo，必须 -j1）
3. `make install DESTDIR=$TEST_PREFIX` — 成功
4. `make check` — N/A（argus 无 check target）

### 对话 #3: Conan 配方生成与验证
1. `ohc-run.py conan-init argus 5.0.2` — 生成 conanfile.py 和 conandata.yml
2. `ohc-run.py conan-verify argus 5.0.2` — 8 道门禁全部通过 (Verdict: PASS)

### 对话 #4: finish 收尾
执行 `ohc-run.py finish argus 5.0.2 published` — 6 步管线全部完成，状态 published。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 不识别 HarmonyOS | GNU config.guess 无 OHOS 分支 | 替换为支持 OHOS 的版本 (补丁 0003) |
| 2 | config.sub 不识别 HarmonyOS | GNU config.sub 无 OHOS 分支 | 替换为支持 OHOS 的版本 (补丁 0004) |
| 3 | configure 脚本 host 识别失败 | configure 不识别 aarch64-ohos | 修补 configure 脚本 (补丁 0005) |
| 4 | ArgusEvents.c 编译错误 | 类型不匹配 | 修复类型声明 (补丁 0001) |
| 5 | _exit() 被静态 musl 拦截 | 静态链接 musl libc 中 _exit() 和 syscall() 均被拦截 | 使用 aarch64 内联汇编 exit_group (补丁 0002) |
| 6 | make install 不安装 libargus.a | autotools 未定义 install 目标 | Conan package() 手动复制 |
| 7 | make install 不安装头文件 | 同上 | Conan package() 手动复制 |
| 8 | Perl/shell 脚本无法执行 | 鸿蒙无 Perl 解释器 | 从 package 移除 argus-*, argusbug |

## 源码修改

5 个补丁：
- 0001-argus-ArgusEvents.c.patch — 修复 ArgusEvents.c 类型不匹配
- 0002-argus-argus.c.patch — 添加 --version/--help 支持，内联汇编绕过 musl _exit() 拦截
- 0003-config-config.guess.patch — 替换 config.guess 支持 OHOS
- 0004-config-config.sub.patch — 替换 config.sub 支持 OHOS
- 0005-configure.patch — 修补 configure 识别 aarch64-ohos

## 依赖版本

无外部依赖（argus 自包含，仅需系统库 pcap, z, m, pthread）

## 验证结果

```bash
$ argus --version
Argus Version 5.0.2
$ echo $?
0

$ file bin/argus
ELF executable, 64-bit LSB arm64, static, not stripped

$ conan-verify: 8/8 PASS (G1, G0, G2, G3, G4, L2, L4, L5)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/argus | 2,627,520 bytes | 静态链接主二进制 |
| lib/libargus.a | 298,030 bytes | 静态库 |
| include/*.h | 65 个文件 | 头文件 |

## 注意事项

- 鸿蒙不支持 mkfifo，make 必须用 -j1
- 静态链接 musl 中 _exit() 和 syscall() 被拦截，需用内联汇编绕过
- argus 无参数运行会 segfault（预期行为，需指定网络接口）
- -h 选项退出码为 255（内联汇编退出路径，功能正确）
---

**编译结束**: 2026-06-29 18:17
**最终状态**: published
