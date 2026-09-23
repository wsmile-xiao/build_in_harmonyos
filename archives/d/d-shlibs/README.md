# d-shlibs

Debian 共享库打包辅助工具集。纯 bash 脚本、零编译，本体只有两个可执行文件：

- **`d-shlibmove`** — 把共享库二进制文件（连同 `-dev` 软链、静态库 `.a`、libtool
  `.la`）移动到正确的 Debian 包目录，并按 `debian/control` 校验包结构，最后打印
  待执行的安装/移动命令（`--commit` 才真正执行，否则 dry-run 退出码为 2）。
- **`d-devlibdeps`** — 读取库的 DT_NEEDED 条目，生成 `-dev` 包所需的
  `devlibs:Depends=` 构建依赖行，写入 `debian/<devpkg>.substvars`。

上游把它用于自动化 libtool 风格的库打包，并捕获常见的打包错误。

## 版本列表

| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 0.109 | published | 2026-09-14 | 纯 bash 脚本打包型适配，零编译；依赖 debhelper/13.3.4 + dpkg/1.23.7 + binutils/2.46.0 |

## 安装内容

- `bin/d-shlibmove` — 共享库移动/打包辅助（bash）
- `bin/d-devlibdeps` — `devlibs:Depends` 依赖行生成（bash）
- `share/man/man1/d-shlibmove.1`、`share/man/man1/d-devlibdeps.1` — man 页
- `licenses/COPYING` — GPL-2.0-or-later

## 平台限制说明

- 两个脚本的 shebang 都是 `#!/bin/bash`，而 OHOS PC 的 `/bin` 指向 `/system/bin`，
  **镜像内没有 `/bin/bash`**。因此调用时必须显式指定解释器
  （例如 `bash <prefix>/bin/d-shlibmove …`），否则会 `bad interpreter`（rc=126）。
- `d-devlibdeps` 的依赖校验分支依赖 `apt-cache`；`apt` 未发布到 ohpcd 制品仓
  （见版本目录 `manifest.yaml` 的 `dependencies_unavailable`），该分支在 OHOS 上不可用。
  DT_NEEDED 可被内置 override 规则消解或命中同源 `debian/control` 的库仍可正常生成
  `devlibs:Depends`。
- 上游 `make check` 的第 3、4 条命令需要 `shellcheck`，该工具在本平台不可用
  （未安装且未发布），因此上游检查中只有 `bash -n` 两条可执行。
- 脚本通过 `$DEB_HOST_GNU_TYPE-objdump` 调用 objdump；`DEB_HOST_GNU_TYPE` 由
  `dpkg-architecture` 运行时给出（本平台为 `aarch64-linux-gnu`），不要在配方里硬编码。

## 相关文件

- `commands.json` — 命令行工具声明（R38）
- `0.109/manifest.yaml` — 版本元数据（含未发布依赖登记）
- `0.109/notes.md` — 适配笔记（含 R47 语言预检误判复核、R51 上游测试三步法）
- `0.109/reports/` — 测试报告 / 配方验证报告 / Pre-PR 审计结果
