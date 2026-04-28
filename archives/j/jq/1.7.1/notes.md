# jq 1.7.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-04-13
- 编译器: clang 15.0.4
- 状态: partial

## 编译步骤
1. 下载并解压源码（jq-1.7.1.tar.gz）
2. 应用 2 个补丁：config.guess + config.sub（含 oniguruma 子模块）
3. 修复 oniguruma 子模块 config.guess 重复条目（第 951 行）
4. 配置：`./configure --prefix=$HOME/usr/local CC=clang CFLAGS="-fPIC -O2"`
5. 编译：`make -j$(nproc)`（含 bundled oniguruma）
6. 测试：7/8 通过

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | oniguruma 子模块 configure 失败 | config.guess 有重复的 HarmonyOS 条目（第 951 行） | 删除重复行 |
| 2 | shtest 失败 | BusyBox script 不支持 -e 选项 | 平台限制，非功能问题 |

## 源码修改
| 文件 | 修改内容 | 是否已生成补丁 |
|------|----------|----------------|
| config/config.guess | 添加 HarmonyOS LIBC 检测 + aarch64:HarmonyOS 识别 | ✅ 0001-config-guess-harmonyos-support.patch |
| config/config.sub | 添加 ohos-linux + linux-ohos* + ohos* | ✅ 0002-config-sub-harmonyos-support.patch |
| modules/oniguruma/config.guess | 删除重复条目 | 已在编译时手动修复 |

## 依赖版本
- oniguruma（bundled，已包含在源码中）

## 验证结果
- 官方测试 7/8 通过：
  - PASS: tests/mantest, jqtest, utf8test, base64test, optionaltest, onigtest, manonigtest
  - FAIL: tests/shtest（BusyBox script -e 不兼容）
- jq --version → jq-1.7.1 ✅
- JSON 处理测试通过 ✅

## 交付物
| 文件 | 大小 | 说明 |
|------|------|------|
| jq-1.7.1-ohos-aarch64.tar.gz | 6.2MB | 预编译包（含 bundled oniguruma） |

## 注意事项
- 本次编译使用 bundled oniguruma（正则表达式支持完整），无需系统安装
- 含 autotools 子模块的项目需单独修复子模块的 config.guess
- 子模块 config.guess 中的 HarmonyOS 补丁可能包含重复条目需清理
