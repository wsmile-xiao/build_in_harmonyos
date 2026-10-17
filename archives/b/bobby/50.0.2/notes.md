# bobby 50.0.2 适配笔记

## 编译环境
- 构建系统: custom（纯 bash prompt 主题脚本，无编译）
- 编译日期: 2026-09-07
- 编译器: 无（纯脚本）
- 状态: built

## 编译步骤

```bash
# conan create 内部（conanfile.py）：
# 1. source(): Git.clone（Bash-it 仓库，--depth 1 浅克隆即 master HEAD，
#    含 themes/bobby/bobby.theme.bash）——git 独立 ssl，CI Python 无 SSL 时可下载
# 2. build(): apply_conandata_patches（无补丁，G1 完整性要求调用）——空操作
# 3. package(): 提取 themes/bobby/bobby.theme.bash → share/bobby/ + 文档
# 4. test_package: test_bobby.py 断言主题存在 + /system/bin/sh -n 语法可解析
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | G2 FAIL：git checkout 报 unable to read tree | 臆造固定 commit（4d2d02f0），浅克隆（--depth 1）只有 HEAD 无该 commit 的 tree | 去掉 git.checkout——浅克隆即 Bash-it master HEAD（含 bobby 主题），固定 commit 需深克隆 |
| 2 | test_package 运行需路径加引号 | 工作目录名含括号 "build_in_harmonyos-main (1)"，/system/bin/sh 解析未加引号的 (1) 报 syntax error | python3 执行 + 路径单引号包裹（参考 boom-completion 同款修复） |

## 源码修改

无外部补丁文件（patches/ 为空）；仅 conanfile.py 的 package() 提取 bobby
主题脚本到 share/bobby/。

## 依赖版本

无 conan 库依赖（纯 bash prompt 主题，运行时依赖 bash+git）。

## 验证结果

```bash
# conan-verify bobby 50.0.2 → 全门禁 PASS
# G1 配方完整性 / G0 知识图谱 / G2 conan create / G3 R26 隔离 /
# G4 产物完整性 / L2 smoke / L4 checksec / L5 基线对比 全部 PASS

# test_package R34：share/bobby/bobby.theme.bash 存在 + /system/bin/sh -n
# 语法可解析（提示符渲染需交互式 shell 环境，OHOS 无法验证，按 rule 1.2 声明）
```
