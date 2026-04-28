# help2man 1.49.3 适配笔记

## 编译环境
- 构建系统: script（纯 Perl）
- 编译日期: 2026-04-14
- 编译器: N/A（Perl 脚本）
- 状态: success

## 编译步骤
1. 下载并解压源码
2. 运行 configure：`./configure --prefix=$TEST_PREFIX`
3. 运行 make install
4. help2man.PL 自动检测并嵌入正确的 perl 路径，无需手动修改 shebang

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Makefile 生成差异 | configure 在 OHOS 上生成的路径不同 | 生成补丁 0001-Makefile.patch |
| 2 | help2man 脚本 perl 路径 | 嵌入的 perl 路径为 OHOS 路径 | 生成补丁 0002-help2man.patch（自动处理） |

## 源码修改
| 文件 | 修改内容 | 是否已生成补丁 |
|------|----------|----------------|
| Makefile | configure 生成的构建文件修改 | ✅ 0001-Makefile.patch |
| help2man | Perl 脚本中嵌入正确的 perl 路径 | ✅ 0002-help2man.patch |

## 依赖版本
- perl 5.42.0
- sed（需修复 fstat 问题的 GNU sed）

## 验证结果
- help2man --version → GNU help2man 1.49.3 ✅
- help2man --help 正常工作 ✅
- 首次运行需点击确认弹窗（鸿蒙安全机制）✅

## 交付物
| 文件 | 大小 | 说明 |
|------|------|------|
| help2man-1.49.3-ohos-aarch64.tar.gz | 49.5KB | 预编译包 |

## 注意事项
- 首次执行时鸿蒙会弹出安全确认窗口，需 30 秒内点击确认
- 生成的脚本自动包含正确的 perl 路径，无需手动修改 shebang
