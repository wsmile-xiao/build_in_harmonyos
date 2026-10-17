# snaphu

`snaphu`（SNAPHU，Statistical-Cost Network-Flow Algorithm for Phase Unwrapping）是斯坦福雷达干涉测量
（InSAR）项目发布的二维相位解缠命令行工具：输入缠绕相位干涉图，输出解缠后的连续相位场。

- 上游发布页：https://web.stanford.edu/group/radar/softwareandlinks/sw/snaphu/
- 源码包：`snaphu-v2.0.7.tar.gz`
  sha256 `c03ac126f9a964321bb5d6fb5b4004728368da268d7cb8407bb295a8abe5b262`
- 许可证：Stanford 自定义许可（允许免费使用/修改/再分发，不收取再分发费用；见 `licenses/README`）
- 构建系统：裸 Makefile（`src/Makefile`，无 configure；`CC`/`CFLAGS`/`BINDIR` 三处硬编码由配方命令行覆写）
- 类型：命令行工具（`bin/snaphu`，无库产物，`package_type = "application"`）
- 上游测试：无（`src/Makefile` 无 `check`/`test` 目标，tarball 全树无测试源文件），
  交付由 `test_package` 消费者驱动验证（1 程序 / 3 场景 / 14 断言）

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 2.0.7 | built | 首次适配 HarmonyOS PC (aarch64) |

## 用法

```bash
snaphu <infile> <linelength> -o <outfile> -d   # 变形（deformation）模式解缠
snaphu -hv                                     # 打印版本与用法
```

## 已知限制

- 上游 `config/` 只是运行期配置模板，本包只交付 `bin/snaphu` 与 man 页；
  使用者按上游 README 自行生成 `snaphu.conf`。
- 上游 `install` 目标只面向维护者本机的 `/usr/local`，本包改由 `package()` 手工安装。
