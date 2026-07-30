# smex 3.0 适配笔记

## 编译环境
- 构建系统: 无（纯 Emacs Lisp 包）
- 编译日期: 2026-07-27
- 包类型: Emacs Lisp 脚本（无可执行二进制）
- 状态: built

## 依赖
- 无 Conan 依赖
- 运行时依赖 Emacs 编辑器（由用户提供，非 Conan 包）

## 适配步骤
```bash
# smex 无构建系统，仅需复制 smex.el 到安装目录
# Conan recipe 的 package() 方法直接复制文件：
#   smex.el → share/emacs/site-lisp/smex.el
```

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | smex 无构建系统 | 上游仅提供 .el 文件 | conanfile.py 的 build() 为空，package() 直接复制 |
| 2 | 包与平台无关 | 纯 Lisp 文件不依赖 OS/arch | package_id() 使用 self.info.clear() |
| 3 | 无法运行时测试 | CI 环境无 Emacs | test_package 改为静态检查 smex.el 内容 |
| 4 | 无 commands.json | smex 不提供可执行文件 | R38 不适用，不创建 commands.json |

## 源码下载
- 官方源: https://github.com/nonsequitur/smex/archive/refs/tags/3.0.tar.gz
- SHA256: 96eb68ac3301d0986195a29ea03d4dad1a5f81647cb097a78de59c1cc6d78e58
- 大小: 6580 字节
- 归档内容: smex-3.0/README.markdown, smex-3.0/smex.el

## 验证结果
- smex.el 存在性检查 ✅
- 版本字符串 "Version: 3.0" 匹配 ✅
- 函数定义 "(defun smex " 存在 ✅
- 纯脚本包，无 NEEDED 依赖

## 注意事项
- smex 3.0 上游最后更新于 2015-12-13，已停更
- 运行时需要 Emacs 24+ 已安装
- 在 Emacs 中通过 (require 'smex) (smex-initialize) 加载
