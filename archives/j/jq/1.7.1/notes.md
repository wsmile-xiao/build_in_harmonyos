# jq 1.7.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-07
- 编译器: clang 15.0.4
- 状态: built (conan-verify 通过)

## 编译步骤
1. 下载并解压源码（jq-1.7.1.tar.gz，从 gitcode.com 镜像获取）
2. 应用 6 个补丁：
   - 0001: config/config.guess HarmonyOS 支持
   - 0002: config/config.sub ohos 三元组支持
   - 0003: modules/oniguruma/config.guess HarmonyOS 支持
   - 0004: modules/oniguruma/config.sub ohos 三元组支持
   - 0005: configure umask 修复（077→000，解决 HMDFS 跨 uid 临时目录权限问题）
   - 0006: modules/oniguruma/configure umask 修复
3. 配置：`./configure --prefix=$DEFAULT_PREFIX --with-oniguruma=builtin`
4. 编译：`make -j1`（HarmonyOS 不支持 mkfifo jobserver）
5. 测试：7/8 通过

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess/config.sub 不识别 HarmonyOS | 上游未包含 ohos 三元组 | 添加 HarmonyOS 和 ohos-linux 支持 |
| 2 | oniguruma 子模块 config 不识别 HarmonyOS | 子模块有独立的 config 文件 | 同步修复子模块的 config.guess/config.sub |
| 3 | config.status 报 Permission denied | HMDFS 文件系统所有文件属主为 file_manager(uid 20001006)，umask 077 创建的临时目录(0700)对其他 uid 不可访问 | 将 configure 中 umask 077 改为 umask 000 |
| 4 | make -j2 报 jobserver mkfifo 失败 | HarmonyOS 不支持 mkfifo | 使用 make -j1 |
| 5 | shtest 失败 | BusyBox script 不支持 -e 选项 | 平台限制，非功能问题 |

## 源码修改
| 文件 | 修改内容 | 补丁 |
|------|----------|------|
| config/config.guess | 添加 HarmonyOS LIBC 检测 + aarch64:HarmonyOS 识别 | 0001 |
| config/config.sub | 添加 ohos-linux + linux-ohos* + ohos* | 0002 |
| modules/oniguruma/config.guess | 添加 HarmonyOS LIBC 检测 + aarch64:HarmonyOS 识别 | 0003 |
| modules/oniguruma/config.sub | 添加 ohos-linux + linux-ohos* + ohos* | 0004 |
| configure | umask 077 → 000（2 处） | 0005 |
| modules/oniguruma/configure | umask 077 → 000（2 处） | 0006 |

## 依赖版本
- oniguruma（bundled，--with-oniguruma=builtin，完整正则表达式支持）

## 验证结果
- 官方测试 7/8 通过：
  - PASS: tests/jqtest, utf8test, base64test, optionaltest, onigtest, manonigtest, mantest
  - FAIL: tests/shtest（BusyBox script -e 不兼容，平台限制）
- jq --version → jq-1.7.1 ✅
- JSON 处理测试通过 ✅
- 正则表达式测试（onigtest）通过 ✅

## Conan 配方
- package_type: application（命令行工具）
- configure_args: --with-oniguruma=builtin
- patches: 6 个（通过 conandata.yml 声明）
- test_package: 运行 jq 二进制验证 JSON 处理和正则表达式支持
- commands.json: 声明 jq 命令行工具
---

**编译结束**: 2026-08-07 01:02
**最终状态**: built
