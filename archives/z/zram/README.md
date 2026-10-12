# zram-generator（recipe 名 zram）

systemd/zram-generator：读取 zram-generator.conf，为 zram 压缩交换设备生成 systemd 单元（.swap/.mount）并在开机时完成 mkswap/swapon 的 systemd generator。OHOS 无 systemd，本仓库以**独立 CLI 工具**形态交付 `zram-generator` 可执行文件。

## 功能概述

- 读取 `/usr/lib`、`/usr/local/lib`、`/etc`、`/run` 下的 `systemd/zram-generator.conf`（及 `.conf.d` drop-in，liboverdrop 覆盖序）定义 zram 设备
- generator 模式：`zram-generator <dir>` 把生成的 systemd 单元写入指定目录
- `--setup-device <zramN>`：对单个设备写压缩算法、mem_limit/disksize，并经 systemd-makefs 做 mkswap
- `--reset-device <zramN>`：写 `/sys/block/zramN/reset` 销毁设备
- `zram-size` 支持表达式（fasteval，如 `min(ram / 2, 4096)`），可按内存上限条件启用

## OHOS 适配

- **无 systemd**：`systemd-zram-setup@.service` 拉起形态不可用；交付独立 CLI，保留 `--setup-device`/`--reset-device`/单元生成三种模式，不安装 systemd unit 与 man 页
- **上游 Makefile 硬门**（`pkg-config systemd` 取 `SYSTEMD_*` 安装目录，OHOS 无 systemd pc 模块）：以 make 命令行变量覆盖绕开（三个 `SYSTEMD_*` 占位 + `NOMAN=1`），Makefile 零补丁
- `SYSTEMD_UTIL_DIR` 经 Makefile `export` 进入 cargo 环境——`src/setup.rs` 以 `env!("SYSTEMD_UTIL_DIR")` 编译期内联（缺失即编译失败），占位 `/usr/lib/systemd` 仅影响 `--help` 内嵌文本与 systemd-makefs 拼接路径
- **dev-deps nix 门控补丁**：nix 0.23 的 pre-ohos cfg 门在 ohos 目标误启用 glibc-only 符号（O_FSYNC/mqueue/aio），以 `cfg(not(target_env = "ohos"))` 门控其 dev-dependency 适用范围（不改动任何上游测试用例，非 OHOS 平台行为不变）
- **设备内核当前无 zram**（`/sys/class/zram-control`、`/dev/zram*` 均不存在）：`--setup-device`/`--reset-device` 在 sysfs 写入处干净报错退出（anyhow 上下文，exit 1，无 panic）；生成器模式（配置解析 + 单元文件生成）不依赖内核 zram，真机可完整验证
- cargo 依赖经 rsproxy.cn sparse 镜像获取（设备直达 crates.io TLS 不通，argc 先例）
- Rust 工具链：harmonybrew cargo/rustc（探测已知位置；缺失时从 Harmonybrew bottles 用 Python urllib 引导，argc/martin 先例）

## 依赖关系

- 编译：cargo/rustc（harmonybrew）、clang（链接器）、GNU make；pkg-config 不需要（变量覆盖绕开，不会执行）
- crate 依赖（cargo 按 Cargo.toml 自动解析，无 C 库）：anyhow、clap 4.5、liboverdrop、rust-ini、log、fasteval；测试 dev-deps 为 tempfile/fs_extra/nix/ctor（nix 在 OHOS 目标被 cfg 门控，见 OHOS 适配）
- 运行：无额外共享库依赖；真实 swap 功能依赖内核 zram 模块（OHOS 内核当前未提供）

## 参考资料

- 上游项目：<https://github.com/systemd/zram-generator>
- 配置参考：上游 `man/zram-generator.conf.5.md`、示例 `zram-generator.conf.example`
