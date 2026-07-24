# tpm 1.3.3 适配笔记

> tpm = **tiny password manager**（`nmeum/tpm`），纯 POSIX shell 脚本，兼容 pass(1)，用 gpg2 加密存储密码。
> Alpine 参考包 `tpm-1.3.3-r4.apk` 的 `-r4` 是 Alpine 修订号，Conan 版本用上游版本 `1.3.3`。

## 编译环境
- 构建系统: makefile（纯 Makefile install-only，无 configure/cmake/meson）
- 编译日期: 2026-07-16
- 编译器: 不适用（纯 shell 脚本，无 C/C++ 编译）
- 状态: built（本地产出就绪；CI 编译验证待用户 push 后触发）

## 编译步骤

tpm 无编译过程。打包步骤（见 conanfile.py `package()`）：

```bash
# 1. 源码下载（Conan get，strip_root=True，解包后顶层即 tpm 脚本）
# 2. 安装 bin/tpm（等价于 Makefile 的 install -Dm755 tpm $(DESTDIR)$(BINDIR)/tpm）
# 3. 附带 LICENSE.txt / README.pod 到 share/doc/tpm/
```

Makefile 的完整 install 目标同时安装 man page（`tpm.1`，由 `pod2man` 从 `README.pod` 生成）。本配方**有意跳过 man page 生成**，理由见下方问题表 #2。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `conan-init` 把构建系统误判为 autotools，生成 library 骨架（Autotools/CMake test_package） | init-build 仅凭目录有 Makefile 时的默认猜测 | 手动改写：conanfile.py 用 makefile/application 模板；test_package 用 executable 模板（test.sh）替换 cmake 测试 |
| 2 | Makefile `all`/`install` 依赖 `pod2man`(perl) 生成 `tpm.1` | 鸿蒙 CI worker 未必有 perl/pod2man | 配方层跳过 man page 生成：`build()` 不跑 `make all`，`package()` 只装 `bin/tpm` + 文档。`tpm` 命令的可用性不依赖 man page |
| 3 | test_package 核心功能（insert/show）依赖 gpg2，鸿蒙制品仓无 gpg2 | `tpm insert/show` 调用 `gpg2` 加解密；真跑必然 "command not found" | **已解决**：test_package 提供 mock gpg2 stub（`mock_gpg2.sh`，可逆 base64 变换非真加密），让 insert→show 完整数据链路可在 CI 跑通。详见下方"测试增强"段。CLI 契约断言同时保留 |
| 4 | 运行时依赖 gpg2 (gnupg) 在鸿蒙制品仓未发布 | 仓库 `archives/g/gnupg/2.4.9/` 有手动编译记录但 status=failed（卡 libiconv），无完整 Conan 配方包，等于未发布 | **非阻塞**：tpm 是纯 shell 脚本，打包只产出 `bin/tpm`，不需要 gpg 参与编译。运行时 insert/show 才调 gpg2，待 gnupg 完整迁移（属路径 C 高难任务）后才有。够不上"无法打包"，不转 B-报告 |
| 5 | search-url 返回 6 个歧义源（tpm.io/savannah/waterlan，均属 tpm2-tools/DOS 工具） | "tpm" 短名高歧义 | 弃用 search-url 全部结果，用主 Agent 已验真的官方 GitHub tag tarball（Sören Tempel 版权 + tiny password manager 描述核验通过） |

## 源码修改

**无补丁**（patch 数 = 0）。

- `C:/Users/80422/tmp/builds/tpm-1.3.3.orig` 与 `.work` 对比：除 `.edit-tracker.json`/`.tarball-sha256` 元数据文件外，源码零差异。
- DESTDIR/PREFIX 在配方层 `package()` 处理，不动上游 Makefile。
- `patches/README.md` 记录零补丁理由。

## 依赖版本

| 依赖 | 类型 | 版本 | 制品仓状态 | 处理 |
|------|------|------|-----------|------|
| gpg2 (gnupg) | 运行时（二进制） | 2.4.9 上游 | ⚠️ 半成品未发布（仓库有 `archives/g/gnupg/2.4.9/` 手动编译记录，status=failed，卡在 libiconv 运行时链接；无完整 Conan 配方包，等于未发布）| 不阻塞打包（tpm 是纯 shell，打包不需要 gpg）；运行时可用性待 gnupg 完整迁移后才有 |
| pod2man | 构建期（host 工具，perl 模块） | — | N/A | 配方层跳过 man 生成，规避 |
| 编译期库依赖 | — | — | — | 无（registry 零依赖，resolve-deps 通过） |

## 验证结果（本地静态预检）

```bash
# conanfile.py 语法
$ py -c "import ast; ast.parse(open('conanfile.py').read())"  # OK

# conandata.yml 解析
$ py -c "import yaml; yaml.safe_load(open('conandata.yml'))"  # OK

# test_package 结构（executable 模板）
$ ls test_package/  # conanfile.py + test.sh + MANIFEST.yml
```

**真实编译验证待 CI**（本地为 Windows，无鸿蒙 conan create 环境；用户 push 后触发）。

## 测试用例对比表（积分赛硬指标）

> tpm 上游（nmeum/tpm）**无自动化测试套件**：上游 Makefile 只有 `all/install/uninstall/clean` 目标，无 `check`/`test`（见 test_package/MANIFEST.yml 的 `upstream_test_in_build: false`）。
> 因此"上游测试"列只能列出脚本对外暴露的可验证 CLI 契约，与 test_package 实际执行的断言逐条对比。

| # | 上游可验证项（CLI 契约 / 文档行为） | 上游是否自带测试 | 适配后 test_package 断言（test.sh） | 对齐状态 |
|---|--------------------------------------|:---:|--------------------------------------|:---:|
| 1 | `tpm` 脚本安装到 `$(BINDIR)/tpm` 后可被 PATH 找到（Makefile install 目标的语义） | ❌ 无 | `command -v tpm` 成功（tpm found on PATH） | ✅ |
| 2 | 无参调用打印 `USAGE: tpm COMMAND ENTRY`（脚本 `usage()` 函数，README.pod 文档） | ❌ 无 | 无参调用输出含 `USAGE: tpm` | ✅ |
| 3 | 无参调用退出码 = 1（脚本 `abort()` → `exit 1` 契约） | ❌ 无 | 断言退出码 `== 1` | ✅ |
| 4 | 未知子命令同样打印 USAGE 并退 1（参数分发逻辑） | ❌ 无 | `tpm boguscommand` 输出含 `USAGE: tpm` | ✅ |
| 5 | 未知子命令退出码 = 1 | ❌ 无 | 断言退出码 `== 1` | ✅ |
| 6 | `tpm insert ENTRY` 用 gpg2 加密写入 `~/.password-store/<entry>.gpg`（核心功能） | ❌ 无 | **已覆盖**：通过 mock gpg2 stub 驱动真实 insert，断言退出码 0 + 条目写到正确路径 + 文件不含明文 | ✅ |
| 7 | `tpm show ENTRY` 用 gpg2 解密读回密码（核心功能·往返） | ❌ 无 | **已覆盖**：断言 show 退出码 0 + 输出含原插入密码（insert→show 完整往返） | ✅ |
| 8 | show 不存在条目退 1 + 报错 / insert 重复条目退 1 / 空名走 USAGE（错误路径） | ❌ 无 | **已覆盖**：Group C 断言上述 3 条错误路径 | ✅ |

**说明**：
- 第 1-5 项（CLI 契约）由 test_package Group A 实质覆盖。
- 第 6-8 项（核心功能 insert/show + 错误路径）由 Group B/C 通过 mock gpg2 stub 实质覆盖——验证 tpm 读取密码、调用加密后端、写入正确存储路径、再解密读回的完整数据链路。
- **L1e 破坏性反验已本地双向验证**：(1) 移走 `bin/tpm` → 全部测试挂（证明 test 依赖 tpm）；(2) 移走 `mock_gpg2.sh` → Group B/C 挂而 Group A 仍过（证明核心功能测试真依赖 mock 后端，不是假测）。
- assertion_count = 15（setup: 1 + Group A: 4 + Group B: 5 + Group C: 5），与 test_package/MANIFEST.yml 一致。

## 测试增强：从 CLI 外围到核心功能覆盖

初版 test_package 只覆盖 CLI 契约（USAGE 行 + 退出码），核心功能 insert/show 因 gpg2 缺失为 0 覆盖，处于"形式合规但价值存疑"的灰色地带。本次增强引入 mock gpg2 stub，把核心功能覆盖度从 0% 提升到完整往返验证：

| 维度 | 初版 | 增强后 |
|------|------|--------|
| 安装可达性 | ✅ | ✅ |
| CLI 外围（USAGE/退出码）| ✅ 5 条 | ✅ 4 条（Group A）|
| **insert 加密写入** | ❌ 未测 | ✅ 3 条（Group B：退出码/路径/不含明文）|
| **show 解密读回** | ❌ 未测 | ✅ 2 条（Group B：退出码/密码往返一致）|
| **错误路径** | ❌ 未测 | ✅ 5 条（Group C：不存在/重复/空名）|
| **核心功能覆盖度** | **0%** | **~100%**（完整 insert→show 往返）|

**mock gpg2 设计**（`test_package/mock_gpg2.sh`）：
- 实现 tpm 实际调用的两种 gpg2 形态：`--encrypt --output <f>`（stdin→文件）和 `--decrypt <f>`（文件→stdout）
- 用 base64 可逆变换代替真加密（带 `MOCKGPG1` tag 防篡改）
- 忽略 tpm 传的其他 flag（`--quiet/--yes/--batch/--default-recipient-self`）
- **透明声明**：非真实加密，仅用于让 gpg2 依赖的代码路径可运行；仅存于 test_package/，不可当真实 gpg2 用
- 未知调用形态退 2（若 tpm 改了 gpg2 契约会立即暴露）

## 交付物

| 文件 | 说明 |
|------|------|
| archives/t/tpm/1.3.3/conanfile.py | Conan 配方（makefile/application 模板，CI 唯一输入） |
| archives/t/tpm/1.3.3/conandata.yml | 源码 URL + 真实 SHA256 + patches 声明 |
| archives/t/tpm/1.3.3/test_package/conanfile.py | executable 测试（依赖被测包，调 test.sh） |
| archives/t/tpm/1.3.3/test_package/test.sh | 调用 `tpm` 断言 USAGE + 退出码 |
| archives/t/tpm/1.3.3/test_package/MANIFEST.yml | 上游测试声明（上游无 test 目标） |
| archives/t/tpm/1.3.3/manifest.yaml | 版本级交叉校验元数据 |
| archives/t/tpm/1.3.3/notes.md | 本笔记 |
| archives/t/tpm/1.3.3/patches/README.md | 零补丁说明 |
| archives/t/tpm/commands.json | 工具命令声明（R38，软件级） |
| archives/t/tpm/README.md | 软件级说明 |
| archives/t/tpm/manifest.yaml | 软件级元数据 |

## 注意事项

- **运行时 gpg 未发布**：tpm 装上鸿蒙后，真实使用需 `gpg2`（insert/show 都靠 gpg 加解密）。仓库有 `archives/g/gnupg/2.4.9/` 手动编译记录但 status=failed（卡 libiconv），无完整 Conan 配方包，等于未发布。运行时可用性待 gnupg 完整迁移（路径 C 高难任务）后才有。这是运行时生态问题，不影响打包提交。
- **man page 未打包**：因跳过 pod2man，制品不含 `tpm.1`。用户可用 `perldoc`/`man` 源 README.pod 自行生成，或直接看 README.pod。
- **同名歧义警告**：网络上有多个名为 "tpm" 的项目（tpm2-tools、waterlan DOS 工具等）。本包**仅指 nmeum/tpm tiny password manager**（GPL-3.0-or-later）。
