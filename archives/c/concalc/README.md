# concalc

`concalc` 是 Extcalc 科学计算器的控制台版本：把 extcalc 的解析/计算算法打包成
一个简单终端程序，支持算术、函数（sqrt/sin/...）、角度制、进制转换与脚本模式。

```
$ concalc "2*(3+7/2)"
13
$ concalc "sqrt(2)"
1.4142135623730950488016887242097
```

- 上游仓库：https://sourceforge.net/projects/extcalc-linux/（concalc 为其子项目）
- 许可证：GPL-2.0-or-later（COPYING）
- 构建系统：CMake（2008 年代项目，CMAKE_MINIMUM_REQUIRED 2.4.3）
- 类型：命令行工具（无库产物）

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 0.9.3 | built | 首次适配 HarmonyOS PC (aarch64) |
