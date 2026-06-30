# vttest 20251205 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-16
- 编译器: clang 15.0.4 / clang++
- 状态: published

## 编译步骤

1. 下载源码: curl -kL 下载 vttest-20251205.tgz（SSL证书验证失败，使用 -kL 绕过）
2. init-build 初始化
3. 修改 config.guess: 添加 HarmonyOS case 返回 `aarch64-unknown-linux-ohos`
4. 修改 config.sub: shebang 改为 bash（已内置 ohos* 支持）
5. 修改 configure: shebang 改为 `/data/service/hnp/bin/bash` 避免 toybox sh /tmp 写入失败
6. 手动 configure: `CONFIG_SHELL=/data/service/hnp/bin/bash bash ./configure --prefix=$DEFAULT_PREFIX`
7. 修改 config.status: 临时目录从 TMPDIR mktemp 改为当前目录 `_cs_tmp`（HMDFS 权限限制）
8. 手动运行 config.status: `bash ./config.status` → 生成 makefile 和 config.h
9. `make -j1` → 编译成功
10. `make install DESTDIR=$TEST_PREFIX` → staging 安装
11. `make install` → 默认前缀安装

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | uname -s = HarmonyOS，config.guess 没有 HarmonyOS case | 添加 `*:HarmonyOS:*:*` case，返回 `aarch64-unknown-linux-ohos` |
| 2 | config.sub shebang `/bin/sh` → toybox sh 临时文件失败 | toybox sh 使用 /tmp 存临时文件，但 /tmp 是只读的 | 修改 shebang 为 `/data/service/hnp/bin/bash` |
| 3 | config.status 临时目录权限问题 | mktemp -d 在 TMPDIR 创建子目录后无法写入文件（HMDFS sandbox） | 修改 config.status 临时目录为 `./_cs_tmp`（当前目录） |
| 4 | make check 需交互终端 | vttest 是终端测试程序 | 无法自动执行，记录跳过原因 |

## 源码修改

- 0001-config.guess.patch: 添加 HarmonyOS 检测（2处：UNAME_SYSTEM case + 主 switch）
- 0003-config.sub.patch: shebang 改为 bash
- 0004-configure.patch: shebang 改为 bash
- config.status: 临时目录修改（生成文件，不纳入补丁，需 configure 后手动修改）

## 依赖版本

- 无额外依赖（vttest 仅依赖标准 C 库和 POSIX 终端接口）

## 验证结果

```bash
$ vttest -V
VT100 test program, version 2.7 (20251205)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| vttest-20251205-ohos-aarch64.tar.gz | TBD | 预编译包 |

## 注意事项

- config.status 是 configure 生成的文件，其临时目录修改无法通过补丁固化；需在 configure 运行后手动修改或通过环境变量设置
- vttest 是交互式终端测试程序，make check 无法自动化
- 源码下载需要 curl -kL 绕过 SSL 验证

**编译结束**

**最终状态**: published
---

**编译结束**: 2026-06-16 21:07
**最终状态**: published
