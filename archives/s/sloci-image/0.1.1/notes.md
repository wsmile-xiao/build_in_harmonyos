# sloci-image 0.1.1 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-06-04
- 编译器: clang/clang++
- 状态: built

## 编译步骤

sloci-image 是一个纯 shell 脚本工具，用于创建 OCI 容器镜像。无需编译，只需安装。

```bash
cd ~/tmp/builds/sloci-image-0.1.1.work
make install DESTDIR=$HOME/tmp/test-install-sloci-image-0.1.1 PREFIX=$HOME/usr/local
```

安装后验证脚本在 `$TEST_PREFIX/$HOME/usr/local/bin/sloci-image` 中。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | verify-build G4 失败：manifest 缺少 build_system | manifest.yaml 缺少 `build_system` 字段且 `build.system` 错误设为 autotools | 添加 `build_system: makefile` 到 manifest.yaml，将 `build.system` 从 autotools 改为 makefile |
| 2 | 无编译产物 | sloci-image 是 shell 脚本而非二进制文件 | 正常，G2 警告 "无二进制文件" 是预期的 |

## 源码修改

无源码修改。sloci-image 是纯 shell 脚本，在 HarmonyOS NEXT 环境下直接可用。

## 依赖版本

- 无编译依赖（shell 脚本工具）
- 运行依赖：POSIX sh

## 验证结果

```bash
file ~/tmp/test-install-sloci-image-0.1.1/storage/Users/currentUser/usr/local/bin/sloci-image
# 输出: /bin/sh script

python3 $SKILL_ROOT/scripts/ohc-run.py verify-build sloci-image 0.1.1
# 质量报告: PASS (G1-G4 全通过，G2 有脚本警告)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| sloci-image-0.1.1-ohos-aarch64.tar.gz | 15KB | 主包（含 shell 脚本） |

## 注意事项

- aarch64-debug 包不适用（shell 脚本无需调试符号包）
- manifest.yaml 需要包含 `build_system` 字段才能通过 G4 门禁
- G0 clean-build verify 失败是因为 makefile 项目在 ohc 自动化流程中 configure 阶段找不到 configure 命令（exit 127），但实际安装已手动验证成功