# open-completion

## 简介

open-completion 提供 macOS `open` 命令的 bash 自动补全脚本，
来源为开源项目 [moshen/open-bash-completion](https://github.com/moshen/open-bash-completion)
的 `open` 文件。纯 bash 脚本，无需编译。

## OHOS 适配

### 适配要点

1. **无编译流程**：纯 bash 补全脚本，`conan create` 只做下载、校验与安装
2. **安装路径**：`share/bash-completion/completions/open`，可被 bash-completion 懒加载
3. **安装名映射**：上游文件名已是命令名 `open`（同 Homebrew open-completion formula 的
   `bash_completion.install "open"`），无需改名
4. **Darwin 守卫**：上游脚本以 `if [[ $(uname) == Darwin ]]` 包裹定义与注册；
   在 OHOS/Linux 上验证注册行为需用 PATH 前置的 fake `uname`（返回 Darwin）复现
5. **依赖 bash-completion**：补全运行时需要 bash-completion 包提供框架函数
   （`_get_comp_words_by_ref`，在 `_open` 函数体内调用）

### 已知问题

- 上游无任何测试套件（仅 `LICENSE`/`README.md`/`open`），已按规范做
  `no_tests` 审计声明，详见 `1.0.5/test_package/MANIFEST.yml`。

## 排除与替代

无排除组件（仅包含一个 completion 脚本）。

## 依赖

### 运行依赖

| 依赖 | 说明 |
|------|------|
| bash-completion | 提供 `_get_comp_words_by_ref` 等补全框架函数 |

### 编译依赖

无编译依赖（纯文本脚本）。

## 功能验证

```bash
# 安装产物
ls $PREFIX/share/bash-completion/completions/open

# 语法与注册检查
bash -n $PREFIX/share/bash-completion/completions/open
grep -q '_open()' $PREFIX/share/bash-completion/completions/open

# Darwin 守卫下复现注册（fake uname）
mkdir -p /tmp/fakebin && printf '#!/bin/sh\necho Darwin\n' > /tmp/fakebin/uname
chmod +x /tmp/fakebin/uname
PATH=/tmp/fakebin:$PATH bash -c 'source $PREFIX/share/bash-completion/completions/open && complete -p open'
# → complete -o filenames -F _open open
```

## 参考

- 官方仓库: https://github.com/moshen/open-bash-completion
- 上游文件: open
- 许可证: MIT
