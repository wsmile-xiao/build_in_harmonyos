# ink

查询喷墨打印机墨水余量的命令行工具（libinklevel 的前端），支持 USB 与 BJNP
网络协议连接的 HP 及兼容设备，按墨盒类型输出百分比余量。

- 上游主页：https://ink.sourceforge.io/
- 许可：GPL-2.0
- 构建系统：autotools（configure + make，无 libtool）
- 运行时依赖：`libinklevel/0.9.7`（制品仓已发布，Conan 自动拉取）
- 产物：单命令行二进制 `ink`（`-v` 打版本，`-p usb|-p bjnp|-b <uri>` 查询余量）

## 版本索引

| 版本 | 状态 | 适配说明 |
|------|------|---------|
| 0.5.3 | built | 首次适配 HarmonyOS PC（aarch64-linux-ohos）：config.guess/config.sub 三元组补丁（2018 vintage，内置补丁脚本对该版补不全，按 libinklevel 同款手补）、configure mktemp 分支补丁（HMDFS/E490 同源防御）；上游无测试套件，补齐 `ink -v` 冒烟测试 |

## 使用方式

```python
self.requires("ink/0.5.3")
```

纯命令行工具（application），无库链接目标；安装后 PATH 中获得 `ink`。
