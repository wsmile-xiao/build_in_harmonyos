# sleuthkit 4.12.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-25
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 初始化：`ohc-run.py init-build sleuthkit latest --url=https://github.com/sleuthkit/sleuthkit/releases/download/sleuthkit-4.12.1/sleuthkit-4.12.1.tar.gz`
2. Configure：`./configure --prefix=$DEFAULT_PREFIX`
3. 编译：`make -j2`
4. 测试：`make check`（记录结果）
5. 安装：`make install DESTDIR=$TEST_PREFIX`
6. 打包：`ohc-run.py package sleuthkit 4.12.1`
7. 验证：`fls -V` → "The Sleuth Kit ver 4.12.1"

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 OHOS | 平台不识别 | 替换 config/config.guess |
| 2 | HMDFS umask 077 权限问题 | UID 映射机制 | 修改 configure 第 24261、24266 行 |
| 3 | 编译错误 - Werror | OHOS SDK 头文件警告 | 移除 tsk/pool/Makefile.am 的 -Werror |

## 源码修改

- 0001-config-config.guess.patch：替换为 aarch64-linux-gnu 识别脚本
- 0002-config-config.sub.patch：替换为 aarch64-linux-gnu 识别脚本
- 0003-configure.patch：umask 077 → umask 022
- 0004-tsk-pool-Makefile.patch：移除 -Werror
- 0005-tsk-pool-Makefile.am.patch：移除 -Werror

## 依赖版本

无额外依赖

## 验证结果

```bash
$ fls -V
The Sleuth Kit ver 4.12.1
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| sleuthkit-4.12.1-aarch64-linux-gnu.tar.gz | 21MB | 预编译包 |

## 注意事项

- 此版本无额外依赖
- 编译时需注意 Werror 问题