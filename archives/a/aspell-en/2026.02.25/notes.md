# aspell-en 2026.02.25 适配笔记

## 软件信息
- **名称**: aspell-en
- **版本**: 2026.02.25
- **描述**: English dictionary for GNU Aspell spell checker
- **许可证**: BSD-3-Clause (the dictionary itself)
- **主页**: http://aspell.net
- **源码URL**: https://ftp.gnu.org/gnu/aspell/dict/en/aspell6-en-2026.02.25-0.tar.bz2
- **SHA256**: 77a5cb437c45d1115f3b593802c20651d8c93803ed1073278dc1a1240016f10d

## 构建特征
- **类型**: Aspell dictionary data package (no C/C++ compilation)
- **构建系统**: autotools (configure + make)
- **产物**: Dictionary data files (.cwl, .dat, .multi, .alias)
- **包类型**: header-library (content/data package, no compiled binary)

## 依赖关系
- **aspell (核心引擎)**: 运行时依赖
  - aspell 提供 `aspell` 和 `prezip-bin` 工具
  - 构建时需要这些工具将 .cwl 词表编译为 .rws 二进制字典文件
  - aspell 当前**未发布**到 ohpcd 制品仓
  - aspell 已有归档目录 `archives/a/aspell/0.60.8/` 但无 conanfile.py
  - **声明**: aspell 作为运行时依赖在 manifest.yaml 中记录

## 构建过程
1. `configure` 脚本运行 `aspell dump config dict-dir` 和 `aspell dump config data-dir` 来查找安装路径
2. `make` 使用 `prezip-bin` 解压 .cwl 文件，然后用 `aspell create master` 编译为 .rws
3. `make install` 将 .rws, .multi, .dat 文件安装到字典和数据目录

### OHOS 适配
- 修复 configure 脚本 shebang: `#!/bin/sh` → `#!/data/service/hnp/bin/bash`
- 设置 `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu`

### 构建回退策略
由于 aspell 核心引擎（提供 `aspell` 和 `prezip-bin`）尚未发布到 ohpcd 制品仓，
构建时这些工具不可用。因此：
1. 尝试 autotools 构建（configure + make）
2. 如果失败（aspell/prezip-bin 不可用），回退到直接安装原始数据文件
3. 原始 .cwl 文件可以被 aspell 在运行时直接使用（aspell 会在运行时解压）

## 测试方法
- aspell-en 源码包**没有** test/ 目录或 `make check` 目标
- 上游验证方式：安装字典后运行 `aspell --lang=en` 进行拼写检查
- test_package 验证内容：
  1. en.dat 存在且非空
  2. en.dat 包含 'name en'
  3. .cwl 词表文件存在
  4. en.multi 多文件配置存在
  5. .dat 文件包含英文特定内容
  6. en.dat 包含字符集声明
  7. 字典数据文件类型完整
  8. 总数据文件数 >= 5

## 关键决策
1. `package_type = 'header-library'` — 纯数据包，无编译二进制
2. `settings = 'os', 'arch'` — 不需要 compiler/build_type（纯字典数据）
3. 构建回退：如果 aspell 工具不可用，直接安装原始 .cwl/.dat/.multi/.alias 文件
4. 包结构：`res/dict/` 存放 .cwl/.multi/.alias，`res/data/` 存放 .dat
5. aspell 作为运行时依赖声明（尚未发布到制品仓）
