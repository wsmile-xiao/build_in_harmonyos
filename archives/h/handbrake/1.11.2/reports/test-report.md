# handbrake 1.11.2 测试报告

**测试环境**: OpenHarmony PC aarch64（musl / clang）真机，新端口 `33332`
**上游版本**: HandBrake 1.11.2
**执行时间**: 2026-08-13 08:03:56 +0800 至 08:38:23 +0800
**run_dir**: `/storage/Users/currentUser/ohos-test-runs/handbrake-1.11.2-20260812-r1/codex-a-handbrake-codex-a-handbrake-conan-create-1.11.2-r45-20260813-080352-20260813-080356-9649`
**说明**: 上游无独立自动化测试套件（`test/` 是 `HandBrakeCLI` 构建模块源码和安装规则，无 `make check`）。本报告记录适配后消费侧验证；未把 `test_package` 计入上游自动化测试数量。

## Conan 验证

| 项 | 内容 |
|----|------|
| 命令 | `conan create archives/h/handbrake/1.11.2 --version=1.11.2 --profile:build=ci/conan/profiles/ohos-aarch64 --profile:host=ci/conan/profiles/ohos-aarch64 --build=handbrake/1.11.2` |
| 结果 | 通过，runner exit code 0 |
| Full package reference | `handbrake/1.11.2#33e6f859fc99fbfd7ea87dc7a166e9be:6b129b068851896169fae42d399fa922d239ce8a#2e4735def1793535bc91373e7c47d793` |

## 用例执行结果

### 用例 1: HandBrakeCLI --version

| 项 | 内容 |
|----|------|
| 目的 | R34：真实执行打包产物，断言可启动并正常退出 |
| 命令 | `HandBrakeCLI --version`（`test_package/test.sh`，`conanrun` 环境） |
| 期望 | 退出码 0；输出含编译/版本信息 |
| 结果 | 通过，退出码 0 |

### 用例 2: HandBrakeCLI --help

| 项 | 内容 |
|----|------|
| 目的 | CLI 入口与参数解析冒烟 |
| 命令 | `HandBrakeCLI --help`（同上） |
| 期望 | 退出码 0 |
| 结果 | 通过，退出码 0 |

## 汇总

| 指标 | 值 |
|------|-----|
| 上游自动化用例 N | 0 |
| 适配后新增断言 M | 2 |
| 适配后消费侧验证通过率 | 2/2 (100%) |
| 未计入通过率的项 | ELF 自签名、全链路 `conan create` 属构建/打包门禁，不计入测试用例数 |

## 已知限制

- 未做真实媒体转码（需输入文件与较长运行时间）；硬件编码器（NVENC/QSV/VCE/MF）在 OHOS 上已禁用。
- CI 全量构建耗时长且依赖 contrib 源码镜像可达性；本轮以真机 `conan create` 结果为准。
