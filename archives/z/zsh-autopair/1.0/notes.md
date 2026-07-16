# zsh-autopair 1.0 适配笔记

## 编译环境

- 构建系统: custom（纯 Zsh 脚本插件，无需 native 编译）
- 编译日期: 2026-07-14
- 编译器: clang/clang++（本项目未调用编译器）
- 状态: built

## 编译步骤

1. 按 SKILL.md 加载 openharmony-compile-agent 流程要求。
2. 通过上游标签 `v1.0` 获取源码：
   ```bash
   python3 scripts/ohc-run.py init-build zsh-autopair 1.0 \
     --url=https://api.github.com/repos/hlissner/zsh-autopair/tarball/refs/tags/v1.0 \
     --tar=tar.gz
   ```
3. 确认项目为纯 Zsh 插件，无 `configure`、`Makefile`、`CMakeLists.txt` 等 native 构建入口。
4. 手动安装到 staging：
   ```bash
   mkdir -p "$TEST_PREFIX/$DEFAULT_PREFIX/share/zsh-autopair"
   cp autopair.zsh "$TEST_PREFIX/$DEFAULT_PREFIX/share/zsh-autopair/autopair.zsh"
   cp LICENSE README.md "$TEST_PREFIX/$DEFAULT_PREFIX/share/zsh-autopair/"
   ```
5. 编写 Conan 配方，`build()` 为空操作，`package()` 复制 Zsh 插件脚本、README 和 LICENSE。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 首次使用 GitHub archive URL 下载失败 | 远端关闭连接 | 改用 GitHub API tarball URL |
| 2 | init-build 未识别构建文件 | 该项目是纯 Zsh 脚本插件 | 采用 custom/no-op build，直接复制脚本打包 |

## 源码修改

无源码补丁，`patches_applied: []`。

## 依赖版本

- 运行依赖: Zsh >= 5.0.2
- 编译依赖: 无

## 验证结果

```bash
# staging 文件检查
find "$TEST_PREFIX/$DEFAULT_PREFIX/share/zsh-autopair" -type f -maxdepth 1
# LICENSE, README.md, autopair.zsh

# smoke test
zsh -fc "source '$TEST_PREFIX/$DEFAULT_PREFIX/share/zsh-autopair/autopair.zsh'; print -r -- \$AUTOPAIR_PAIRS"
# 输出包含默认配对: " } ' ) ] `
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 2 配方，纯脚本打包 |
| conandata.yml | 上游源码 URL 与 sha256 |
| test_package/conanfile.py | Conan smoke test |
| test_package/test.sh | test_package 源文件占位与文件存在检查 |
| manifest.yaml | 版本级元数据 |

## 注意事项

用户需在 `.zshrc` 中手动 source 插件：

```zsh
source $HOME/usr/local/share/zsh-autopair/autopair.zsh
autopair-init
```
