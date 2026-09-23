# coinor-vol — 软件归档

COIN-OR Vol（Volume Algorithm）—— 针对 LP 松弛的子梯度方法实现，同时产出原始解与对偶解。

| 版本 | 状态 | 构建系统 | 说明 |
|------|------|----------|------|
| 1.5.4 | built | autotools | 首次 HarmonyOS PC (arm64) 适配 |

## 关键信息

- 上游: https://github.com/coin-or/Vol
- 许可证: Eclipse Public License 1.0 (EPL-1.0)
- 核心库: libVol（无强制第三方依赖；CoinUtils/Osi 仅用于可选 OsiVol 接口与测试）
- 适配要点: config.guess/config.sub 2007 版需加 HarmonyOS/aarch64 支持；VolVolume.hpp
  的 register 关键字与 C++17 不兼容需移除；COIN-OR 递归 configure 的 config.status
  在 HMDFS 上需修补 mktemp/umask

详见 `1.5.4/notes.md` 与 `1.5.4/manifest.yaml`。