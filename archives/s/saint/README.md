# saint 2.5.0 — OpenHarmony 编译记录

## 基本信息
- 软件: saint (SAINT)
- 版本: 2.5.0
- 构建系统: makefile
- 目标: ohos-aarch64
- 依赖: gsl/2.8

## 编译指导
- 纯 Makefile 工程，无 configure。conanfile 按 R33 从 Conan conf / gsl 依赖注入 CC、-I、-L 与链接闭包。
- 不跑 `make all`：其末尾 clean 的 `rm src/*/*.gch` 在无 .gch 时 glob 不匹配会失败；改为逐工具 target 构建（`-j1`）。
- zip 归档含 `__MACOSX/` 与预编译 `bin/`，source() 已剔除，确保全量源码构建。

## 补丁清单
- 无（0 补丁）。

## 已知限制
- 4 个 MCMC 工具（saint-spc-noctrl / spc-noctrl-matrix / spc-ctrl / int-ctrl）全量分析需大型真实 AP-MS 数据集且为小时级，test_package 仅做 usage 冒烟（验证可执行 + GSL 拉起）。
- saint-reformat 的轻量数据重排已完整跑通，作为核心功能验证。

## 功能验证
- 真机 OHOS aarch64 conan create（test_package 11 项断言）：5 个可执行安装、`-v` 版本、saint-reformat 真实数据重排产出 interaction.new、4 个 MCMC 工具 usage 冒烟。
- 上游无测试框架（已审计），test_package 为自建功能验证。
