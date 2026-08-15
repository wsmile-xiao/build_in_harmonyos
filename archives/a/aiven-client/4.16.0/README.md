# aiven-client

Aiven.io 官方命令行客户端 (avn)，纯 Python 包（hatchling + hatch-vcs 构建后端）。

- 版本: 4.16.0
- 许可证: Apache-2.0
- 上游仓库: https://github.com/aiven/aiven-client
- 构建系统: hatchling (纯 Python src layout: aiven/)
- 运行时依赖: requests, requests-toolbelt, certifi（由设备端 pip 环境提供）
- 适配平台: HarmonyOS PC (arm64) / Linux

## 构建

```bash
conan create archives/a/aiven-client/4.16.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
```

## 上游测试

`python3 -m pytest tests/ -v` → **223 passed in 40.48s** (100% 通过率)

## test_package smoke tests

7 项 smoke test 覆盖模块导入/版本/AivenClient/argx/pretty/speller/session，不依赖 pytest。
