# emojify 2.2.0 适配笔记

## 编译环境
- 构建系统: none（纯 bash 脚本，无编译）
- 编译日期: 2026-08-14
- 编译器: n/a（脚本无需编译）
- 状态: published

## 软件简介

emojify 是一个纯 bash shell 脚本，用于在命令行上将 emoji 别名（如
`:sparkling_heart:`）替换为 emoji 原始字符。主文件 `emojify` 约 102KB，
shebang 为 `#!/usr/bin/env bash`，仅需 bash 4+ 运行（仅使用 bash 内置 +
`cat`/`tr`），无任何 C/C++ 库依赖。

## 适配步骤

1. 下载源码包并校验 sha256：
   `https://codeload.github.com/mrowa44/emojify/tar.gz/refs/tags/2.2.0`
   sha256 = `340b866c432705989f71a61551c92af55f49f14d8f17b2c63a0db99e2d687e55`
2. 解压后目录 `emojify-2.2.0/` 包含 `emojify`（脚本）、`LICENSE.md`、
   `README.md`、`emoji_scrap_github.py`、`emojify_tests.bats`、`img/`、
   `.circleci/`。
3. 编写 conandata.yml（sources + patches: []）。
4. 编写 conanfile.py：
   - `source()`: `get(self, **self.conan_data["sources"], strip_root=True)`
   - `build()`: `apply_conandata_patches(self)`（本版本无补丁）
   - `package()`:
     * 用 `copy()` 把 `emojify` 脚本复制到 `bin/`
     * 用 `replace_in_file()` 把 shebang `#!/usr/bin/env bash` 改为
       `#!/data/service/hnp/bin/bash`（OHOS bash 5.3 路径，构建机上同样存在）
     * `os.chmod(bin_path, 0o755)` 赋予可执行权限
     * 复制 `LICENSE.md` 到 `licenses/` 和 `share/emojify/`
   - `package_info()`: `libs=[]`, `includedirs=[]`, `libdirs=[]`,
     `bindirs=["bin"]`
5. 编写 test_package/：conanfile.py + test.sh + MANIFEST.yml。
6. 运行 `python3 scripts/ohc-run.py conan-verify emojify 2.2.0` 验证。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 误标 build_system=autotools | emojify 无构建系统，init-build 默认推断有误 | manifest.yaml 中修正 build.system=none；conanfile build() 仅 apply_conandata_patches |
| 2 | 上游 shebang `#!/usr/bin/env bash` 在 OHOS 上 /usr/bin/env 可能不可用 | OHOS 标准环境 PATH 中无 env 或 bash 不在 /usr/bin | replace_in_file 改为 `#!/data/service/hnp/bin/bash` |
| 3 | 纯脚本无 ELF 签名机制 | 非 ELF 二进制 | 仅 os.chmod 0o755，不需 binary-sign-tool |
| 4 | 不适用 shared/fpic options | 脚本非共享库 | conanfile 不声明 options |

## 源码修改

- 无源码补丁（patches: []）。
- 唯一修改是在 package() 阶段对已安装脚本做 shebang 替换（replace_in_file），
  不修改原始源码树。

## 依赖版本

- 无外部依赖（无 C 库，仅 bash 内置 + cat/tr）
- 运行时依赖：bash 4+（OHOS 提供 bash 5.3 @ /data/service/hnp/bin/bash）
- 构建工具：conan 2.x（仅用于打包，不编译）

## 验证结果

```bash
$ python3 scripts/ohc-run.py conan-verify emojify 2.2.0
# conan create emojify/2.2.0@ohpcd/stable
# test_package: test.sh 运行 6 个功能用例（emoji 替换 + --version）
# 结果: PASS
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/emojify | bash 脚本，shebang 已改为 OHOS bash 路径，权限 0755 |
| licenses/LICENSE.md | MIT 许可证 |
| share/emojify/LICENSE.md | MIT 许可证副本 |

## 注意事项

- 该软件为纯 bash 脚本，无编译阶段，conan create 不会调用任何编译器。
- shebang 补丁在 package() 中执行（对包内副本操作），不修改源码树。
- 脚本非 ELF 二进制，L4 安全扫描（checksec）会跳过（无 ELF magic）。
- bash 版本检查：emojify 内部检查 `${BASH_VERSION%%.*} < 4` 会报错退出，
  OHOS bash 5.3 满足要求。
---

**编译结束**: 2026-08-14 16:12
**最终状态**: published
