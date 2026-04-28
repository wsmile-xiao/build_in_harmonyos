# sevenzip 26.00 适配笔记

## 编译环境
- 构建系统: custom makefile (cmpl_clang.mak)
- 编译日期: 2026-04-23
- 编译器: clang 15.0.4
- 状态: published

## 编译步骤
```bash
cd CPP/7zip/Bundles/Alone2
make -j -f ../../cmpl_clang.mak
# 生成 b/c/7zz
```

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | const cast 丢失 qualifier | OpenHarmony CPU_ISSET 宏 | 添加 -Wno-cast-qual |
| 2 | 整数精度转换警告 | unsigned long → int | 添加 -Wno-shorten-64-to-32 |
| 3 | 递归宏展开警告 | OpenHarmony stdin/stdout 递归宏 | 添加 -Wno-disabled-macro-expansion |

## 源码修改
- fix-clang-warnings.patch: 修改 warn_clang.mak 添加 -Wno-* 选项

## 验证结果
- 压缩/解压测试通过 ✅
- 7zz b 基准测试正常 ✅

## 交付物
- 7zz (3.0MB ELF 可执行文件)

## 注意事项
- 仅编译命令行版本 7zz
- RAR 解压功能保留（含 unRAR 许可限制）
