# aurpublish 20231227.3b978be 适配笔记

## 编译环境
- 构建系统: makefile (纯 bash 脚本项目，sed 渲染)
- 编译日期: 2026-09-01
- 编译器: 无（纯 bash 脚本，无任何编译产物）
- 状态: published

## 软件说明
aurpublish 是 Arch User Repository 的 PKGBUILD 管理框架：基于 git subtree
将仓库中的软件包子目录推送到 AUR。上游无任何 tag/release，版本号采用
`日期.短SHA` 约定（20231227.3b978be，先例：archives/a/agedu/20211129.8cd63c5）。

## 编译步骤

上游 Makefile 极简：`%: %.in` 规则用 sed 将 `aurpublish.in` 中的
`@HOOKSDIR@` 占位符替换为 `$(HOOKSDIR)`（默认 `$(PREFIX)/share/aurpublish`）
生成 `aurpublish` 脚本；`install` 目标安装 bin/aurpublish、share/aurpublish/*.hook
（3 个 git hooks）、zsh/bash 补全、man 页。

实际执行（Step 2 手动构建）：
```bash
cd $BUILD_SRC_DIR
make aurpublish          # sed 渲染生成 aurpublish 脚本（@HOOKSDIR@ -> /usr/local/share/aurpublish）
# staging 安装（MANS="" 跳过 man 页，见问题#1）
make install DESTDIR=$TEST_PREFIX MANS=""
```

**关键适配决策 — HOOKSDIR 运行时解析**：上游将 HOOKSDIR 以构建期绝对路径
硬编码进脚本（如 `/usr/local/share/aurpublish`），conan 包安装位置可变
（package cache），硬编码路径必然失效。适配：`@HOOKSDIR@` 替换值改为
`$(dirname -- "$(readlink -f -- "$0")")/../share/aurpublish`（相对脚本自身
位置运行时解析），包内 `bin/../share/aurpublish` 布局下 hooks 始终可寻址，
包可重定位。该行为在本地验证：临时 git 仓库中 `aurpublish setup` 成功安装
3 个 hooks 符号链接，指向包内 hooks。

conanfile.py 的 build() 用 Python 原生字符串替换执行同样的 sed 语义（等价于
上游 `make aurpublish` 的 edit 规则），不依赖 shell 环境变量（R33）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `make all`/`make man` 失败 | man 页由 a2x (asciidoc) 生成，环境无 a2x | 跳过 man 页：staging 用 `make install MANS=""`；conanfile 不安装 man。核心产物 bin/aurpublish + share/aurpublish/*.hook + 补全不受影响 |
| 2 | `install -dm755` 在 HMDFS 上失败 | 平台限制：install -d 创建目录后 chmod 报 No such file or directory，目录创建不完整，后续 *.hook 复制错位成文件 | conanfile package() 改用 Python 原生 os.makedirs/copy（conan.tools.files.copy），规避平台 install 命令缺陷 |
| 3 | `./aurpublish` 直接执行报 bad interpreter | 脚本 shebang 为 `#!/bin/bash`，OHOS 无 /bin/bash（bash 实际在 /data/service/hnp/bin/bash） | 保留上游 shebang 不做 patch（标准 Linux/CI 环境均有 /bin/bash，先例 abcde 2.9.3 同样处理）；本地与 test_package 中用 `bash <script>` 方式调用 |
| 4 | `make install` 触发 pkg-config 查询 bash-completion 失败 | 环境无 bash-completion.pc | 非致命：Makefile 回退默认路径 /usr/share/bash-completion/completions；conanfile 直接安装到包内相对路径，不涉及 |
| 5 | 上游无 make check/test 目标 | 纯脚本项目，上游无测试套件 | test_package 自建真实冒烟测试（见验证结果），notes 记录 |
| 6 | W3 本地 CI 模拟 L0p 门禁失败：settings 缺 compiler/build_type | CI 规范（build_and_test.sh L0p）强制配方 settings 四项齐全（os/compiler/build_type/arch），早期 abcde 2.9.3 先例的 "os","arch" 两项写法已过时 | conanfile.py 改为 `settings = "os", "compiler", "build_type", "arch"`（W1 同步最新 main 后以当前规范为准） |
| 7 | finish Step3 G0 干净构建验证失败（configure exit 127），非阻塞 | clean-verify 框架假定 autotools 项目、尝试运行 ./configure；aurpublish 无 configure 脚本（纯 Makefile + sed 渲染），属框架对脚本类项目的误判 | 非阻塞警告。真实可复现性已由 conan-verify G2（conan create 干净构建）+ W3 本地 CI 模拟（L0 全过）覆盖验证 |
| 8 | W3 的 L2 冒烟 `aurpublish --version/--help` 直接执行失败（非阻塞 skip） | W3 L2 直接执行包内二进制（依赖 /bin/bash shebang），OHOS 无 /bin/bash；且上游无 --version 选项 | 非阻塞。test_package（bash 调用方式）的 --help/setup 真实冒烟全过，L1 执行证据 + L1e 破坏性反向验证均 PASS |

## 源码修改

无补丁（patches_applied 为空）。@HOOKSDIR@ 替换值的变化属构建参数注入
（上游 Makefile 本就通过 sed 变量完成渲染），未修改任何源文件。

## 依赖版本

- 运行时：bash（>=4，本机 5.3.0）、git（subtree 子命令）。无任何 Conan 依赖。
- 构建时：仅 sed/chmod（由 conanfile Python 原生实现替代）。

## 验证结果

```bash
# 1) --help 冒烟（真实执行安装后的脚本）
bash $TEST_PREFIX/usr/local/bin/aurpublish --help
# 输出完整 usage（Usage: aurpublish ... / Push a subtree to the AUR ...），exit 0

# 2) setup 子命令（临时 git 仓库，验证 HOOKSDIR 运行时解析）
cd $TMPDIR/aurpublish-setup-test && git init && git commit (初始化)
bash $TEST_PREFIX/usr/local/bin/aurpublish setup
# 输出 "Adding commit hooks..." + 3 个 "-> *.hook"，exit 0
# .git/hooks/ 下 pre-commit、post-commit、prepare-commit-msg 符号链接
# 均指向包内 share/aurpublish/*.hook

# 3) test_package（conan create 自动运行）
# bash test_aurpublish.sh <bin_dir>: 语法检查 + --help + setup/hooks，全过
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/aurpublish | 渲染后的主脚本（755） |
| share/aurpublish/{pre-commit,post-commit,prepare-commit-msg}.hook | git hooks（755，`setup` 子命令安装为符号链接） |
| share/zsh/site-functions/_aurpublish | zsh 补全 |
| share/bash-completion/completions/aurpublish | bash 补全 |
| （man 页） | 跳过：无 a2x/asciidoc 工具链（问题#1） |

## 注意事项

- OHOS 本机无 /bin/bash：直接执行脚本会 bad interpreter，用 `bash aurpublish ...`
  调用或部署到含 /bin/bash 的环境（同 abcde 2.9.3 先例）。
- `aurpublish setup` 依赖 git（含 subtree）；`pre-commit.hook` 调用 makepkg
  （Arch 生态工具），OHOS 上该 hook 的 .SRCINFO 自动生成功能不可用，仅作
  脚本框架管理用途时无影响。
- 版本号 20231227.3b978be 为 日期.短SHA 约定（上游 commit
  3b978be48dde74eae86dff49d55ae29bb4a217ec，2023-12-27 之后无新提交）。
---

**编译结束**: 2026-09-01 15:10
**最终状态**: published
