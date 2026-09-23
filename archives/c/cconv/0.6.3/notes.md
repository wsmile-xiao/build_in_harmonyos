# cconv 0.6.3 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-05
- 编译器: clang 15.0.4 / clang++ (HarmonyOS OHOS SDK aarch64-linux-ohos)
- 状态: built

## 编译步骤

```bash
# 源码: 官方标签 v0.6.3 (commit 23d41d5a)
#   https://github.com/xiaoyjy/cconv/archive/refs/tags/v0.6.3.tar.gz
#   sha256: 82f46a94829f5a8157d6f686e302ff5710108931973e133d6e19593061b81d84
# 上游 tarball 未含 configure 脚本（需 autogen）：
libtoolize --force
aclocal-1.16 -I m4        # 环境默认 aclocal 指向损坏的 automake-1.17，改用 1.16
autoheader
autoconf -f -i
automake-1.16 --add-missing --force
# configure 缺 config.sub/install-sh/missing（automake 1.16 share 目录补齐）
./configure --prefix=$DEFAULT_PREFIX
make -j1
make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 cannot guess build type | 上游 config.guess 为 2005 旧版，不识别 HarmonyOS | 换用 automake-1.16 的 config.guess 并用 scripts/patch-autotools-ohos.pl 打补丁（E007），输出三元组 aarch64-unknown-linux-ohos |
| 2 | config.status 报 can't create ./confXXXXXX/subs1.awk: Permission denied | HMDFS 上 umask 077 创建的临时目录对当前进程不可写（E011，UID 映射 + setgid） | configure 中两处 `umask 077 && mktemp` 改为 `umask 022`（E011 rec_approach） |
| 3 | 链接错误 undefined symbol: rindex | OHOS libc 无 BSD 遗留函数 rindex | main.c 改用标准函数 strrchr（<string.h> 已包含） |
| 4 | -f GBK/-t BIG5 报 Not support character code set | cconv 的 GBK/BIG5/GB18030 路径依赖系统 iconv；OHOS 系统 iconv (toybox 0.8.12) 不支持这些编码 | 平台限制：GBK/BIG5 互转在 OHOS 不可用；核心简繁转换（内置 zh_map 表，UTF8-CN↔UTF8-TW/UTF8-HK）完全正常，不阻塞 |

## 源码修改

| 文件 | 修改 |
|------|------|
| main.c | `rindex(s_program, '/')` → `strrchr(s_program, '/')`（OHOS libc 无 rindex） |

（config.guess/config.sub 的 HarmonyOS 补丁由配方构建时注入，不落源码。）

## 依赖版本

- 无第三方依赖（零依赖，自含编码转换表）

## 验证结果

```bash
# 上游语料全量转换（R51）
./cconv -f UTF8-CN -t UTF8-TW < test_s2t   # 45 行简体 → 繁体，rc=0，输出正确
./cconv -f UTF8-TW -t UTF8-CN < test_t2s   # 44 行繁体 → 简体，rc=0，输出正确
# 消费者 API 测试（R34 实质测试，test_package/test.c）
#   cconv_open(UTF8-HANT, UTF8-HANS) + cconv() + cconv_close
#   "头发剪了，后天才到" → "頭髮剪了，後天才到" PASS
# 边界
printf '' | ./cconv -f UTF8-CN -t UTF8-TW  # rc=0
```

## 交付物

| 文件 | 说明 |
|------|------|
| libcconv.so.0.0.0 / libcconv.a | 共享/静态库 |
| cconv | 命令行工具（简繁转换，R38 commands.json 已声明） |
| cconv.h / unicode.h | 头文件 |

## 注意事项

- GBK/BIG5/GB18030 转换在 OHOS 不可用（系统 iconv=toybox 不支持），依赖 iconv 的路径返回 "Not support character code set"；不影响库的主要用途（简体/繁体 UTF8 转换）。
- 上游 tarball 无 configure 脚本，需 autogen 生成；本机环境 automake-1.17 perl 模块损坏，须用 automake-1.16/aclocal-1.16。
---

**编译结束**: 2026-09-05 20:36
**最终状态**: built
