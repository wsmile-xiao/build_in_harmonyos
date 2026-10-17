# 真机自带 ohos-aarch64 profile 缺 os.version：一律用仓库 CI profile

- **软件**: libdisasm 0.23（泛化到所有真机隔离 job 构建）
- **阶段**: conan create
- **severity**: 2
- **状态**: DRAFT

## 现象

```
======== Computing necessary packages ========
ERROR: There are invalid packages:
<pkg>: Invalid: 'settings.os.version' value not defined
```

构建在依赖图计算阶段即终止，编译根本不开始。

## 根因

真机自带的 `$HOME/.conan2/profiles/ohos-aarch64` 只写到 `os=OHOS`，没有
`os.version`；而 OHOS 适配版 conan 的 `settings.yml` 对 OHOS 定义了
`version: ["5.0", "6.0"]`（必填子设置），package_id 无法计算。

设备上的 `ohos-aarch64-fixed` 虽含 `os.version=6.0`，但它是某次会话的私有补丁版
（cppstd/libcxx/cflags 与 CI 不一致），用它会导致真机结果与 CI 产物不可比。

## 修复

真机跑 `conan create`/`conan test` 时不用设备自带 profile，把仓库
`ci/conan/profiles/ohos-aarch64` 传到设备（含 `os.version=6.0`、
`compiler_executables` 指向 `/data/service/hnp/bin`、buildenv 的
PATH/CONFIG_SHELL/LD_LIBRARY_PATH），`-pr:h`/`-pr:b` 都指向它。真机结果与
buildbot CI 完全同源可比。

## 证据

libdisasm 0.23（10.62.178.77）：设备 profile 首报
`'settings.os.version' value not defined`；settings.yml 定义
`OHOS: version: ["5.0", "6.0"]`；换仓库 CI profile 后 create 正常
（settings 行显示 `os.version=6.0`），打包 + test_package 21/21 通过。
