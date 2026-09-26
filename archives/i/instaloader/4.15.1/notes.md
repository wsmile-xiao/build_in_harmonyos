# instaloader 4.15.1 适配笔记

## 编译环境
- 构建系统: setuptools（纯 Python）
- 编译日期: 2026-09-25
- 平台: HarmonyOS aarch64 / Python 3.12.8 / Conan 2.29.1
- 状态: built（conan-verify 与 W3 已通过，尚未上传制品）

## 源码与依赖
- 官方 PyPI sdist：instaloader-4.15.1.tar.gz
- SHA256: 323ee2015540e627df25535703f246dc39695b71f7f04dadfe67e239dadf3b55
- 必需运行时依赖：requests>=2.25
- 可选 extra：browser_cookie3>=0.19.1，本基础包不安装
- Conan 制品仓依赖探测：ohpcd 远端返回 `system acceleration policy not enabled`，未能完成远端 recipe 证明；recipe 不声明未经证实的 C/C++ 依赖。

## 测试策略
上游 4.15.1 sdist 不包含 tests/ 目录、pytest 配置或测试运行器，因此没有可执行的上游测试用例可保留或修改。test_package 增加真实消费者测试：导入已安装模块、实例化 `Instaloader`、调用公开 API 符号，并执行安装后的 `instaloader --version`。

## 源码修改
无。未修改上游源码或测试文件。

## 验证结果
- `python3 -m pip wheel --no-deps --no-build-isolation -w dist .`：通过
- 源码消费者 API 导入/实例化：通过
- `python3 -m instaloader --version`：通过，输出 `4.15.1`
- 上游测试：上游 sdist 不含测试目录，测试数为 0
- 新增消费者测试：9/9 通过（8 个 smoke 断言 + 1 个 CLI `--version` 集成测试）
- `conan-verify instaloader 4.15.1`：通过
- W3 `build_and_test.sh instaloader/4.15.1`：通过
---

**编译结束**: 2026-09-25 23:29
**最终状态**: built
