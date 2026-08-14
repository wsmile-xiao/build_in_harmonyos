# adarkroom 1.4+dfsg.1 适配笔记

## 三重身份

| 身份 | 值 |
|------|-----|
| 平台 | adarkroom 1.4+dfsg.1（Issue #2139） |
| 上游 | doublespeakgames/adarkroom，tag 1.4，MPL-2.0 |
| 归档 | conan ref `adarkroom/1.4+dfsg.1`，路径 `archives/a/adarkroom/1.4+dfsg.1/` |

版本说明：平台版本 `1.4+dfsg.1` 是 Debian 对上游 tag 1.4 的 DFSG 重打包
（移除压缩的第三方 lib/jquery.min.js、lib/jquery.color-*.min.js 与生成的
lang/*/strings.js）。Conan 版本沿用 `1.4+dfsg.1`（Conan Version 解析有效），
与平台版本保持一致，未擅自改名。

## 编译环境

- 构建系统: custom（纯 HTML/CSS/JS 浏览器游戏，无原生编译）
- 编译日期: 2026-08-13
- 状态: built

## 编译步骤

1. 源码：`adarkroom_1.4+dfsg.1.orig.tar.xz`（deb.debian.org 官方 pool）
   - SHA256 `1ffcce45edc7b2315b565e98381d12277f516ba8794a2837e542774bcb0dfbf4`
   - 与官方 .dsc Checksums-Sha256 一致
2. 解包核验：目录 `adarkroom-1.4/`，许可证 LICENSE.md（MPL-2.0）
3. 无编译步骤：`build()` 为空；`package()` 将网页资源安装到
   `share/adarkroom/www/`（与 Debian 布局 `/usr/share/adarkroom/www/` 对齐）
4. 许可证与文档：LICENSE.md → licenses/；README.md、contributing.md → share/doc/adarkroom/

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 无 | 纯静态网页资源包，上游无构建系统 | 按数据包方式归档，仅安装真实产物 |

## 依赖版本

- 无 Conan 依赖（上游浏览器游戏不依赖任何系统库）

## 验证结果

- `conan create` 干净构建通过（G2）
- test_package 消费者测试：验证 index.html/engine.js/css/audio/img/lang/
  licenses 真实产物，断言全部通过
- 上游无自动化测试（无 test 文件、package.json 仅 dev-server），如实记 0

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | 数据包配方（package_type=application，resdirs=share/adarkroom） |
| conandata.yml | 官方源码 URL + SHA256 |
| test_package/ | 消费者测试（test_adarkroom.py 验证真实网页产物） |

## 注意事项

- 不创建 commands.json：本包无 CLI 可执行文件（R38 仅 tool 类型需要）
- 上游无测试用例，测试统计以消费者测试为主
---

**编译结束**: 2026-08-14 08:33
**最终状态**: built
