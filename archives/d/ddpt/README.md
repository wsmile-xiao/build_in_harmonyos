# ddpt

`ddpt` 是 Douglas Gilbert（sg3-utils 作者）编写的 dd 克隆式数据拷贝工具，用于在常规文件、
块设备与 SCSI passthrough（sg）设备之间拷贝数据，支持类似 dd 的 if/of/bs/count/skip/seek
参数，另有 JF 作业文件模式与 `--wscan`/`--xcopy` 等 SCSI 特有扩展。附带 `ddptctl`、
`ddpt_sgl` 两个辅助程序。

- 上游仓库：https://sg.danny.cz/sg/ddpt.html
- 许可证：BSD-3-Clause
- 构建系统：autotools（release tarball 自带 configure）
- 类型：命令行工具（安装 bin/ 下 ddpt、ddptctl、ddpt_sgl 三个程序）

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 0.97 | built | 首次适配 HarmonyOS PC (aarch64)；config.guess/config.sub OHOS 三元组补丁 + umask 022 修正 |
