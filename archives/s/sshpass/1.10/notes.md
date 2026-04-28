# sshpass 1.10 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-04-23
- 编译器: gcc (clang 15.0.4)
- 状态: published

## 编译步骤
```bash
./configure --prefix=$HOME/usr/local --host=aarch64-unknown-linux-ohos
# 由于 toybox mktemp 问题，手动编译:
gcc -o sshpass sshpass.c -DHAVE_CONFIG_H
cp sshpass $TEST_PREFIX/$HOME/usr/local/bin/
```

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | E007 平台识别缺失 | 补丁 0001/0002 |
| 2 | config.status 临时文件权限错误 | toybox mktemp 不兼容 | 手动编译绕过 |
| 3 | make 尝试运行 aclocal-1.16 | autotools 依赖链问题 | 手动编译 sshpass.c |

## 源码修改
- 0001-config.guess.patch: 添加 HarmonyOS 平台识别
- 0002-config.sub.patch: 添加 linux-ohos 内核支持

## 验证结果
- sshpass -V 显示版本信息 ✅
- ELF 64-bit LSB pie executable, ARM aarch64

## 交付物
- bin/sshpass

## 注意事项
- toybox mktemp 与 GNU mktemp 不兼容
- 建议使用手动编译方式
