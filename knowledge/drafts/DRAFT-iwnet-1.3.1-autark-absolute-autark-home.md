# AUTARK_HOME 绝对路径注入（Autark 嵌套外部项目构建）

## 概述
Autark（build.sh 包装的 Makefile 驱动，Softmotions 系库 iwnet/iowow/libhive 使用）在
**嵌套外部项目**（`iowow.autark` 等 `include` 的 extern 项目）构建时，若环境变量
`AUTARK_HOME` 为**相对路径**（build.sh 默认 `autark-cache/.autark-dist`），父 autark
在 cwd 已切换的 extern 目录内再次 spawn `autark` 子进程时无法解析到真实二进制，
报 `execve: Permission denied` 并 FATAL。

## 错误特征
```
execve: Permission denied
FATAL   autark.c:8475 -15|External command failed (AK_ERROR_EXTERNAL_COMMAND)|
        src/<mod>/Autark:<n> ..@ autark: 1
FATAL   autark.c:8475 -15|External command failed (AK_ERROR_EXTERNAL_COMMAND)|
        <proj>.autark:<m> run /bin/sh: 254
```

## 根因
1. `build.sh` 默认 `AUTARK_HOME=autark-cache/.autark-dist`（**相对**当前目录）。
2. 父 autark 解析 `iowow.autark` 等 extern 项目时，`fetch_resource.sh` 下载到
   `autark-cache/extern_*`，随后 `run` 块在 extern 目录内再次调用 `autark`。
3. 子进程 `execvp("autark")` 依赖 PATH；相对 `AUTARK_HOME` 在 cwd 变化后解析错位，
   导致 execve 失败（Permission denied / not found 表象差异取决于文件 mode）。

## 方案
在构建入口（含 Conan recipe `build()`）注入**绝对路径**：
```sh
export AUTARK_HOME="$(pwd)/autark-cache/.autark-dist"
mkdir -p "$AUTARK_HOME"
export PATH="$(pwd)/autark-cache/.autark-dist:$PATH"   # 供嵌套 autark 自解析
./build.sh --prefix="$PREFIX"
```
Conan 配方中可用内联环境前缀：
```python
self.run(f"BUILD_TYPE=Release AUTARK_HOME={autark_home} ./build.sh --prefix={build_dir}", cwd=build_dir)
```

## 验证
- iwnet 1.3.1：注入绝对 AUTARK_HOME 后 `./build.sh --prefix=...` rc=0，
  `autark-cache/src/libiwnet.a`、`lib64/libiwnet.a`、include/iwnet、include/iowow、
  pkgconfig 全部产出；conan-verify G2 conan create PASS。
- 未注入时 100% 复现 `iowow.autark:14 run /bin/sh: 254`。

## 适用边界
- 适用于任何 Autark 驱动且包含 extern 外部项目（fetch_resource + run）的库。
- 仅单层 extern 时也可能出现（cwd 切换即触发），与项目深度无必然关系。
- 反例（不适用）：无 extern 嵌套的简单 Autark 项目可继续用相对 AUTARK_HOME。

## 关联条目
- similar_to：E002（/tmp 只读——同属环境变量注入解决类）
- similar_to：E098（toybox 缺 install——同属 OHOS 工具/构建环境适配）
- prerequisite_of：conan 深缓存路径下构建 Autark 系库