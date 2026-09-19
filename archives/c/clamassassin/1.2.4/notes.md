# clamassassin 1.2.4 适配笔记

## 编译环境
- 构建系统: autotools (configure + make)
- 编译日期: 2026-09-09
- 编译器: 无（纯 shell 脚本）
- 状态: pending

## 编译步骤

1. 下载源码: `clamassassin-1.2.4.tar.gz` from jameslick.com
2. 解压后运行 configure:
   - `./configure --prefix=/ --disable-clamdscan --disable-version-check`
3. 编译: `make`（实际无编译步骤，all 目标为空）
4. 安装: `make install DESTDIR=<pkg_dir>`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 需要 clamscan/formail/sigtool | 这些是运行时依赖，configure 用 AC_PATH_PROG 检测 | 使用 --disable-version-check 跳过版本检查；clamscan 等需在 PATH 中 |

## 依赖版本

无构建依赖。运行时依赖 clamav (clamscan) 和 procmail (formail)。

## 测试

上游 tarball 无自带测试（仅 8 个文件：configure/configure.ac/Makefile.in/
clamassassin.in/README/CHANGELOG/LICENSE）。因此 test_package 采用
**mock 桩功能测试**（`test_package/test.sh`）：

- mock `clamscan`：`-V` 返回版本号；扫描 stdin 发现 EICAR 标记返回 1 并输出
  `STDIN: Eicar-Signature FOUND`，否则返回 0
- mock `formail`：`-f -I HDR` 前置头；`-c -x FIELD` 提取头值（保留上游
  clamassassin 需剥离的前导空格行为）
- 对已安装脚本做 TMPPATH/工具路径归一化后，用两封真实邮件跑通完整过滤逻辑：
  1. clean 邮件 → `X-Virus-Status: No`（断言 2 项）
  2. infected 邮件 → `X-Virus-Status: Yes` + `X-Virus-Report: Eicar-Signature FOUND`（断言 2 项）
- 另有安装存在性 + `sh -n` 语法校验（断言 1 项）

共 5 项断言，本地 `conan create` 全绿。

## 注意事项

- 纯 shell 脚本，无编译代码
- make install 仅复制一个脚本文件到 bin/
- configure 需要多个运行时工具在 PATH 中
- 本机 /bin/sh 为 zsh 且 /tmp 只读：test.sh 避免 here-document（zsh here-doc
  会写 /tmp 临时文件），mock 脚本用 printf 逐行生成
