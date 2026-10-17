# DRAFT-cht.sh-pure-script-conan-ci-gates-commands-settings：纯脚本 conan 包的 CI 专属闸（L0k/L0p）在本地 conan create 不可见

> Contributor: atomcode | Team: - | Status: Draft | Updated: 2026-09-11
> Route: 路径 A（基础适配） | Source: cht.sh 0.0-git20220418.571377f 适配交付中发现的 CI 闸与本地验证的盲区

## 现象

cht.sh（纯 bash 脚本 CLI 客户端，无编译步骤）本地 `conan create`
（CI 同款 profile `ci/conan/profiles/ohos-aarch64` + `--build=missing`）
**exit 0、test_package 4 项断言 ALL TESTS PASSED**，但按
`ci/conan/build_and_test.sh` 的 L0 质量闸逐条复刻检查后发现两处必挂点，
本地 create 完全不会暴露：

1. **L0k (R38)**：`package_type = "application"` 且产出 `bin/cht.sh`
   可执行文件 → CI 强制要求软件级目录 `archives/c/cht.sh/commands.json`
   （type=tool、name 含包名、versions 含版本号）。缺失即
   `[fail] L0k: CLI tool detected but commands.json missing (R38)`。
2. **L0p**：`settings` 必须同时声明 `os/compiler/build_type/arch`
   四项。纯脚本包常写 `settings = "os", "arch"`（"无编译不需要
   compiler"）→ `[fail] L0p: settings 缺少 'compiler'`。

两处都导致 "本地通过、PR CI 失败"，且失败信息只出现在推送后的
CI 构建里，本地无任何警告。

## 根因

`conan create` 只做 构建 → 打包 → test_package 三步，**不跑**
build_and_test.sh 的 L0 质量闸（L0a-L0p）与 L1 日志验证。L0k 的
commands.json 要求、L0p 的 settings 四项要求都是脚本层 grep/python
检查，与 conan 引擎无关。纯脚本包恰恰最容易触发这两条：

- 没有 compiler 直觉，settings 写不全 → L0p；
- 产出 bin/ 工具但"只是脚本"，忘了 commands.json → L0k。

## 解决方案

1. **纯脚本 CLI 包 conanfile.py 固定写法**（对齐 strace 等工具包惯例）：
   `settings = "os", "compiler", "build_type", "arch"` 四项全声明
   （compiler/build_type 实际不使用，仅为 profile 兼容与 L0p）。
2. **凡产出 bin/ 可执行文件的包**（`package_type = "application"`
   或 package() 写 bin/），必须在软件级目录（`archives/<x>/<包名>/`）
   提供 `commands.json`，模板 `templates/commands.json.template`：
   `type: "tool"`、`name` 含包名、`versions` 含 `包名/版本` ref。
3. **推送前用 build_and_test.sh 的闸逻辑本地复刻**（零成本，无需跑
   完整 CI）：L0k 用 `ci/conan/detect_bindirs.py` 判定是否 CLI 工具
   + 校验 commands.json 三字段；L0p grep settings 行四项；L0m 校验
   目录 4 段结构与 slug 字符集；L0n 校验分支名精确等于
   `{包名}-{版本}`（可带 feat/ 等前缀，不许后缀）。
4. **L0j (R37) 预检**：推送前 `conan download 包/版本 -r=ohpcd
   --only-recipe`，404 = 首次发布安全；已存在则比对 recipe，
   有修改必须递增版本后缀。
5. **L1 无需处理**：test_package 经 `self.run(f"sh test.sh")` 真实
   执行（日志有 `Launching test_package` / `Running test()`），
   L1a 过；上游 tests/ 仅为手动快照无可执行框架时，
   `test_package/MANIFEST.yml` 声明 `upstream_test_in_build: false`
   即可（L1c 仅 info，不拦）。

## 验证

- 本地 `conan create`（CI 同款命令）exit 0，test_package 4 断言全过
- L0a/L0b/L0c/L0d/L0e/L0f/L0g/L0h/L0k/L0m/L0n/L0o/L0p 逐条复刻通过
- 制品仓 `conan download cht.sh/0.0-git20220418.571377f` 404
  → 首次发布，无 L0j 冲突
