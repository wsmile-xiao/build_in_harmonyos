# avy 0.5.0.1 — 适配笔记

## 软件信息

- **名称**: avy
- **版本**: 0.5.0.1（recipe 递增后缀，上游源码标签仍为 0.5.0，制品仓 R37 不支持同版本多 revision）
- **描述**: GNU Emacs Lisp package for jumping to tree-based visual selections
- **许可证**: GPL-3.0-or-later
- **源码**: https://github.com/abo-abo/avy/archive/refs/tags/0.5.0.tar.gz
- **SHA256**: 8106ca3652ec8198fa88c17082f885b06ffd079dd4aac12cdc4f1c74942d2894
- **构建系统**: Makefile (Emacs Lisp byte-compilation)
- **主页**: https://github.com/abo-abo/avy

## 构建特征

avy 是一个纯 Emacs Lisp 包。它不需要 C/C++ 编译：

- `avy.el` — 主源文件，约 2143 行 Emacs Lisp 代码，92 个 defun
- `avy-test.el` — Emacs ert 测试文件
- `Makefile` — 仅用于 Emacs byte-compilation 和 ert 测试
- `doc/Changelog.org` — 变更日志
- `targets/` — Emacs 初始化辅助文件

安装方式：将 `.el` 文件复制到 Emacs site-lisp 目录即可。

## 依赖

- **运行时依赖**: `emacs` (Emacs 编辑器，尚未完成 OHOS 适配)
- `requirements()` 中暂未声明（emacs 为运行时依赖，非 Conan 构建依赖）
- 待 emacs 完成 OHOS 适配后，可在 `requirements()` 中补充: `emacs/29.4`

## 适配过程

### 下载与校验
- 从 GitHub 下载 0.5.0 标签归档 (tags/0.5.0.tar.gz)
- SHA256 校验通过: `8106ca3652ec8198fa88c17082f885b06ffd079dd4aac12cdc4f1c74942d2894`

### conandata.yml 修复
- 原版使用 `source:` 键（Conan 1.x 格式），已改为 `sources:` 键（Conan 2.29 格式）
- 版本号 `"0.5.0.1"` 作为子键，包含 `url` 和 `sha256`（源码标签仍为 0.5.0）

### conanfile.py 设计
- `package_type = "header-library"` — 纯 Elisp 内容包，无编译产物
- `settings = "os", "arch"` — 保留平台/架构兼容性，无需 compiler/build_type
- `source()`: 使用 `self.conan_data["sources"][str(self.version)]` + `get(..., strip_root=True)`
- `build()`: 无操作（纯 Elisp，无需 C/C++ 编译）
- `package()`: 复制 `*.el` 文件到 `lib/site-lisp/` 目录
- `package_info()`: `includedirs = ["lib/site-lisp"]`, `libdirs = []`, `bindirs = []`

### 测试方法 (R34)
- test_package 使用 Python 脚本验证 avy.el 内容的实质性
- 8 项断言：
  1. avy.el 存在且非空
  2. avy.el 包含 `(provide 'avy)` — Emacs Lisp provide 形式
  3. avy.el 包含 `defun` — 确认定义了函数
  4. avy-test.el 存在且包含 ert-deftest
  5. avy.el 的 defun 数量 > 10
  6. avy.el 包含 `avy-jump` — 关键入口函数
  7. avy.el 包含 `avy-process` — 核心处理函数
  8. avy.el 包含 `avy-read` — 核心读取函数

## 无补丁

avy 是纯 Emacs Lisp 项目，无需源码修改。

## 关键决策

1. **conandata.yml 使用 `sources:` 键** — 符合 Conan 2.29 格式
2. **package_type = header-library** — 纯 Elisp 包，无二进制产物
3. **settings 仅 os/arch** — 不需要 compiler/build_type 变体
4. **test_package 实质性验证** — 验证 avy.el 内容特征，满足 R34
5. **cpp_info includedirs** — 设置 `["lib/site-lisp"]` 以便下游 Elisp 包引用

---

**适配日期**: 2026-08-08
**最终状态**: built
