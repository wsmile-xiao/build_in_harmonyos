# E429 — Makefile 内置编译器默认值绕过 OHOS 交叉工具链

## 错误特征
上游 Makefile 在文件中设置 `CC := gcc`、`CPP := g++`，构建日志仍显示主机编译器，或在交叉构建环境中报找不到 `gcc`/`g++`。Conan profile 中的交叉编译器配置不会自动覆盖这类 Makefile 赋值。

## 触发条件
- 构建系统: make
- 阶段: compilation/linking
- 目标: OHOS aarch64 等交叉编译平台

## 根因分析
GNU make 将命令行变量赋值置于 Makefile 普通赋值之前。因此，仅在环境或 profile 中提供 `CC`、`CXX` 并不足以覆盖上游 `CC := gcc`、`CPP := g++`；需要在 make 命令行显式传递工具链可执行文件。

## 解决方案

### 推荐方案
从 Conan 的 `tools.build:compiler_executables` 读取 C 与 C++ 编译器，并通过命令行传给 make，例如 `make -j1 CC="$OHOS_CC" CPP="$OHOS_CXX"`。保持上游链接参数（例如 `-pthread`），并检查实际构建日志中的编译器路径。

### 禁止做法
- ❌ 不要为迎合主机编译器而删掉上游 `CC`/`CPP` 赋值或改写源文件。
- ❌ 不要只设置环境变量后假定 Makefile 已使用交叉工具链。

## 验证
```bash
make -j1 CC="$OHOS_CC" CPP="$OHOS_CXX"
# 确认编译和链接命令都指向 OHOS aarch64 clang 工具链。
```

## 关联条目
- 相关: 无
