# PARI seadata-big

PARI/GP 的大阶 Atkin 模多项式数据集，为 `ellcard`/SEA 算法提供 500 < p < 800 的 44 个素数阶数据，适用于约 1100 位以内的有限域。

本仓库按任务约定使用 `pari-seadate-big` 名称（`seadate` 是任务目录名）；官方名称为 `seadata-big`。20170418 对应官方 2017-04-18 的 `seadata-big.tar`。

## HarmonyOS 适配

- 这是架构无关的数据包，无需编译数据，也不包含 `.so`、静态库或命令行程序。
- Conan 将官方 `sea*.gz` 原样安装到 `share/pari/seadata/`，同时保留 `README.big` 和许可文本。
- `package_id()` 清除平台设置，使同一数据包可以供 HarmonyOS arm64 PC 和 x86_64 虚拟机使用。
- 通过 `PARI_SEADATA_BIG_DATADIR` 暴露包内 `share/pari`，不自动覆盖 PARI 全局 `datadir`，避免遮蔽已有的其他可选数据。
- 虚拟机验证覆盖 44 个文件的完整解压读取，以及鸿蒙可写 `TMPDIR` 下带空格路径的复制、重命名、重新读取与完整 CRC 校验。

## 使用前提

数据打包没有编译依赖。消费端需要已安装的 PARI/GP，以及基础 seadata 的 `sea0`（例如官方 `seadata-small.tgz`）。big 是增补数据，不替代基础 seadata。

PARI `seadata_cache()` 首先读取 `sea0`，缺少它时即使 `sea503.gz` 存在，`ellmodulareqn(503)` 仍会报文件缺失。请把本包的 `seadata/` 内容与基础数据合并到应用私有数据目录，再在 GP 中设置：

```gp
default(datadir, "/应用可写目录/pari");
e = ellmodulareqn(503);
[poldegree(e[1], x), e[2]]  /* [504, 1] */
```

应用应使用实际的私有可写路径；无需写入系统目录。Conan 获取方式：

```sh
conan install --requires=pari-seadate-big/20170418 -r=ohpcd -pr:h=ohos-aarch64
```

当前为本地验证产物，尚未发布至远程制品仓；发布前请先在本仓库中运行 `conan create`。

## 参考

- [官方数据包说明、日期与 SHA256](https://pari.math.u-bordeaux.fr/packages.html)
- [官方数据源](https://pari.math.u-bordeaux.fr/pub/pari/packages/seadata-big.tar)
- [PARI 椭圆曲线接口](https://pari.math.u-bordeaux.fr/dochtml/html/Elliptic_curves.html)
- 版本级 `20170418/notes.md`：复现命令、测试计数和环境边界。
