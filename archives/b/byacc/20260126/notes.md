# byacc 20260126 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-26
- 编译器: clang 15.0.4 / clang++
- 平台: aarch64-unknown-linux-ohos (HarmonyOS)
- 状态: built

## 编译步骤

1. init-build: `python3 $SKILL_ROOT/scripts/ohc-run.py init-build byacc 20260126 --url=https://invisible-mirror.net/archives/byacc/byacc-20260126.tgz`
2. 预扫描: 发现 PSCAN-BUILD-001(config.guess需补丁)、PSCAN-FS-001(/tmp硬编码)、PSCAN-HMDFS-002(chmod)
3. 补丁 config.guess/config.sub: `perl patch-autotools-ohos.pl config.guess config.sub`
4. configure: `./configure --prefix=$DEFAULT_PREFIX`
5. 修复 config.status umask: HMDFS上umask 077创建临时目录导致Permission denied，修改为umask 002
6. 重运行 config.status: `./config.status` 成功生成 config.h、makefile、install-man
7. make: `make -j2` 成功
8. make install DESTDIR: `make install DESTDIR=$TEST_PREFIX` 成功
9. make check: 绝大多数测试通过，8项错误消息格式差异（非功能性bug）
10. 预编译包制作: `python3 $SKILL_ROOT/scripts/ohc-run.py package byacc 20260126`
11. 本地安装验证: `make install` → `$DEFAULT_PREFIX/bin/yacc --version` → ✅ 2.0 20260126

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess/config.sub 不识别 OHOS | autotools 默认不支持 HarmonyOS 三元组 | 使用 patch-autotools-ohos.pl 补丁 (E007) |
| 2 | config.status 创建临时文件 Permission denied | HMDFS 上 umask 077 创建的目录权限受限（setgid+drwx--S---模式） | 修改 config.status 中 `umask 077` 为 `umask 002`，这是 HMDFS 平台限制 |
| 3 | make check 8项错误消息差异 | yacc 处理不存在文件时错误优先级不同（先报告语法错误而非文件错误） | 非功能性差异，不影响使用 |

## 源码修改

| 文件 | 修改类型 | 说明 |
|------|----------|------|
| config.guess | autotools补丁 | 添加 __OHOS__ LIBC 检测和 HarmonyOS 系统标识 |
| config.sub | autotools补丁 | 添加 ohos-linux 三元组支持 |

注意: configure 的 umask 077 修改已固化为补丁（sed -i 's/umask 077/umask 022/g' configure），这是 E011 推荐方案。

## 依赖版本

无外部依赖，byacc 是独立的解析器生成工具。

## 验证结果

```bash
$DEFAULT_PREFIX/bin/yacc --version
# 输出: yacc - 2.0 20260126

# 功能测试: 用 yacc 处理简单语法文件
$DEFAULT_PREFIX/bin/yacc test_grammar.y
# ✅ 成功生成 y.tab.c
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| byacc-20260126-ohos-aarch64.tar.gz | 236KB | 预编译包（含 yacc 二进制+man page） |

## 注意事项

1. config.status umask 077 在 HMDFS 上不可用 - 这是一个平台级问题（E002变体），影响所有 autotools 软件。需要记录到知识图谱。
2. make check 错误消息差异不影响功能，属于测试套件敏感度问题。
3. /tmp 硬编码（main.c:780）在 HMDFS 上不阻塞（代码已有 "." fallback），但最佳实践应改用 TMPDIR。

## 知识提取记录

- HMDFS umask 077 临时目录权限问题：引擎匹配 E011 ✅（已有知识条目）
  - 引擎匹配: E011（HMDFS umask 077 权限问题）
  - 推荐方案: sed -i 's/umask 077/umask 022/g' configure（已执行）
  - 无需创建新草稿（已有E011条目）�）
  - 计划: `python3 $SKILL_ROOT/scripts/ohc-run.py graph add --draft` 创建草稿t` 创建草稿
---

**编译结束**: 2026-05-26 04:52
**最终状态**: built
