# shpotify 2.1 适配笔记

## 编译环境
- 构建系统: none（纯 Bash 脚本包，无编译步骤）
- 编译日期: 2026-08-14
- 编译器: 不适用（无 C/C++ 代码，无 ELF 产物）
- 状态: built

## 编译步骤

shpotify 是纯 Bash 脚本包，上游 tarball 仅包含 `README.md` 和 `spotify`
两个文件。无 configure、无 Makefile、无编译。conanfile.py 的 package()
将 `spotify` 脚本安装到 bin/ 并置可执行位，将 README.md 安装到
share/doc/shpotify 与 share/licenses/shpotify（MIT 许可证文本内嵌于
README.md "Copyright and license" 章节和脚本头部，上游无独立 LICENSE 文件）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `spotify help` 在 OHOS 上 exit 1 | 脚本检测不到 macOS Spotify.app 即退出 | 测试只用无参数入口（打印 Usage 且 exit 0），不修改上游脚本 |

## 依赖版本

运行时依赖（均为 OHOS PC 系统自带或预编译可用）：
- bash（Bash 4+）
- curl、base64、grep、sed、tr（coreutils）

## 验证结果

```bash
# 无参数入口（OHOS 可运行的真实入口）
bash spotify            # 输出 "Usage:"，exit 0
bash -n spotify         # 语法检查通过
# test_package 消费者测试：3 个测试用例 / 4 个断言全部通过
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/spotify | 上游 Bash 脚本（可执行） |
| share/doc/shpotify/README.md | 上游文档（含 MIT 许可证文本） |
| share/licenses/shpotify/README.md | 许可证记录 |

## 注意事项

- 上游 playback/search 子命令通过 macOS osascript 控制 Spotify 桌面应用，
  属 macOS 平台设计，OHOS 上不可用；不在测试中伪造这些入口的通过。
- 无上游自动化测试（tarball 仅两个文件），上游测试数如实记 0。
---

**编译结束**: 2026-08-14 20:28
**最终状态**: built
