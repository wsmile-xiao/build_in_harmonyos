# autojump 22.5.3 适配笔记

## 编译环境
- 构建系统: custom（Python+bash 脚本项目，Conan 打包）
- 编译日期: 2026-09-17（conan 配方适配；首次手动适配 2026-06-01）
- 编译器: N/A（纯脚本，无 C 编译）
- 状态: built

## 背景说明

autojump 是纯 Python/bash 脚本项目，不涉及 C 编译。2026-06 完成手动适配归档；
本目录补充 Conan 配方（conanfile.py + conandata.yml + test_package/），
使包可通过 `conan install autojump/22.5.3` 消费，脚本纳入 Conan 依赖链管理。

## Conan 配方构建步骤（conan create）

1. `source()`: 从 GitHub 官方源下载 release-v22.5.3.tar.gz（CI 自动加镜像回退）
2. `build()`: 应用补丁后以 DESTDIR 模式安装到 build 目录 staging:
   `python3 install.py -d <build>/staging -p usr/local -z <build>/staging/usr/share/zsh/site-functions --force`
3. `package()`: 拷贝 staging/usr/local（bin、share、man）、staging/etc/profile.d
   （autojump.sh shell 集成）、zsh 补全到 package 目录
4. `package_info()`: bindirs=usr/local/bin；runenv 定义 `AUTOJUMP_SHARE_DIR`
   指向消费端本机的包内 share/autojump 目录（消费端求值，非构建机路径）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | install.py 下载 SSL 错误 | 鸿蒙环境 urllib SSL 证书不匹配 | conandata.yml 声明官方源 URL，由 conan get() 下载 |
| 2 | install.py os.path.join 覆盖 destdir | Python os.path.join 绝对路径会覆盖前序路径 | `-p` 参数必须用相对路径 `usr/local` |
| 3 | autojump.sh 硬编码 `/usr/local/share/autojump` | 上游默认系统安装路径 | 补丁 0001 增加 `AUTOJUMP_SHARE_DIR` 环境变量检查分支，配合配方 runenv 注入；不硬编码任何构建机路径 |
| 4 | install.py shell/root 检查 | install.py 要求 root 权限和特定 shell | 使用 `--force` 绕过 |
| 5 | shebang `#!/usr/bin/env python` | OpenHarmony 无 `python` 命令名 | 补丁 0002 改为 `python3` |
| 6 | autojump.sh 内嵌 Conan 缓存绝对路径 | 早期版本把 `self.package_folder`（构建机缓存路径）写入脚本，部署后失效 | 改为 AUTOJUMP_SHARE_DIR 运行时环境变量方案（AI 检视 High 意见修复） |

## 源码修改（patches/）

- `0001-bin-autojump.sh.patch`: autojump.sh 增加 AUTOJUMP_SHARE_DIR 检查分支（portability）
- `0002-bin-autojump-shebang.patch`: bin/autojump shebang python → python3（portability）

## 依赖版本

- Python 3（系统自带）
- bash/sh（系统自带）

## 验证结果

```bash
$ autojump --version
autojump v22.5.3
```

test_package: conanrun 环境下执行 `autojump --version` 冒烟验证。

## 上游测试情况（R51 申报）

- 上游仓库有 tests/ 目录（autojump_match_test.py、autojump_utils_test.py），
  运行依赖 pytest + tox + python2/3 双版本矩阵，且依赖 X11 环境的 DISPLAY。
- CI 环境无 pytest/tox，上游测试未在 CI 中运行；test_package 冒烟测试通过。
- 上游 Makefile 的 `test` 目标同样依赖 tox。

## 注意事项

- autojump 是纯脚本项目，不需要 ELF 签名
- 安装后需要在 shell 配置文件中 source autojump.sh 并激活 conanrun 环境变量
  （或手工 export AUTOJUMP_SHARE_DIR）才能使用 shell 集成
- DESTDIR 模式下 install.py 的 `-p` 参数必须使用相对路径（os.path.join 行为）

---

**编译结束**: 2026-09-17
**最终状态**: built
