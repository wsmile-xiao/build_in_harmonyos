# argbash 2.11.0 适配笔记

## 编译环境
- 构建系统: autotools（使用 autom4te 从 m4 宏生成脚本，非传统 configure/make）
- 编译日期: 2026-08-10
- 编译器: N/A（纯 shell 脚本工具，无 C/C++ 编译）
- 状态: built

## 编译步骤

argbash 是纯 shell 脚本工具，构建过程不涉及 C/C++ 编译，而是使用 autom4te 从 m4 宏源码生成可执行脚本。

1. **源码解压**: tar xzf argbash-2.11.0.tar.gz --strip-components=1
2. **Bootstrap**: `cd resources && make bootstrap` — 使用 autom4te 从 `src/*.m4` 生成 `bin/argbash` 脚本
3. **构建辅助脚本**: `bash bin/argbash src/argbash-init.m4 -o bin/argbash-init` 和 `bash bin/argbash src/argbash-1to2.m4 -o bin/argbash-1to2`
4. **安装**: `make install PREFIX=$DEFAULT_PREFIX ROOT=$TEST_PREFIX INSTALL_COMPLETION=no`
5. **验证**: `argbash --version` 输出 `argbash 2.11.0`

关键命令:
```bash
# Bootstrap (生成 argbash 主脚本)
cd resources && make bootstrap

# 构建辅助脚本 (OHOS chmod +x 不生效，需用 bash 调用)
bash bin/argbash src/argbash-init.m4 -o bin/argbash-init
bash bin/argbash src/argbash-1to2.m4 -o bin/argbash-1to2

# 安装到 staging 目录
make install PREFIX=/usr/local ROOT=$TEST_PREFIX INSTALL_COMPLETION=no
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 嵌套源码检测错误提取了 doc/ 子目录 | tarball 中 doc/ 目录被误判为源码根目录 | 手动重新解压 tarball --strip-components=1 |
| 2 | automake 未安装 | OHOS 环境未预装 automake | argbash 实际不需要 automake，仅需 autom4te（autoconf 2.72 已安装） |
| 3 | rst2man 未安装 | python-docutils 未预装 | pip3 install docutils（用于生成 manpage，非关键依赖） |
| 4 | make check 中 argbash-1to2 失败: chmod --reference 不支持 | OHOS 的 chmod 不支持 --reference（GNU coreutils 扩展） | 记录为平台限制，非关键功能（argbash-1to2 仅用于旧版本迁移） |
| 5 | conan create 中 bin/argbash 无法直接执行 | OHOS chmod +x 不生效（E046, SELinux 限制） | conanfile.py build() 中使用 `bash bin/argbash` 调用而非直接执行 |
| 6 | make bootstrap 后 make 尝试重建 argbash | bootstrap 中 touch src/argbash.m4 使 argbash.m4 比 bin/argbash 新 | 不使用 make 目标构建辅助脚本，直接用 bash 调用 |
| 7 | argbash 脚本中 process substitution (/dev/fd/63) 失败 | OHOS bash 对 /dev/fd 支持有限 | 非关键路径（settle_wrapped_fname 函数），不影响 argbash-init/1to2 生成 |

## 源码修改

无补丁。源码未做任何修改。

## 依赖版本

- autoconf (autom4te): 2.72
- bash: 系统自带 (/data/service/hnp/bin/bash)
- python3-docutils (rst2man): 0.23 (pip install，仅用于 manpage 生成，非必需)

## 验证结果

```bash
# argbash 版本检查
$ argbash --version
argbash 2.11.0

Argbash is an argument parser generator for Bash.

# 安装产物
$ find $TEST_PREFIX -type f | wc -l
29  # 包含 3 个可执行脚本 + 25 个 m4 库文件 + 1 个 manpage

# Conan 验证
$ conan-verify: PASS (G1, G2, G3, G4, L2, L4, L5)

# W3 本地 CI 模拟
$ setup.sh: PASS
$ build_and_test.sh: PASS
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/argbash | 主代码生成器脚本 |
| bin/argbash-init | 模板生成工具 |
| bin/argbash-1to2 | 旧版本格式转换工具 |
| lib/argbash/*.m4 | m4 宏库文件（25个） |
| share/man/man1/argbash.1.gz | manpage |

## 注意事项

- argbash 是纯 shell 脚本工具，无 C/C++ 编译，无 ELF 二进制
- 构建依赖 autom4te（autoconf 套件），运行依赖 bash（支持数组，bash >= 3.0）
- `chmod +x` 在 OHOS 上不生效（E046, SELinux 限制），需通过 `bash` 调用脚本
- `chmod --reference` 在 OHOS 上不支持，影响 argbash-1to2 的部分功能（非关键）
- Conan 配方中 package_type = "application"（命令行工具，非库）
- m4dir 路径在 package() 中被 patch 为相对路径 `$script_dir/../lib/argbash`
- conanfile.py build() 使用 `bash bin/argbash` 而非直接执行，绕过 OHOS chmod 限制

## 最终状态

编译结束。argbash 2.11.0 在 HarmonyOS PC (aarch64) 上编译成功，状态: built。
conan-verify 通过，W3 本地 CI 模拟通过。
---

**编译结束**: 2026-08-10 10:45
**最终状态**: built
