# autojump 22.5.3 适配笔记

## 编译环境
- 构建系统: custom（Python+bash脚本项目）
- 编译日期: 2026-06-01
- 编译器: N/A（纯脚本，无C编译）
- 状态: built

## 编译步骤

autojump 是纯 Python/bash 脚本项目，不涉及 C 编译，无需 configure/make。

1. 下载源码: `autojump-release-v22.5.3.tar.gz` (GitHub)
2. 解压到工作目录
3. 安装到 staging 目录（DESTDIR 模式）:
   ```
   python3 install.py -d $TEST_PREFIX -p usr/local -z usr/local/share/zsh/site-functions --force
   ```
4. 修正路径引用: autojump.sh 中 `/usr/local` 替换为 `$DEFAULT_PREFIX`
5. 重组 staging 目录结构，从 `$TEST_PREFIX/usr/local/` 移动到 `$TEST_PREFIX/$DEFAULT_PREFIX/`
6. 将 `/etc/profile.d/autojump.sh` 也移入 prefix 目录下 (`$DEFAULT_PREFIX/etc/profile.d/`)
7. 验证 autojump 可用
8. 打包预编译包

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | install.py 下载 SSL 错误 | 鸿蒙环境 urllib SSL 证书不匹配 | 手动用 curl 下载 tarball |
| 2 | install.py os.path.join 覆盖 destdir | Python os.path.join 绝对路径会覆盖前序路径 | 使用相对 prefix (`usr/local`) 代替绝对路径 (`$DEFAULT_PREFIX`) |
| 3 | autojump.sh 硬编码 `/usr/local` | 上游默认系统安装路径 | 修改为 `$DEFAULT_PREFIX` (`/storage/Users/currentUser/usr/local`) |
| 4 | install.py shell/root 检查 | install.py 要求 root 权限和特定 shell | 使用 `--force` 绕过 |
| 5 | /etc/profile.d 文件不在 prefix 下 | install.py 将 profile.d 直接放在 destdir/etc/ | 手动移入 `$DEFAULT_PREFIX/etc/profile.d/` |

## 源码修改

- `bin/autojump.sh`: 将 `/usr/local/share/autojump` 替换为 `/storage/Users/currentUser/usr/local/share/autojump`
- 无其他源码修改，无需 ELF 签名（纯脚本项目）

## 依赖版本

- Python 3 (系统自带)
- bash/sh (系统自带)

## 验证结果

```bash
$ autojump --version
autojump v22.5.3
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| autojump-22.5.3-ohos-aarch64.tar.gz | ~309K | 预编译包 |

## 注意事项

- autojump 是纯脚本项目，不需要 ELF 签名
- 安装后需要在 shell 配置文件中 source autojump.sh 才能使用
- autojump.sh 中路径已修改为鸿蒙平台 DEFAULT_PREFIX
- DESTDIR 模式下 install.py 的 -p 参数必须使用相对路径（usr/local），不能使用绝对路径（因为 os.path.join 行为）
---

**编译结束**: 2026-06-01 23:30
**最终状态**: built
