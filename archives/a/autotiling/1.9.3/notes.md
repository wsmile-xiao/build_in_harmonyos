# autotiling 1.9.3 适配笔记

## 编译环境
- 构建系统: python (pip install, setuptools/PEP 517)
- 编译日期: 2026-08-21
- Python版本: 3.12.x（OHOS 真机）
- 目标平台: HarmonyOS PC aarch64

## 适配过程
1. 上游源：PyPI sdist autotiling-1.9.3.tar.gz（官方源，R39 合规）
   - URL / sha256 见 conandata.yml（已实测 sha256sum 一致）
2. 配方：package_type="application"，纯 Python noarch（settings 仅 os/arch，无编译器）
   - build(): `pip install . --prefix=<stage>`，console_scripts `autotiling` 落 stage/bin
   - 运行依赖 i3ipc（>=2.0.1）未发布为 conan 配方 → 由 pip 从 pypi.cnb.cool 镜像
     解析并装入同一 site-packages（airthings-ble 同模式，不声明 conan requires）
   - package(): 整棵 stage 树复制（含 site-packages 与 bin/）
   - package_info(): runenv/buildenv 注入 PYTHONPATH + PATH(bin)
3. test_package：真实调用被测包 API（R34），无需 i3/sway 运行环境
   - import autotiling + __version__ == "1.9.3"
   - get_parser() 构造 ArgumentParser；真实解析 -w/-sr/-e 参数并校验
   - save_string() 文件写入往返；temp_dir() 非空
   - bin/autotiling --version / -h（argparse 动作，不连接 i3 IPC，退出码 0）
   - 输出 HMBS_TEST_PACKAGE_RESULT（discovered/passedCount = 实际检查数）与
     HMBS_UPSTREAM_TEST_RESULT（status=no_tests，reason 见 MANIFEST.yml 审计）

## 上游测试审计（no_tests 判定依据）
autotiling 1.9.3 上游**无任何测试套件**：
- PyPI sdist：仅 autotiling/ 包 + setup.py/setup.cfg/pyproject.toml/README/LICENSE，
  无 tests/ 目录、无测试文件
- GitHub v1.9.3 源码树：顶层无 tests/ 目录（仅 .github/、autotiling/、文档与构建文件）
- Makefile：仅有 upload/tag/publish/clean/format/black/lint 目标，无 check/test 目标
- main.py（214 行）：无 assert 断言（hmbs 清单探测不会误判）
- 因此 MANIFEST.yml 写 `upstream_tests_exist: false` + 非空 upstream_test_audit，
  test_package 输出 status=no_tests、discovered=0、executed=0 及具体 reason
  （符合 hmbs 规则：确无测试才可用 no_tests，显式审计为证）

## 验证命令（真机）
```bash
conan create . -pr=ohos-aarch64
# test_package 自动运行 test_autotiling.py + CLI 冒烟
# 预期输出：HMBS_TEST_PACKAGE_RESULT discovered=7 passedCount=7
#           HMBS_UPSTREAM_TEST_RESULT status=no_tests discovered=0 executed=0
```

## 注意事项
- i3ipc 需可从 pypi.cnb.cool 镜像解析（pip 构建期依赖）；若镜像缺失需补 vendoring
- 真机无 sway/i3 环境，测试只覆盖与窗口管理器无关的 API 与 argparse 冒烟路径；
  连接类逻辑（switch_splitting/Connection）依赖实际 i3/sway，未纳入 test_package
- 工具类型：软件级 commands.json 已声明（R38）
