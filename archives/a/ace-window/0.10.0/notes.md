# ace-window 0.10.0 — 适配笔记

## 软件信息

- **名称**: ace-window
- **版本**: 0.10.0
- **描述**: GNU Emacs package for quickly switching windows
- **许可证**: GPL-3.0-or-later
- **源码**: https://github.com/abo-abo/ace-window/archive/refs/tags/0.10.0.tar.gz
- **SHA256**: b05403890ad4891f2cb4827b9bfa49660504c62dae951152d25a3b1290e21213
- **构建系统**: Makefile (Emacs Lisp byte-compilation)

## 构建特征

ace-window 是一个纯 Emacs Lisp 包，与 ace-link 同属作者 abo-abo 的 Emacs 扩展系列。不需要 C/C++ 编译：
- `ace-window.el` — 主源文件，约 1000 行 Emacs Lisp 代码
- `Makefile` — 仅用于 Emacs byte-compilation (`emacs -batch -l test/make-compile.el`)
- `test/` — 测试目录
- 依赖: `emacs`, `avy` (Emacs Lisp 包, 版本 >= 0.5.0)

安装方式：将 `.el` 文件复制到 Emacs site-lisp 目录即可。

## 适配过程

### 下载
- 从 GitHub 下载 0.10.0 标签归档 (tags/0.10.0.tar.gz)
- SHA256 校验: b05403890ad4891f2cb4827b9bfa49660504c62dae951152d25a3b1290e21213

### 安装
- 纯 Emacs Lisp 包，无需 C/C++ 编译
- `build()`: 无操作（无需编译）
- `package()`: 复制 `*.el` 文件到 `lib/site-lisp/` 目录
- 使用 DESTDIR 隔离安装，不污染系统目录

### 依赖
- 运行时依赖: `emacs` (Emacs 编辑器), `avy` (Emacs Lisp 包)
- `requirements()` 中已声明: `avy/0.5.0`（已在 ohpcd 制品仓发布，本机 conan 缓存已有）
- emacs 本身尚未完成 OHOS 适配，待完成后在 `requirements()` 中补充: `emacs/29.4`

### 测试
- test_package: 验证 ace-window.el 文件存在于安装目录
- test_results: explicit (1/1 passed)
- R34 受限：因 emacs 尚未完成 OHOS 适配，当前测试仅做文件完整性验证（存在性 + 非空性 + `(provide 'ace-window)` 内容特征 + `(defun ace-window` 函数定义标记），**未实际调用 ace-window 的任何 Emacs Lisp API**（如 `ace-window` 函数等）。
  - **解除条件**：待 emacs 完成 OHOS 移植并发布到制品仓后，在 test_ace_window.py 中通过 `emacs -batch -l ace-window.el --eval "(ace-window)"` 实际加载并调用 ace-window API
  - **预期时间**：emacs 移植为独立大工程，保守估计 3~6 个月，不在本 PR 范围内
  - **当前状态**：文件完整性验证可确保配方正确安装，不会因缺失 `.el` 文件或内容损毁而漏报

## 无补丁

ace-window 是纯 Emacs Lisp 项目，无需源码修改。

## 关键决策

1. **conanfile.py 基于 ace-link 0.5.0 模板**：ace-window 与 ace-link 同属作者 abo-abo 的纯 Emacs Lisp 包，构建方式完全一致（仅复制 .el 文件）
2. **settings 设计**：ace-window 为纯 Emacs Lisp 包，`settings = "os", "arch"` 保留 os/arch 是为了 Conan 包管理兼容性，无需 compiler/build_type 变体
3. **test_package 简化**：不使用 CMake，直接用 Python 检查文件存在性
4. **cpp_info**：设置 `includedirs = ["lib/site-lisp"]` 以便其他 Elisp 包引用

---

**适配日期**: 2026-08-06
**最终状态**: built
