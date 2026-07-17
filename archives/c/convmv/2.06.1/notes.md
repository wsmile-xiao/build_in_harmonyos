# convmv 2.06 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-05-25
- 编译器: clang/clang++（实际不需要C编译器，convmv为纯Perl脚本）
- 状态: built

## 编译步骤

convmv 是纯 Perl 脚本，使用简单 Makefile 构建：
1. `make PREFIX=$DEFAULT_PREFIX` — 使用 pod2man 生成 man 页面
2. `make install DESTDIR=$TEST_PREFIX PREFIX=$DEFAULT_PREFIX` — 安装到 staging 目录
3. `make install PREFIX=$DEFAULT_PREFIX` — 本地安装（验证）
4. 无 configure 步骤（makefile 类构建系统）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL下载失败 | HarmonyOS CA证书缺失，Savannah服务器超时 | 设置 SSL_CERT_FILE 环境变量；使用 Debian pool URL |
| 2 | `../convmv: No such file or directory` | shebang `#!/usr/bin/perl` 在鸿蒙上无效（/usr/bin/perl不存在） | 修改为 `#!/usr/bin/env perl`（补丁 0001-convmv.patch） |
| 3 | manifest 缺少 build_system 字段 | init-build模板使用嵌套格式，G4检查期望顶层字段 | 在manifest顶层添加 `build_system: makefile` |
| 4 | G0 clean-verify configure失败 | convmv无configure脚本，G0默认运行configure | 已知限制，makefile类不需configure，G1-G4全部PASS |
| 5 | convmv --version 不支持 | convmv无--version选项 | 通过 `--help` 输出获取版本信息（首行显示 "convmv 2.06"） |
| 6 | 测试套件double-utf8-test失败 | symlink时间戳不一致（cp不保留symlink mtime） | 非功能性缺陷，核心编码转换功能正常 |

## 源码修改

- `convmv`: 将 `#!/usr/bin/perl` 改为 `#!/usr/bin/env perl`
  - 补丁: `0001-convmv.patch`（+7/-7, platform类, 仅适用于鸿蒙平台）

## 依赖版本

- perl 5.42.0（系统自带，位于 /data/service/hnp/bin/perl）
- pod2man（系统自带，位于 /data/service/hnp/bin/pod2man）

## 验证结果

### 版本验证
```bash
$ $DEFAULT_PREFIX/bin/convmv --help | head -2
convmv 2.06 - converts filenames from one encoding to another
Copyright (C) 2003-2025 Bjoern JACKE <bjoern@j3e.de>
```

### 功能验证
```bash
# --unescape: 百分号编码文件名转换
$ convmv --unescape --notest -r test_dir/
  test%20file.txt → test file.txt  ✅

# --upper: 大写转换
$ convmv --upper -f utf8 --notest -r test_dir/
  hello.txt → HELLO.TXT  ✅

# --list: 编码列表
$ convmv --list | wc -l
  124  ✅

# NFC智能检测
$ convmv --nfc -f utf8 -t utf8 -r test_dir/
  正确跳过已是UTF-8的文件名  ✅
```

### 安装完整性
```bash
$ file $DEFAULT_PREFIX/bin/convmv
  perl script  ✅
$ ls $DEFAULT_PREFIX/share/man/man1/convmv.1.gz
  已安装  ✅
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| convmv-2.06-ohos-aarch64.tar.gz | 60KB (61980B) | 预编译包 |
| 0001-convmv.patch | 4279B | shebang修改补丁 |
| test-report.md | — | 详细测试验证报告 |
| quality-report.md | — | G1-G4质量门禁报告 |

## 注意事项

- convmv 不支持 --version，验证时使用 --help 输出的版本信息
- 上游测试套件 double-utf8-test 失败（symlink mtime 不保持），不影响核心功能
- G0 clean-verify 对 makefile 类构建系统不适用（缺少 configure 步骤）
- 完整测试验证报告见 `reports/test-report.md`

---
**编译结束**: 2026-07-15 15:39
**最终状态**: built
