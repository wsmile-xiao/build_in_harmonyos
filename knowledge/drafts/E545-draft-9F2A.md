# E545 — autotools 库适配 OHOS：config.guess 缺 HarmonyOS 分支

## 错误特征

configure 阶段失败，日志含：

```
configure: error: cannot guess build type; you must specify one
checking build system type... Invalid configuration
```

`sh config.guess` 报 `unknown ... machine` 或无法输出。

## 触发条件

- 构建系统: autotools
- 阶段: configure（build 类型探测）

## 根因分析

上游发布包的 `config.guess` 未内置 HarmonyOS 内核/系统分支（GNU 主线
config.guess 到较新版本才支持 OHOS）。configure 在 `--build` 探测阶段调用
config.guess 失败即中止。注意 `config.sub`（2024-07-27 起）已内置
`ohos*` / `linux-ohos-*`，通常无需改动。

## 解决方案

### 推荐方案

在 `config.guess` 的 NetBSD 分支之前插入 HarmonyOS case：

```sh
case $UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:$UNAME_VERSION in
    *:HarmonyOS:*:*)
        case $UNAME_MACHINE in
            aarch64|arm64) echo aarch64-unknown-linux-ohos; exit ;;
            *) echo "$0: unsupported HarmonyOS machine $UNAME_MACHINE" >&2; exit 1 ;;
        esac
        ;;
esac
```

验证：

```bash
sh config.guess   # 应输出 aarch64-unknown-linux-ohos
./configure --host=aarch64-linux-ohos --enable-shared --disable-static
```

### 禁止做法

- ❌ 对所有 HarmonyOS 机器报错退出——会阻断 `--build` 自动探测。
- ❌ 同时给 config.sub 补 ohos 分支——新版已内置，重复补会覆盖上游语义。

## 验证

```bash
sh config.guess
conan create . --build=missing
```

## 关联条目

- 相关: E543（新建文件补丁头）
