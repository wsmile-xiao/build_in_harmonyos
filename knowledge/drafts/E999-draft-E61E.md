# E999: OHOS zsh missing standard autoload functions (is-at-least, compinit)

## 基本信息
- **严重度**: 2 (🟡 medium)
- **类别**: platform | shell-compat
- **触发工具**: zsh | runtime
- **阶段**: runtime

## 错误特征

```
is-at-least:8: is-at-least: function definition file not found
compinit:26: compinit: function definition file not found
Error: your zsh version $ZSH_VERSION is less than the required version: 5.7
```

**关键词**: zsh, autoload, is-at-least, compinit, function definition file not found, fpath, OHOS

## 根因分析

OHOS zsh 5.9 (aarch64-unknown-linux-musl) is installed without the standard autoload function files directory. Functions like `is-at-least` and `compinit` are part of zsh's standard distribution but the function files are not installed in the fpath on OHOS. This causes any zsh script using `autoload -Uz is-at-least` or `autoload -Uz compinit` to fail.

The zsh binary itself works (version 5.9), but the supporting function library that ships with zsh source was not installed during the OHOS zsh build process.

**影响范围**: All zsh scripts on OHOS that use `autoload -Uz is-at-least` or `autoload -Uz compinit`, including install.sh scripts and CLI tools like arttime.

## 推荐方案

### 方法 1: create-missing-zsh-function (优先级 1)

Create the missing `is-at-least` autoload function file in a directory on the zsh fpath.

```bash
mkdir -p ~/.local/share/zsh/site-functions
cat > ~/.local/share/zsh/site-functions/is-at-least << 'EOF'
emulate -L zsh
local i
if [[ "$1" == *.* ]]; then
  local IFS=.
  local -a v1 v2
  v1=(${=1})
  v2=(${=ZSH_VERSION})
  for ((i = 1; i <= ${#v1}; i++)); do
    if (( ${v2[i]:-0} > ${v1[i]:-0} )); then return 0
    elif (( ${v2[i]:-0} < ${v1[i]:-0} )); then return 1; fi
  done
  return 0
else
  [[ ${ZSH_VERSION} -ge $1 ]]
fi
EOF
```

For test scripts, also set the FPATH environment variable:
```bash
export FPATH="$HOME/.local/share/zsh/site-functions:${FPATH:-}"
```

### 方法 2: bypass-install-script (优先级 2, 回退)

For Conan recipes packaging shell scripts, avoid running install.sh directly and instead use `conan.tools.files.copy()` to replicate the install logic, bypassing zsh function dependencies entirely.

## 验证

```bash
zsh -c 'fpath=(~/.local/share/zsh/site-functions $fpath); autoload -Uz is-at-least && is-at-least 5.7 && echo "PASS" || echo "FAIL"'
```

## 涉及软件

- arttime/2.5.0 — install.sh and arttime.zsh both use `autoload -Uz is-at-least`
- Any zsh-based CLI tool that checks zsh version with `is-at-least`

## 相关模式

- E276 — Conan get() BadZipFile (GitHub API URL without extension)
- E275 — Shell set -eu unbound variable

---
*doc/E999.md · knowledge graph draft · 2026-08-18 · contributor: E61E*
