# bork 0.14.0 适配笔记

## 编译环境
- 构建系统: custom（纯 bash 配置管理工具，无编译）
- 编译日期: 2026-09-07
- 编译器: 无（纯脚本）
- 状态: built

## 编译步骤

```bash
# conan create 内部（conanfile.py）：
# 1. source(): Git.clone（borksh/bork，--depth 1 --branch v0.14.0 浅克隆）——
#    git 独立 ssl，CI Python 无 SSL 模块时可下载
# 2. build(): apply_conandata_patches（无补丁，G1 完整性要求调用）——空操作
# 3. package(): bin/bork → bin/ + lib/{declarations,helpers,support} → lib/ + 文档
#    （bork 按 BASH_SOURCE 推导 BORK_SOURCE_DIR=<pkg> 并 source <pkg>/lib/.../，
#     不读环境变量覆盖，故模块必须落在 <pkg>/lib/）
# 4. test_package: test_bork.py 断言 bork 存在 + bash -n 语法可解析
#    + lib 模块已打包 + 实际执行 bork version 输出版本号
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Git.clone 指定 tag 需用 --branch | 浅克隆（--depth 1）下 checkout 固定 commit 报 unable to read tree | Git.clone args=["--depth","1","--branch","v0.14.0"] 直接切 tag |
| 2 | test_package 运行需路径加引号 | 工作目录名含括号 "build_in_harmonyos-main (1)"，/system/bin/sh 解析未加引号的 (1) 报 syntax error | python3 执行 + 路径单引号包裹（参考 boom-completion 同款修复） |

## 源码修改

无外部补丁文件（patches/ 为空）；仅 conanfile.py 的 package() 复制 bork
主脚本与 lib/ 模块到 bork 实际加载路径（bin/ + lib/）。

## 依赖版本

无 conan 库依赖（纯 bash 配置管理工具，运行时依赖 bash 3.2 + sed/awk/grep）。

## 验证结果

```bash
# conan-verify bork 0.14.0 → 全门禁 PASS
# G1 配方完整性 / G0 知识图谱 / G2 conan create / G3 R26 隔离 /
# G4 产物完整性 / L2 smoke / L4 checksec / L5 基线对比 全部 PASS

# test_package R34：bin/bork 存在 + bash -n 语法可解析 +
# lib/{declarations,helpers,support} 模块已打包（含 .sh）+
# 实际执行 `bork version` 输出版本号（运行时真实执行，非仅静态校验）
```
