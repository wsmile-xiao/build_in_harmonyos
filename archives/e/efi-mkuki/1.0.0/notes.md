# efi-mkuki 1.0.0 适配笔记

## 编译环境
- 构建系统: custom (shell script)
- 编译日期: 2026-08-06
- 编译器: N/A (shell script)
- 状态: published

## 源码
- 仓库: https://github.com/jirutka/efi-mkuki
- 版本: v1.0.0
- sha256: 3a485ce63ef4977b9d7586d0a2abded7d2ecfb7a582386ed0cc6a43e190410d0

## 编译步骤

Shell 脚本项目，无需传统 configure/make 流程。Conan 配方使用 `copy()` 手动安装脚本到 `bin/` 目录：

```python
# conanfile.py package() 方法
copy(self, "efi-mkuki", src=self.source_folder, dst=bin_dir)
```

Makefile 仅包含 install/uninstall/help/bump-version/release 目标，无 configure/make check。

## 遇到的问题与解决方案

1. **版本号问题**: 任务指定版本 "7" 但 Conan 不接受单字符版本号（需至少2字符）。
   - 解决: 按 R37 使用上游版本 "1.0.0" 作为 Conan 版本号。

2. **conanfile.py 模板不匹配**: 自动生成的模板使用 Autotools，但本项目是纯 shell 脚本。
   - 解决: 参考 abcde 等 shell 脚本项目，重写 conanfile.py 为 application 类型，手动复制脚本到 bin/。

3. **test_package 模板不匹配**: 自动生成的模板使用 CMake/C，不适用于 shell 脚本工具。
   - 解决: 重写 test_package 为 bash 脚本验证，检查脚本存在、可执行、shebang、语法、版本输出。

## 验证结果

- `efi-mkuki -V`: ✅ 输出 `efi-mkuki 1.0.0`
- conan-verify: ✅ G1-G4 全部通过
- W3 本地 CI 模拟: ✅ 通过

## make check

- **结果**: SKIP
- **原因**: 项目无 test/check 目标，Makefile 仅包含 install/uninstall/help 目标

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方 (application 类型, shell 脚本安装) |
| conandata.yml | 源码 URL + sha256 |
| test_package/ | 消费者测试 (bash 脚本冒烟测试, 5 断言) |
| commands.json | 命令行工具声明 (R38) |

---
**编译结束**: 2026-08-06
**最终状态**: published
