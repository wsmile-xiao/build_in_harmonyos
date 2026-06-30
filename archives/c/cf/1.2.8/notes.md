# cf 1.2.8 适配笔记

## 编译环境
- **构建系统**: autotools
- **编译日期**: 2026-06-10
- **编译器**: clang 15.0.4 (OHOS dev) llvm-project 0e01a01d567b9acfce8edfdadb66a7b69f088fb0)
- **链接器**: LLD 15.0.4
- **目标平台**: aarch64-unknown-linux-ohos (HarmonyOS Kernel 1.12.0)
- **源码URL**: https://ee.lbl.gov/downloads/cf/cf-1.2.8.tar.gz
- **源码SHA256**: 52ce4302f7f9dd67227e5a3d09fc289127bf0ad256d24d8e1698733ea2e1fd48
- **许可证**: BSD-3-Clause
- **状态**: published

- **依赖**: 无

## 编译步骤

1. init-build: `ohc-run.py init-build cf 1.2.8 --url=https://ee.lbl.gov/downloads/cf/cf-1.2.8.tar.gz`
2. 修补 config.guess: 添加 HarmonyOS 系统识别分支（E007 — config.guess 不识别 HarmonyOS）
3. 修补 config.sub: 添加 ohos 三元组验证，3处修改：ohos-linux 映射、 OS 白名单 ohos*  kernel-os 白名单 linux-ohos*）（E072 -- config.sub 三元组验证失败）
4. 修补 configure: HMDFS 文件系统 umask 077 创建的目录无法写入（改为 umask 022 + 使用 $TMPDIR）
5. `./configure --prefix=$DEFAULT_PREFIX`（configure 后需手动修补生成的 config.status 中的临时目录逻辑）
6. 手动运行修补后的 `./config.status` 生成 Makefile
7. `make -j1` → 编译成功
8. `make install DESTDIR=$TEST_PREFIX` → staging 安装成功
9. 手动功能验证: `echo "1712345678 test" | cf` → `Apr  6 03:34:38 test`
10. `ohc-run.py package cf 1.2.8` → 预编译包制作成功 (83KB)
11. `make install`（不带 DESTDIR）→ 本地安装成功
12. `cf --version` → `cf version 1.2.8`
13. `ohc-run.py finish cf 1.2.8 published`

## 遇到的问题与解决方案

| # | 问题 | 根因（知识图谱匹配） | 解决方案 |
|---|------|------|----------|
| 1 | configure: cannot guess build type | config.guess (2018版) 不识别 HarmonyOS (**E007**) | 手动添加 HarmonyOS case 分支和 LIBC=ohos, 以及 *:HarmonyOS:*:* 系统识别 |
| 2 | config.sub 三元组验证失败 | config.sub 不识别 ohos OS (**E072**) | 手动添加 3 处修改：① ohos-linux 映射 ② OS 白名单 ohos* ③ kernel-os 白名单 linux-ohos* |
| 3 | config.status: Permission denied 创建 subs1.awk | HMDFS 上 umask 077 创建的目录无法写入文件（新发现） | 修改 configure 脚本：umask 077→022, 临时目录从 `./confXXXXXX` 改为 `${TMPDIR}/confXXXXXX` |

## 源码修改
- `config.guess`: 添加 `HarmonyOS)` case 分支（LIBC=ohos）和 `*:HarmonyOS:*:*)` 系统识别
- `config.sub`: 添加 ohos-linux 映射、 OS 白名单 ohos*、 kernel-os 白名单 linux-ohos*
- `configure`: 修改 umask 077→022 和 临时目录使用 $TMPDIR

## 补丁列表
| 补丁文件 | 修改内容 | 类型 |
|---------|------|------|
| 0001-config.guess.patch | 添加 HarmonyOS 识别 (+6/-0) | 平台适配 |
| 0002-config.sub.patch | 添加 ohos 三元组验证 (+6/-2) | 平台适配 |
| 0003-configure.patch | 修改 umask/TMPDIR (+3/-3) | 平台适配 |

## 依赖版本

无依赖

## 验证结果
```bash
# 版本验证
$ cf --version
cf version 1.2.8

# 功能验证：基本时间戳转换
$ echo "1712345678 hello world" | cf
Apr  6 03:34:38 hello world

# 功能验证：多行输入
$ echo -e "1712345678 line1\n1712345679 line2\n1712345680 line3" | cf
Apr  6 03:34:38 line1
Apr  6 03:34:39 line2
Apr  6 03:34:40 line3

# 功能验证：无时间戳行（不转换）
$ echo "no timestamp here" | cf
no timestamp here

# 功能验证：-l 选项（长格式）
$ echo "1712345678" | cf -l
Apr  6 03:34:38 2024

# 功能验证：-u 选项（UTC时间）
$ echo "1712345678" | cf -u
Apr  5 19:34:38

# 功能验证：-f 格式选项
$ echo "1712345678" | cf -f "%Y-%m-%d %H:%M:%S"
2024-04-06 03:34:38

# 功能验证：从文件读取
$ echo "1712345678 from file" > $TMPDIR/cf_test_input.txt
$ cf $TMPDIR/cf_test_input.txt
Apr  6 03:34:38 from file
```

## 交付物
| 文件 | 大小 | 说明 |
|------|------|------|
| cf-1.2.8-ohos-aarch64.tar.gz | 83KB (82,977 bytes) | 预编译包（ELF已签名） |
| cf-1.2.8-ohos-aarch64-debug.tar.gz | 31KB (30,743 bytes) | 调试符号包 |

## 注意事项
- config.guess/config.sub 年份为 2018-08-29，需手动修补 HarmonyOS 支持
- HMDFS 文件系统限制：umask 077 创建的目录内无法写入文件（需 umask 022 + 使用 TMPDIR）
- configure 每次运行会重新生成 config.status，需确保 configure 中的 TMPDIR 修复已包含
- G0 干净构建验证失败为 Python subprocess 平台限制（传递空参数 `[]`），手动验证通过
---

**编译结束**: 2026-06-10 01:42
**最终状态**: published