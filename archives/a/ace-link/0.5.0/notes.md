# ace-link 0.5.0 — 适配笔记

## 软件信息

- **名称**: ace-link
- **版本**: 0.5.0
- **描述**: GNU Emacs package for selecting a link to jump to
- **许可证**: GPL-3.0-or-later
- **源码**: https://github.com/abo-abo/ace-link/archive/refs/tags/0.5.0.tar.gz
- **SHA256**: 340f74e02bdf4f3ef4761b8b2a5a9378c0ba07d0164e0ed2b695b94c0df99c7d
- **构建系统**: Makefile (Emacs Lisp byte-compilation)

## 构建特征

ace-link 是一个纯 Emacs Lisp 包，类似 cask。它不需要 C/C++ 编译：
- `ace-link.el` — 主源文件，约 1100 行 Emacs Lisp 代码
- `Makefile` — 仅用于 Emacs byte-compilation (`emacs -batch -l test/make-compile.el`)
- `test/` — 测试目录
- 依赖: `emacs`, `avy` (Emacs Lisp 包, 版本 >= 0.4.0)

安装方式：将 `.el` 文件复制到 Emacs site-lisp 目录即可。

## 适配过程

### 下载
- 从 GitHub 下载 0.5.0 标签归档 (tags/0.5.0.tar.gz)
- SHA256 校验: 340f74e02bdf4f3ef4761b8b2a5a9378c0ba07d0164e0ed2b695b94c0df99c7d

### 安装
- 纯 Emacs Lisp 包，无需 C/C++ 编译
- `build()`: 无操作（无需编译）
- `package()`: 复制 `*.el` 文件到 `lib/site-lisp/` 目录
- 使用 DESTDIR 隔离安装，不污染系统目录

### 依赖
- 运行时依赖: `emacs` (Emacs 编辑器), `avy` (Emacs Lisp 包)
- `requirements()` 中已声明: `avy/0.5.0`（PR #3384 已合并，通过 ohpcd 制品仓可用）
- emacs 本身尚未完成 OHOS 适配，待完成后在 `requirements()` 中补充: `emacs/29.4`

### 测试
- test_package: 验证 ace-link.el 文件存在于安装目录
- test_results: explicit (1/1 passed)
- R34 受限：因 emacs 尚未完成 OHOS 适配，当前测试仅做文件完整性验证（存在性 + 非空性 + `(provide 'ace-link)` 内容特征），**未实际调用 ace-link 的任何 Emacs Lisp API**（如 `avy--ace-link-jump` 等）。
  - **解除条件**：待 emacs 完成 OHOS 移植并发布到制品仓后，在 test_ace_link.py 中通过 `emacs -batch -l ace-link.el --eval "(ace-link-avy-setup)"` 实际加载并调用 ace-link API
  - **预期时间**：emacs 移植为独立大工程（见下方关键决策第4条），保守估计 3~6 个月，不在本 PR 范围内
  - **当前状态**：文件完整性验证可确保配方正确安装，不会因缺失 `.el` 文件或内容损毁而漏报

## 无补丁

ace-link 是纯 Emacs Lisp 项目，无需源码修改。

## 关键决策

1. **conanfile.py 基于 makefile 模板**：虽然构建系统是 Makefile，但实际只需复制 .el 文件，无编译步骤
2. **settings 设计**：ace-link 为纯 Emacs Lisp 包，`settings = "os", "arch"` 保留 os/arch 是为了 Conan 包管理兼容性，无需 compiler/build_type 变体
3. **test_package 简化**：不使用 CMake，直接用 Python 检查文件存在性
4. **cpp_info**：设置 `includedirs = ["lib/site-lisp"]` 以便其他 Elisp 包引用

---

**适配日期**: 2026-07-14
**最终状态**: built
