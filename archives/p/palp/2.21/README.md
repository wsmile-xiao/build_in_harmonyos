# palp 2.21 — 鸿蒙 PC conan 制品

`os=OHOS, arch=armv8`(= aarch64) 的 conan 包。**纯命令行工具包**：只出 `bin/`，无库无头。

## 出包（鸿蒙 PC CI）

```bash
# 鸿蒙 PC 设备原生编译
conan create . -pr ohos-native
```

> 源码由 `conandata.yml` 的 url 在 `conan create` 时下载并 sha256 校验（`source()` 用 `get()`）。

## 前提

> 所用 conan 的 settings 须含 `os=OHOS`（大写）及 `compiler.version=15`；stock conan 2 默认不含 OHOS。推荐在 `~/.conan2/settings_user.yml` 的 `os:` 下加一行 `    OHOS:`（非侵入扩展，不改 settings.yml），或使用 OpenHarmonyPCDeveloper 分发的 conan。

## 产物

25 个可执行文件：

| 程序 | 作用 |
|---|---|
| `poly.x` / `poly-{4,5,6,11}d.x` | 多胞形的顶点、格点、面、反射性分析 |
| `class.x` / `class-{4,5,6,11}d.x` | 反射多胞形的分类/枚举 |
| `cws.x` / `cws-{4,5,6,11}d.x` | 组合权重系统 |
| `nef.x` / `nef-{4,5,6,11}d.x` | nef 部分与 Hodge 数 |
| `mori.x` / `mori-{4,5,6,11}d.x` | Mori 锥与相交环 |

后缀 `-Nd` 表示该二进制按 `POLY_Dmax=N` 编译；维度是**编译期常量**，故每个维度一份。
无后缀的按 `Global.h` 的默认值（6）编译。

## ELF 签名

`package()` 对 `bin/` 下所有 ELF 做 XPM 自签（`--sign-so` 等价动作）。产可执行文件的包必签，
否则设备上 exec 报 `Permission denied`。

## 消费

```bash
# 装到设备 ~/usr/local（裸调用）
conan install --requires=palp/2.21 -pr ohos-native \
    --deployer=usr_local --deployer-folder=$HOME/usr/local

# 或在 conan 工程里取 bindir
conan install --requires=palp/2.21 -pr ohos-native
```

## 点对点搬运预编译包（免 remote）

```bash
conan cache save "palp/2.21:*" --file palp.tgz   # 出包机导出（recipe + 二进制）
conan cache restore palp.tgz                      # 目标机导入
```
