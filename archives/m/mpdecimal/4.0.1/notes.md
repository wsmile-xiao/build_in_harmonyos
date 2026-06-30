# mpdecimal 4.0.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-03
- 编译器: clang 15.0.4 / clang++ 15.0.4 (OHOS SDK)
- 状态: published

- 平台: aarch64-unknown-linux-ohos (HarmonyOS Kernel 1.12.0)

## 编译步骤

1. init-build --url=https://www.bytereef.org/software/mpdecimal/releases/mpdecimal-4.0.1.tar.gz
2. 使用 patch-autotools-ohos.pl 打补丁 config.guess/config.sub (识别 HarmonyOS
3. configure --prefix=$DEFAULT_PREFIX CC=$HOME/tmp/wrapper-bin/clang CXX=$HOME/tmp/wrapper-bin/clang++ LDFLAGS="-fuse-ld=/data/service/hnp/binutils.org/binutils_2.45/bin/ld"
4. make -j2 CC=$HOME/tmp/wrapper-bin/clang CXX=$HOME/tmp/wrapper-bin/clang++
5. make install DESTDIR=$TEST_PREFIX
6. make check（手动下载 deectest.zip 并签名测试二进制）
6. ohc-run.py package mpdecimal 4.0.1
7. make install（本地安装到 $DEFAULT_PREFIX）

8. ohc-run.py verify-build mpdecimal 4.0.1

9. ohc-run.py finish mpdecimal 4.0.1 published

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | E007: GNU config.guess 不含 HarmonyOS 检测 | 使用 patch-autotools-ohos.pl 打补丁 config.guess/config.sub |
| 2 | configure conftest Permission denied | 需要运行 ELF 签名才能执行 conftest | 创建 CC/CXX wrapper clang 脚本，自动签名编译产物 |
| 3 | lld 不可运行（缺 libxml2.so.16） | lld 需要 libxml2.so.16 但 harmonybrew 中有但 但动态链接器无法找到 | 使用 GNU ld 2.45 替代 lld (-fuse-ld=path) |
| 4 | make check Permission denied | 测试二进制未签名 | 手动签名 runtest/runtest_shared |
| 5 | wget 无法下载测试数据 | wget -nv 选项不兼容 | 手动 curl +kfsSL 下载 deectest.zip |

| 6 | verify-build G4 失败 | 纯库包无可执行文件+manifest缺 build_system | 添加 build_system 字段+纯库包特跳过二进制检查 |

| 7 | make check C++ 测试找不到 testdata | C++ 测试目录缺少 testdata | 创建符号链接到 C 测试的 testdata |

## 源码修改
1. config.guess: 添加 __OHOS__ LIBC 检测和 HarmonyOS 系统识别
2. config.sub: 添加 ohos-linux triplet 和 OS 列表

补丁文件:
- 0001-config.guess.patch
- 0002-config.sub.patch

## 依赖版本
- 无额外依赖（纯 C/C++ 库， 仅需 -lm 数学库）

## 验证结果
- pkg-config --modversion libmpdec: 4.0.1 ✅
- pkg-config --modversion libmpdec++: 4.0.1 ✅
- C 库测试 (runtest official.decTest): 131/131 PASS
- C 库测试 (runtest additional.decTest): 15/15 PASS
- C++ 库测试 (runtest official.topTest): 131/131 PASS
- 共享库测试 (runtest_shared official.decTest): 131/131 PASS

## 交付物
| 文件 | 大小 | 说明 |
|------|------|------|
| mpdecimal-4.0.1-ohos-aarch64.tar.gz | 1447KB | 预编译包 |

| libmpdec.so.4.0.1 | 207KB | C 共享库 |
| libmpdec++.so.4.0.1 | 88KB | C++ 共享库 |
| libmpdec.a | 240KB | C 静态库 |
| libmpdec++.a | 97KB | C++ 静态库 |

## 注意事项
1. mpdecimal 是纯库包（无命令行工具）， 不在 bin/ 下有可执行文件
2. 编译时必须使用 CC/CXX wrapper clang 蔻动来自动签名 ELF 二进制
3. 编译时必须添加 LDFLAGS=-fuse-ld=GNU ld 代替 lld（lld 因 libxml2.so.16 缺失无法运行）
4. make check 时需要手动签名测试二进制才能执行
---

**编译结束**: 2026-06-03 17:54
**最终状态**: published
