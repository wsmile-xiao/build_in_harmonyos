# imenu-list 0.9 适配笔记

## 上游与形态

- 上游 `bmag/imenu-list` v0.9：GNU Emacs 包，把当前缓冲区的 imenu 条目
  显示在独立缓冲区 "*Ilist*"（可折叠大纲、随缓冲区实时更新，集成
  hideshow/eglot 可选联动）。**单文件 Emacs Lisp 包**：`imenu-list.el`
  （686 行，Package-Requires: cl-lib 0.5）+ LICENSE（GPL v3）+
  README.md + images/×2。**无任何 C/C++ 源码、无构建系统、无测试套件**
  （tar 清单内无 -tests.el / ERT 文件）。
- 任务平台标签为 C++，实为 Emacs Lisp 包，按已合入的 web-mode 17.3.20
  单文件 elisp 先例适配（字节编译 + 消费者功能断言），如需确认可与小
  助手核对。
- **tag 名带 v 前缀**：上游 tags 为 v0.1~v0.9（git ls-remote 实测），
  裸 "0.9" 归档 URL 返回 404；conandata 写
  `https://github.com/bmag/imenu-list/archive/refs/tags/v0.9.tar.gz`，
  sha256=847d935f...c0961 双源实测（github.com 归档 URL 与
  codeload.github.com 字节一致）。

## OHOS 适配（web-mode 先例范式）

- `requires("emacs/29.1")`——Emacs 既是字节编译工具链也是运行期宿主
  （ohpcd 制品仓已发布，传递依赖 ncurses/6.5）；
- `build()`：防漂移校验（imenu-list.el 在位、686 行落在 620–750 区间）
  → `emacs -Q --batch -f batch-byte-compile`（经 conanbuild env，emacs
  二进制取自依赖包 `bin/emacs`）→ 断言 imenu-list.elc 产出且非空；
- 字节编译对 GNU Emacs 29.1 零 Error，仅上游固有非致命警告：
  `point-at-bol` 废弃提示（613 行，上游兼容旧版写法）、
  `hs-toggle-hiding`/`eglot--lsp-position-to-point`/`eglot-managed-p`
  未定义提示（可选运行时依赖，加载相应模式后可用），无需 patch；
- `package()`：.el/.elc 装到 `share/emacs/site-lisp/imenu-list-0.9/`，
  README 装 `share/doc/imenu-list/`，LICENSE 装 `licenses/`；
- `package_info()`：定义 `IMENU_LIST_LISPDIR`（buildenv+runenv）并前置
  `EMACSLOADPATH`（web-mode 同款，消费者 `(require 'imenu-list)` 直接
  可用）；
- `package_id()` 清空（纯 Elisp 无编译产物分裂维度，web-mode/inheritenv
  同款）。

## 测试口径

上游 v0.9 **无测试套件**（发行包内无任何 ERT/测试文件，R51 清点结论），
按 inform-mode 先例以内容级+功能级消费者探针代替：

1. `test_imenu_list.sh`：校验 IMENU_LIST_LISPDIR 下 .el/.elc 双文件
   在位、EMACSLOADPATH 含安装目录（消费侧环境约定）；
2. `test_imenu_list.el`（8 断言）：`(require 'imenu-list)` 加载成功
   （featurep）、`imenu-list-buffer-name` 默认 "*Ilist*"、
   `imenu-list-minor-mode` 已定义、batch 下 enable/disable 实测切换、
   `imenu-list-smart-toggle` 已定义、`imenu-list-position` 默认 'right、
   `imenu-list-size` 定制变量在位、版本头 "Version: 0.9"。

本机（HarmonyOS aarch64 真机）实测：字节编译 RC=0（elc 26545 字节）、
功能探针输出 `imenu-list functional assertions: 8/8 PASS`（batch 临时
缓冲区打印的 `couldn't create index` 为无 imenu 支持缓冲区的预期非致命
消息，不影响断言结果）。

## 依赖关系

- conan 依赖：emacs/29.1（ohpcd 已发布）
- 运行期 Emacs 侧依赖：cl-lib 0.5（Emacs 29 内置满足）；可选联动
  hideshow/eglot 不在打包范围（byte-compile 警告即源于此，属预期）
- 被依赖：无

## 参考

- GitHub: https://github.com/bmag/imenu-list
- MELPA: https://melpa.org/#/imenu-list

## 本地验证记录（2026-10-04，HarmonyOS PC aarch64 真机）

- `conan install --requires emacs/29.1 -pr ohos-aarch64 --build=missing`
  成功（package 2c84c7a3d4c52682ab17a0a48741ae0156075437）；
- emacs 29.1 须 source conanrun.sh 后经 `$EMACS` 调用（EMACSLOADPATH/
  EMACSDATA 等 env 由包的 package_info 提供，裸调报 charsets 错误）；
- `batch-byte-compile imenu-list.el`：RC=0，imenu-list.elc 26545 字节，
  0 Error / 4 Warning（point-at-bol 废弃 1 + 可选依赖未定义 3）；
- 功能探针：`imenu-list functional assertions: 8/8 PASS`。
