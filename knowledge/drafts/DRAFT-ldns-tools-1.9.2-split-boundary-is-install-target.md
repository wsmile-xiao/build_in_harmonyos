# DRAFT: 库与 CLI 同一次 make 产出时，拆分边界在 install 目标层

> Contributor: username- | Status: DRAFT | Created: 2026-09-17
> 来源: ldns-tools 1.9.2 适配（ldns 的库 + drill + ldns-* 示例程序同工程）

## 症状

按上游 README 适配 tools 包：

```
./configure --with-drill --with-examples && make && make install
```

产物"看起来对"，但

1. `make install` 装出来的东西包含 `libldns.a`、`ldns/*.h`、`ldns.pc`
   以及 **470+ 个 `ldns_*.3` man3 页**——与命令行工具毫无关系；
2. 在鸿蒙设备上，把这些文件安装 + 逐个签名的时间会把任务拖到超时。

## 根因

`--with-drill` / `--with-examples` 只决定**编不编这些程序**，
真正的库/工具边界只存在于 Makefile 的安装目标层：

```make
install-lib:      # libldns
install-h:        # 头文件
install-pc:       # pkg-config
install-manpages: # 470+ man3
install-drill:    # drill 及其 man1
install-examples: # ldns-* 系列程序及其 man1
install: install-lib install-h install-pc install-manpages install-drill install-examples
```

也就是说 configure 阶段**没有**"只出 CLI"的开关，聚合 `install`
必然把所有产物一起装上。判据：

```sh
grep -nE '^install(-[a-z]+)?:' Makefile      # 列出可拆的安装目标
grep -c 'ldns_.*\.3' Makefile                # man3 计数（ldns 1.9.2: 470+）
```

## 修复

逐目标安装，并显式给 `DESTDIR`：

```sh
make -j1 install-drill install-examples DESTDIR=<package_folder>
```

包内再防御性删掉 `include/ lib/`，保证"同一文件只有一个属主"。

## 同一次适配里另外两个必踩的点

- **config.guess 的分支与 config.sub 的认可要一起改。** ldns 1.9.2 自带的
  config.guess 时间戳已是 `2026-05-17`，依旧只认 `aarch64:Linux:*`；
  交叉构建时报 `cannot guess build type; you must specify one`。
  补上 `aarch64:HarmonyOS:*` 分支后，config.guess 猜出的三元组还要
  config.sub 接受（`aarch64-harmonyos-linux-gnu`），否则变成
  `Invalid configuration`。两个文件必须成对补。
- **`drill` 是 getopt 不是 getopt_long。** 它用 `-v` 打印版本并以 0 退出，
  平台 L2 冒烟的 `--version`/`--help` 会落到未知选项分支；
  本包靠同工程的 `examples/ldns-version`（`main(void)` 忽略 argv 直接
  打印 `ldns_version()`）通过冒烟，不需要额外补丁——但要点在于
  **先确认包里到底有没有一个能对 `--version` 返回 0 的程序**，再决定改不改上游。