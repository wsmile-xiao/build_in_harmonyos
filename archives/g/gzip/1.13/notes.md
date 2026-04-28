# gzip 1.13 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-04-12
- 编译器: clang 15.0.4
- 状态: success

## 编译步骤
1. 下载 gzip-1.13.tar.xz 并解压
2. 应用 config.guess/config.sub 补丁
3. `./configure --prefix=$TEST_PREFIX CC=clang CFLAGS="-fPIC -O2"`
4. `make && make install`

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 不识别 HarmonyOS | 标准问题 | patch-autotools-ohos.pl 修复 |
| 2 | config.sub ohos-linux 块有 bug（重复行/错误值） | 补丁脚本 bug | 手动修复 3 处 |
| 3 | config.sub 缺少 linux-ohos* 允许列表 | 未包含 | 添加到 linux-gnu* 行 |
| 4 | shell 脚本因 shebang 限制无法执行 | HM 安全限制 | 通过 sh 直接调用 |

## 源码修改
| 文件 | 修改内容 | 是否已生成补丁 |
|------|----------|----------------|
| build-aux/config.guess | 添加 HarmonyOS 检测 | ✅ 0001 |
| build-aux/config.sub | 添加 ohos 三元组支持 | ✅ 0002 |

## 依赖版本
- 无外部依赖

## 验证结果
- gzip 压缩/解压 ✅
- gunzip 脚本 ✅
- zcat ✅
- 管道模式 ✅
- zless/zmore（需 sh 调用）✅

## 交付物
| 文件 | 大小 | 说明 |
|------|------|------|
| gzip-1.13-ohos-aarch64.tar.gz | 297KB | Release 包 |
| gzip-1.13-ohos-aarch64-debug.tar.gz | 49KB | Debug 符号 |

## 注意事项
- zless/zmore 等 shell 脚本需通过 `sh zless` 方式调用
