# 真机隔离 job 构建 cmake 不可用（Error 127）— hnp 工具链不在 PATH

> 草稿（DRAFT）。与同目录 `opencsg-1.8.2-shadow-ci-isolated-job-hnp-toolchain-path.kv` 成对。

## 现象

在真机隔离 job 里 `conan create` 到 build 阶段失败：

```text
opencsg/1.8.2: Running CMake.configure()
opencsg/1.8.2: RUN: cmake -G "Unix Makefiles" ...
/system/bin/sh: cmake: inaccessible or not found
ERROR: opencsg/1.8.2: Error in build() method, line 107
        cmake.configure()
        ConanException: Error 127 while executing
```

L0 质量门禁全部通过，源码下载/解压与全部补丁应用也正常——失败只发生在“找不到 cmake”。

## 根因

hnp 工具链的 `cmake` / `make` / `ninja` / `clang` 位于 `/data/service/hnp/bin`，但该目录
**不在隔离 job 的运行 PATH 上**：

- `ohos-prepare-isolated-conan-job.sh` 生成的 `run-conan-heavy.sh` 只带
  `$HOME/ohpc-ci-shadow/python-user/bin:$HOME/.local/bin:$PATH`；
- `ohos-test-runner.sh` 默认注入的 `TOOL_PATH` 也不含 `/data/service/hnp/bin`。

所以 `CMake().configure()` 在 `/system/bin/sh` 下找不到 cmake。**这是运行环境/调用方式问题，
不是配方问题**——同设备其它可用 job 的 run 脚本都显式把 `/data/service/hnp/bin` 放进 PATH，
并用 `ohos-test-runner.sh --path` 传入。

## 正确做法

按既有 job 惯例调用 runner（不改基础设施脚本）：

```sh
export PATH=$HOME/usr/local/bin:$HOME/.local/bin:/data/service/hnp/bin:/usr/bin:/bin:$PATH
ohos-test-runner.sh \
  --user <user> --lib <lib> --task <task> --mode heavy \
  --workdir "$REPO" \
  --path "$HOME/usr/local/bin:$HOME/.local/bin:/data/service/hnp/bin:/usr/bin:/bin" \
  -- "$HOME/usr/local/bin/zsh" -f -c \
     'zsh -f ci/conan/setup.sh && zsh -f ci/conan/build_and_test.sh "$CI_PACKAGES"'
```

## 不要怎么做

- ❌ 不要为绕过它在库里加 `tool_requires("cmake/...")`：ohpcd 制品仓没有 cmake recipe，
  且 CI 禁用了 conancenter，L0i 依赖发布检查会硬失败。
- ❌ 不要改 `ci/` 下的公共脚本（越权且影响其它库）。

## 适用范围

所有在真机隔离 job 里 `conan create`、且构建系统需要 cmake/make/ninja 的库。
症状是 configure 阶段 `Error 127`，而非编译错误。

## 证据

opencsg 1.8.2：

- round1（用 job 生成脚本的默认调用）与 round2 均在 `cmake.configure()` 处
  `cmake: inaccessible or not found` → `Error 127`；
- 改为显式注入 hnp PATH 后 round3 全绿：`L0/L1/L2/L4/L5` 通过、exit code 0、
  test_package 9 项确定性 + 2 项条件断言全部 `[ok]`。
