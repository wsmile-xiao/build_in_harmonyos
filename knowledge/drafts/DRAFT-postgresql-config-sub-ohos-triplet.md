# DRAFT-postgresql-config-sub-ohos-triplet：旧 autotools 内置 config.sub 缺 aarch64-linux-ohos 识别

## 现象

PG 16.10（内置 config.sub 为较旧 autotools 版本）configure 直接失败：

```text
checking build system type... Invalid configuration `aarch64-linux-ohos': OS `ohos' not recognized
configure: error: /bin/sh ../postgresql-16.10/config/config.sub aarch64-linux-ohos failed
```

## 根因

库内置的 `config/config.sub` OS 列举中没有 `ohos*` / `linux-ohos*`。autoconf 2.72
起 config.sub 才加入 OHOS；PG 18.3 内置版本已支持（直接 `--build=aarch64-linux-ohos`
即可），16.10 的旧版本不支持。同类库（afflib、babeltrace2 等）通过补丁给
config.sub 加 ohos 支持解决。

## 修复（最小移植清单）

`config/config.sub` 三处：

1. 基础系统类型表：`gnu* | android* | bsd* | ...` → 加入 `ohos*`
2. 通用 OS 尾部表：`... | zephyr* \` 行 → 加入 `| ohos*`
3. 内核-OS 组合校验：`linux-gnu* | linux-dietlibc* | linux-android* | ...` → 加入 `linux-ohos*`

验证：`./config/config.sub aarch64-linux-ohos` → `aarch64-unknown-linux-ohos`（exit 0）。

## 与本库 umask 修复的组合（combination_novelty）

需改 configure 脚本（config.status 内 `umask 077 && mktemp -d` 在 hmdfs 建
`drwx--S---` 目录且 chmod 无效 E046，`subs1.awk` 写入 Permission denied，见
E011/E052/E060——但 E011/E052/E060 均未覆盖 config.sub 移植）。16.10 因
config.sub 也必须改，故把 configure/config.guess 的 `umask 077`→`022` 一并内嵌
到同一补丁（18.3 无 config.sub 需求，是在 conanfile build() 动态 replace）。

## 适用边界

- autotools 库 + 内置 config.sub 不支持 ohos → 移植本清单；支持（如 18.3）则不用
- CI 干净环境不可依赖外置 config.sub/guess 拷贝（路径不存在）
- 显式 `--build=aarch64-linux-ohos` 后 configure 跳过 config.guess（其数据库亦不识别 OHOS）

## 验证证据

- `./config/config.sub aarch64-linux-ohos` exit 0
- configure → make → install → conan build/export-pkg 全通过
- 消费者用例真实连接 SQL 通过

## 查重关系

- similar_to: E011, E052, E060（umask/config.status hmdfs 权限）
- caused_by: 无
- prerequisite_of: 无
- conflicts_with: 无
- 适用反例：内置 config.sub 已支持 ohos 的版本（PG 18.3）不需要本移植