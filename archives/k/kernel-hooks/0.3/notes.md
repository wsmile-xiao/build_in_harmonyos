# kernel-hooks 0.3 鸿蒙适配笔记

## 环境信息
- 操作系统：HarmonyOS 6.0（aarch64）
- 构建系统：Shell（无编译）

## 源码来源
- Alpine aports 仓库：https://gitlab.alpinelinux.org/alpine/aports/
- 子目录：`main/kernel-hooks/`
- 固定 commit：`a3c0689895e115d2910ab915de99a85bc11afe42`
- 上游无独立 tarball，采用 raw URL 分别下载两个文件

## 文件清单
| 文件 | 上游作用 | 安装路径 |
| --- | --- | --- |
| README | 说明文件 | `etc/kernel-hooks.d/README` |
| kernel-hooks.trigger | APK trigger 脚本 | `share/kernel-hooks/kernel-hooks.trigger`（可执行） |

## 测试情况

### 上游测试
上游 APKBUILD 中声明 `options="!check"  # no tests`，即上游无测试用例。
这是一个纯 Shell 脚本包，不涉及编译产物，上游未提供任何自动化测试。

### 新增鸿蒙测试
在 `test_package/test_package.sh` 中新增了消费者测试，验证：

1. `README` 已安装到 `etc/kernel-hooks.d/README`，且内容包含 `kernel-hooks`
2. `kernel-hooks.trigger` 已安装到 `share/kernel-hooks/`，且具备可执行权限（755）
3. trigger 脚本通过 `sh -n` 语法检查
4. 在无 `/etc/kernel-hooks.d` 的环境下，trigger 脚本正常退出（exit 0）

## 适配说明
- 纯 Shell 脚本包，无编译过程
- APK 的 trigger 机制在鸿蒙 + Conan 环境下不自动激活
- trigger 脚本作为参考实现保留，如需激活需额外集成系统级 hook 机制

## CI 修复记录
- **问题**：CI L0p 门禁检查失败，提示 `settings` 缺少 `compiler` 和 `build_type`
- **原因**：OHOS profile 要求 `settings` 必须包含全部四项（`os`, `arch`, `compiler`, `build_type`），即使本包为纯脚本、不使用编译器
- **修复**：将 `settings = "os", "arch"` 改为 `settings = "os", "arch", "compiler", "build_type"`

## 相关 PR
（待填写）
