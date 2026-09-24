# zgen 0-20150919 适配笔记

## 编译环境

- 构建系统: custom（纯 Zsh 脚本项目，无 configure/Makefile/CMakeLists.txt）
- 编译日期: 2026-09-21
- 编译器: 未调用（无 native 代码）；Conan profile 仍为 ohos-aarch64
- 目标平台: OpenHarmony PC aarch64（交付物为解释型脚本，架构无关）
- 状态: built

## 版本号来源

上游 `tarjoilija/zgen` 从未发布 release tag，`0-20150919` 是 2015-09-19 的源码快照。
该日无提交，快照对应 master 当时的最后一次提交：

```bash
curl -s "https://api.github.com/repos/tarjoilija/zgen/commits?until=2015-09-20T00:00:00Z&per_page=1"
# => 6ac1bf1b201f52d9f5493988f8b3f26b7c0299e0  (2015-09-18T19:12:57Z)
```

`conandata.yml` 因此锁定该 commit 的官方归档，并核对 sha256。

## 适配步骤

```bash
# 1) 取源码（github.com 直连在本机不可达，改用 GitHub 官方归档域 codeload）
python3 scripts/ohc-run.py init-build zgen 0-20150919 \
  --url=https://codeload.github.com/tarjoilija/zgen/tar.gz/6ac1bf1b201f52d9f5493988f8b3f26b7c0299e0

# 2) 语言预检（R47）。zgen 为纯 Zsh，协议 §4.6 语言枚举无 zsh，按 other 如实申报
python3 scripts/ohc-run.py lang-preflight zgen 0-20150919 \
  --src /root/tmp/builds/zgen-0-20150919.work --lang other      # => lang_checked

# 3) 唯一适配点：shebang（见下节），生成补丁
python3 scripts/ohc-run.py refresh-patch --auto zgen 0-20150919

# 4) 生成并验证配方
python3 scripts/ohc-run.py conan-init   zgen 0-20150919
python3 scripts/ohc-run.py conan-verify zgen 0-20150919        # => G1/G2 PASS
```

无 `configure`/`make`/`make install` 步骤：`build()` 只应用补丁，`package()` 复制脚本。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `init-build` 下载失败：`Remote end closed connection without response` | 本机到 `github.com` 直连不可达（curl 60s 超时） | 改用 GitHub 官方归档域 `codeload.github.com`（仓库已有 286 处先例，不属 PF7 镜像黑名单） |
| 2 | `conan create` source() 报 `BadZipFile: File is not a zip file` | 知识图谱 **E483**：codeload 快照 URL 末段是 commit id，`get()` 据此猜格式 | 按 E483 推荐方案在 `get()` 显式传 `filename=f"zgen-{self.version}.tar.gz"`（不在 conandata 再写 filename，避免重复关键字） |
| 3 | `lang-preflight` 把纯 Zsh 项目判为 `other` + “无源文件可统计” | `scripts/ohc/lang_detect.py` 的 `_EXT_LANG` 无 `.zsh` 映射，`_zgen` 无扩展名 | 按检测结果如实用 `--lang other` 申报（不谎报 bash）；缺口写入知识草稿 `E543-draft-27D5` 与 SKILL_FEEDBACK |
| 4 | test_package 功能层首跑失败：`ZGEN_INIT: parameter not set` | 自写测试脚本设了 `setopt no_unset`，而 zgen.zsh 依赖 `[[ -z "${ZGEN_INIT}" ]]` 探测未设变量 | 去掉 `no_unset`（保留 `emulate -L zsh`），并在脚本内注明原因 |
| 5 | 首版测试把 `ZGEN_DIR` 沙箱建在 `test_package/` 内，污染归档树 | 未设 layout 时 `self.build_folder` 即 recipe 目录 | 改用 `tempfile.mkdtemp()` 私有沙箱 + `finally` 清理，绝不写 `$HOME` 或归档树 |

## 源码修改

`patches/0001-zgen.zsh.patch`（+1/−1）：

```diff
-#!/bin/zsh
+#!/usr/bin/env zsh
```

OpenHarmony 没有 `/bin/zsh`（zsh 安装在包前缀下），硬编码解释器路径会让脚本无法直接执行。
`/usr/bin/env zsh` 在各平台等价可用，因此补丁**不含平台宏、无需 `#ifdef` 守卫**（R8 / PF5）。

## 上游测试清点（R51 第一步）

上游快照整包只有 4 个文件，无任何测试设施：

```bash
$ tar tzf zgen-0-20150919.tar.gz | sed 's|^[^/]*/||' | grep -v '^$'
LICENSE
README.md
_zgen
zgen.zsh

$ ls -d tests test spec t 2>/dev/null          # => 无
$ ls Makefile CMakeLists.txt meson.build configure 2>/dev/null   # => 无
$ ls .travis.yml .github 2>/dev/null           # => 无
```

结论：**上游测试数 N = 0**（无 `make check` / `ctest` / `pytest` 注册项），
故 R51 第二步“实际运行上游测试”无对象；第三步按 N=0 如实回填，
并由 `test_package/` 补齐真实功能测试（26 条断言，见下）。

## 依赖版本

- Conan 编译依赖: 无
- 运行依赖: `zsh`（解释器，宿主提供）；`git`（仅 `zgen load/update/selfupdate` 等联网子命令使用）

## 验证结果

```bash
$ python3 scripts/ohc-run.py conan-verify zgen 0-20150919
G1: PASS   # 配方完整性
G2: PASS   # conan create（ohos-aarch64 profile）+ test_package 实跑

# test_package 层一：包布局与内容（POSIX sh，18 断言）
[ok] zgen.zsh installed / executable bit / LICENSE / _zgen on FPATH
[ok] OHOS shebang patch applied ; no hardcoded /bin/zsh
[ok] _zgen declares #compdef zgen
[ok] function zgen() zgen-load() zgen-save() zgen-reset() zgen-list() zgen-saved()
     zgen-update() zgen-selfupdate() zgen-oh-my-zsh() zgen-prezto() zgen-clone() defined
[PASS] zgen package layout: 18 assertions

# test_package 层二：真实 zsh 功能（zsh 5.9，7 断言）+ zsh -n 语法检查
[ok] zgen() defined after source
[ok] 'zgen' prints usage and returns 1
[ok] 'zgen list' reports the missing init.zsh
[ok] 'zgen saved' returns non-zero without init.zsh
[ok] unknown subcommand is rejected
[ok] public zgen-* subcommand functions exported
[ok] ZGEN_DIR/ZGEN_INIT honour the sandbox
[PASS] zgen functional checks: 7 assertions
```

通过率 **26/26 = 100%**。

### 环境说明（不夸大结论）

- 本机 runner 是 **x86_64**，功能层由构建机 `zsh 5.9` 解释执行。zgen 交付物是**解释型脚本、
  无 ELF 产物**，字节与交付内容完全一致，因此该执行覆盖的是真实交付代码。
- `qemu-aarch64` 实跑**不适用**：包内没有任何可执行 ELF；OHOS 目标上的行为差异只可能来自
  目标机 zsh 版本，而 zsh 本身不在本包交付范围内。
- 结论边界：**未在 OHOS aarch64 真机上运行**，上述测试不等价于真机验证。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 2 配方：应用补丁 + 复制脚本，`package_id.clear()`（架构无关） |
| conandata.yml | 官方 codeload 快照 URL + sha256 + 补丁声明 |
| patches/0001-zgen.zsh.patch | shebang 适配（唯一补丁） |
| test_package/test.sh | 布局与内容断言（18 条） |
| test_package/test_zgen.zsh | 真实 zsh 功能断言（7 条） |
| test_package/conanfile.py | 驱动两层测试 + `zsh -n`；无 zsh 时显式 warning skip |
| manifest.yaml | 版本级元数据 |

## 知识沉淀

与 `manifest.yaml` 的 `knowledge_gained` 一一对应：

1. zgen 是纯 Zsh 插件管理器，唯一的 OHOS 适配点是 `zgen.zsh` 的 `#!/bin/zsh` shebang
   （OHOS 无 `/bin/zsh`），改为 `#!/usr/bin/env zsh`。
2. **E483 复现**：codeload 快照 URL 末段是 commit id，conan `get()` 会按该名字猜格式并抛
   `BadZipFile`，必须显式传 `filename="<name>-<ver>.tar.gz"`。
3. `lang-preflight` 对 `.zsh` 源码无扩展名映射，纯 Zsh 项目被判 `other` / “无源文件可统计”，
   默认 `--lang cpp` 下会直接写 `env_unsupported`——已沉淀为知识草稿 **E543-draft-27D5**
   （含 zsh 生态打包范式：shebang、`site-functions` + FPATH、`package_id.clear()`）。

## 注意事项

安装后在 `.zshrc` 中 source 主脚本即可（包已导出 `ZGEN_SOURCE_FILE`，并把 `_zgen` 放进 `FPATH`）：

```zsh
source "$(conan_package_prefix)/share/zgen/zgen.zsh"
# 或直接写绝对路径：
source $HOME/usr/local/share/zgen/zgen.zsh

zgen load zsh-users/zsh-syntax-highlighting
zgen save
```

- `zgen save` / `zgen load` 会调用 `git` 克隆插件仓库，需要网络与 `git`。
- 包内 `share/zsh/site-functions/_zgen` 提供 `zgen` 子命令补全，`compinit` 后生效。
---

**编译结束**: 2026-09-21 20:33
**最终状态**: built
