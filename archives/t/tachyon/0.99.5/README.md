# tachyon 0.99.5 — 鸿蒙 PC conan 制品

`os=OHOS, arch=armv8`(= aarch64) 的 conan 包。**纯命令行工具包**：只出 `bin/tachyon`，无库无头。

## 出包（鸿蒙 PC CI）

```bash
# 鸿蒙 PC 设备原生编译
conan create . -pr ohos-native
```

> 源码由 `conandata.yml` 的 url 在 `conan create` 时下载并 sha256 校验（`source()` 用 `get()`）。
> 该 tarball 与 sage 用的 `tachyon-0.99.5.p0.tar.gz` **逐字节相同**（sha256 已核对），
> `.p0` 只是 sage 侧的重打包命名。

## 前提

> 所用 conan 的 settings 须含 `os=OHOS`（大写）及 `compiler.version=15`；stock conan 2 默认不含 OHOS。推荐在 `~/.conan2/settings_user.yml` 的 `os:` 下加一行 `    OHOS:`（非侵入扩展，不改 settings.yml），或使用 OpenHarmonyPCDeveloper 分发的 conan。

## 依赖

| 依赖 | 用途 |
|---|---|
| `libpng/1.6.58.1` | `-format PNG` 输出（`#if defined(USEPNG)` 分支） |

## ELF 签名

`package()` 对 `bin/tachyon` 做 XPM 自签。**本包必须重签**：上游 Makefile 在链接后紧跟
`strip`，会把链接器打上的自签改废；不重签则设备上 exec 报 `Permission denied`。

## 消费

```bash
# 装到设备 ~/usr/local
conan install --requires=tachyon/0.99.5 -pr ohos-native \
    --deployer=usr_local --deployer-folder=$HOME/usr/local

# 渲染
tachyon scene.dat -format PNG -o out.png -res 640 480
```

## 点对点搬运预编译包（免 remote）

```bash
conan cache save "tachyon/0.99.5:*" --file tachyon.tgz   # 出包机导出（recipe + 二进制）
conan cache restore tachyon.tgz                           # 目标机导入
```
