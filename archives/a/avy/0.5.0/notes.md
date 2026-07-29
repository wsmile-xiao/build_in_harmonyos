# avy 0.5.0 — 适配笔记

## 软件信息

- **名称**: avy
- **版本**: 0.5.0
- **描述**: GNU Emacs Lisp package for jumping to tree-based visual selections
- **许可证**: GPL-3.0-or-later
- **源码**: https://github.com/abo-abo/avy/archive/refs/tags/0.5.0.tar.gz
- **SHA256**: 8106ca3652ec8198fa88c17082f885b06ffd079dd4aac12cdc4f1c74942d2894
- **构建系统**: Makefile (Emacs Lisp byte-compilation)

## 构建特征

avy 是一个纯 Emacs Lisp 包，类似 ace-link。它不需要 C/C++ 编译：
- `avy.el` — 主源文件，约 2800 行 Emacs Lisp 代码
- `avy-pkg.el` — 包元数据文件
- `Makefile` — 仅用于 Emacs byte-compilation (`make`)
- `test/avy-tests.el` — 测试文件
- 依赖: `emacs` (运行时依赖)

安装方式：将 `.el` 文件复制到 Emacs site-lisp 目录即可。

## 适配过程

### 下载
- 从 GitHub 下载 0.5.0 标签归档 (tags/0.5.0.tar.gz)
- SHA256 校验: 8106ca3652ec8198fa88c17082f885b06ffd079dd4aac12cdc4f1c74942d2894

### 安装
- 纯 Emacs Lisp 包，无需 C/C++ 编译
- `build()`: 无操作（无需编译）
- `package()`: 复制 `*.el` 文件到 `lib/site-lisp/` 目录
- 使用 DESTDIR 隔离安装，不污染系统目录

### 依赖
- 运行时依赖: `emacs` (Emacs 编辑器)
- `requirements()` 中暂未声明（emacs 为运行时依赖，非 Conan 构建依赖）
- emacs 本身尚未完成 OHOS 适配，现仅通过 manifest.yaml 文档记录依赖关系
- 待 emacs 完成 OHOS 适配后，可在 `requirements()` 中补充: `emacs/29.4`

### 测试
- test_package: 验证 avy.el 文件存在于安装目录
- test_results: explicit (1/1 passed)
- R34 受限：因 emacs 尚未完成 OHOS 适配，无法通过 `emacs -batch` 调用 avy 的实际 API。
  当前测试降级为文件完整性验证（存在性、非空性、内容特征），待 emacs 适配完成后补充实质性 API 测试。

## 无补丁

avy 是纯 Emacs Lisp 项目，无需源码修改。

## 关键决策

1. **conanfile.py 基于 makefile 模板**：虽然构建系统是 Makefile，但实际只需复制 .el 文件，无编译步骤
2. **settings 设计**：avy 为纯 Emacs Lisp 包，`settings = "os", "arch"` 保留 os/arch 是为了 Conan 包管理兼容性，无需 compiler/build_type 变体
3. **test_package 简化**：不使用 CMake，直接用 Python 检查文件存在性
4. **cpp_info**：设置 `includedirs = ["lib/site-lisp"]` 以便其他 Elisp 包引用（如 ace-link 依赖 avy）
5. **R32 合规**：settings 仅保留 "os" 和 "arch"，符合规范要求
6. **R34 合规**：test_package 同时验证文件存在性、非空性、以及内容特征 `(provide 'avy)`

---

**适配日期**: 2026-07-28
**最终状态**: built
