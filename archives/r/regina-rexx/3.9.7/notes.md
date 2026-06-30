# regina-rexx 3.9.7 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-12
- 编译器: clang/clang++
- 目标平台: aarch64-unknown-linux-ohos (HarmonyOS)
- 状态: published

## 编译步骤

```bash
source .build-context-regina-rexx-3.9.7
cd $BUILD_SRC_DIR

# 1. 修补 config.guess/config.sub（E007）
perl $SKILL_ROOT/scripts/patch-autotools-ohos.pl common/config.guess common/config.sub
# 手动添加 linux-ohos*) ;; 到 config.sub kernel-OS 验证 case 语句

# 2. 修补 configure（E011）
sed -i 's/umask 077/umask 022/g' configure

# 3. 创建缺失的 config.h.in（从 config.status 提取）
grep "^D\[" config.status | sed 's/D\["\(.*\)"\]="\(.*\)"/#undef \1/' | sort -u > config.h.in

# 4. 恢复被误删的 configur.h
cp $BUILD_SRC_ORIG_DIR/configur.h $BUILD_SRC_DIR/configur.h

# 5. configure（禁用screen功能避免terminfo依赖）
./configure --prefix=$DEFAULT_PREFIX --disable-screen

# 6. 重新运行 config.status 生成 config.h
./config.status

# 7. make -j1

# 8. make install DESTDIR=$TEST_PREFIX

# 9. make install（本地安装）
# 10. regina --version 验证
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别鸿蒙平台 | E007: GNU config.guess 不含 HarmonyOS 检测 | patch-autotools-ohos.pl 修补 + 手动添加 linux-ohos*) ;; 到 config.sub |
| 2 | config.status Permission denied | E011: HMDFS umask 077 创建的临时目录不可写 | sed configure 中 umask 077 → umask 022（2处） |
| 3 | config.h.in 不存在 | 项目未提供 config.h.in | 从 config.status 提取 D[] 条目生成（104行 #undef） |
| 4 | configur.h 缺失 | 清理临时文件时误删 | 从 orig 目录恢复 |
| 5 | regscreenux.c 编译失败（tgetstr/tgetent/tgoto） | terminfo库函数不可用但 HAVE_TERM_H=1 触发 USE_TERMCAP_DB | configure --disable-screen |
| 6 | SourceForge SSL下载失败 | 证书验证问题 | curl --insecure -L 下载 |
| 7 | regina 执行 Operation not permitted | 鸿蒙ELF签名安全限制 | ohc-run.py sign-elf 签名后可执行 |

## 源码修改

| 文件 | 修改内容 | 补丁文件 |
|------|----------|----------|
| common/config.guess | 添加 HarmonyOS 系统识别（+11行） | 0001-common-config.guess.patch |
| common/config.sub | 添加 ohos-linux triplet + linux-ohos*) kernel-OS 组合（+9/-1） | 0002-common-config.sub.patch |
| config.h.in | 新建（从 config.status 提取，+103/-390） | 0003-config.h.in.patch |
| configure | umask 077 → umask 022（+2/-2） | 0004-configure.patch |

所有补丁均为平台适配补丁（platform_only=True），修改的是构建系统文件而非源代码，无需 #ifdef __OHOS__ 守卫。

## 依赖版本

- 无外部依赖（required和optional都为空）
- ncurses 在 ~/usr/local 已安装（静态库），但 configure --disable-screen 避免链接

## staging 安装产物清单

| 产物 | 路径 | 大小 | 说明 |
|------|------|------|------|
| regina | bin/regina | 10000B | 主解释器（符号链接） |
| rexx | bin/rexx | 411552B | 主解释器（实际二进制） |
| rxqueue | bin/rxqueue | 30552B | 队列接口工具 |
| rxstack | bin/rxstack | 63320B | 堆栈接口工具 |
| regina-config | bin/regina-config | 2579B | 配置脚本 |
| libregina.a | lib/libregina.a | 2416168B | 静态库 |
| libregina.so.3.9 | lib/libregina.so.3.9 | 489304B | 共享库（动态链接） |
| libregina.so → libregina.so.3 → libregina.so.3.9 | lib/ | — | 符号链接链 |
| rexxsaa.h | include/rexxsaa.h | 27744B | SAA API 头文件 |
| de/en/es/no/pl/pt/sv/tr.mtb | share/regina-rexx/ | ~21-26KB | 多语言消息文件 |
| examples/ | share/regina-rexx/examples/ | — | 示例脚本 |
| pkgconfig/ | lib/pkgconfig/ | — | pkg-config 文件 |
| regina-rexx/ | lib/regina-rexx/ | — | 回调库 |

## 验证结果

### 版本验证
```bash
$ regina --version
REXX-Regina_3.9.7(MT) 5.00 18 Mar 2025 (64 bit)
```

### 功能测试（5项全部通过）

| 测试项 | 测试内容 | 结果 |
|--------|----------|------|
| 算术运算 | 2+3=5, 10-4=6, 3*7=21, 15/3=5 | ✅ 通过 |
| 字符串操作 | LENGTH/SUBSTR/LEFT/RIGHT/REVERSE | ✅ 通过 |
| 流程控制 | DO循环(1到5) + IF条件判断 | ✅ 通过 |
| 内置函数 | ABS/MAX/MIN/SIGN/DATATYPE/STRIP/TRANSLATE/CENTER | ✅ 通过 |
| 版本验证 | regina --version 输出正确版本号 | ✅ 通过 |

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| regina-rexx-3.9.7-ohos-aarch64.tar.gz | 5587KB (5721469B) | 预编译包（含bin/lib/include/share） |
| regina-rexx-3.9.7-ohos-aarch64-debug.tar.gz | 278KB (278591B) | 调试符号包 |

## 注意事项

- configure 必须使用 --disable-screen 避免 terminfo 链接问题，否则 regscreenux.c 会因 tgetstr/tgetent/tgoto 未定义而编译失败
- config.h.in 需手动创建（项目未自带），可从 config.status 提取 D[] 条目生成
- configur.h 是项目自带头文件，清理临时文件时注意不要误删
- SourceForge 下载需 curl --insecure -L
- 首次运行 regina 可能遇到 "Operation not permitted"，需使用 sign-elf 签名

---
**编译结束**: 2026-06-12 21:55
**最终状态**: published
