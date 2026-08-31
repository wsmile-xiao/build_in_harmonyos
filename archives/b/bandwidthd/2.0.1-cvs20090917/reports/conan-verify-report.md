# Conan Verify Report — bandwidthd 2.0.1-cvs20090917

**Verdict**: PASS
**Reference**: `bandwidthd/2.0.1-cvs20090917@ohpcd/stable`
**Profile**: ohos-aarch64
**Date**: 2026-08-26T20:17:00.938069

## W3: ✅ PASS — real OHOS worker

在真实 OpenHarmony PC arm64 worker（SSH alias `hm`）执行：

```bash
conan create archives/b/bandwidthd/2.0.1-cvs20090917 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

- `conan create` 返回码：`0`
- `test_package` 返回码：`0`
- 测试输出：`bandwidthd CLI checks passed`
- 通过项：`bandwidthd --help`、`bandwidthd -c <temp-config> -l`，共 `2/2`
- 运行适配：test_package 将已安装 ELF 复制到 `/data/storage/el1/base`，用 `binary-sign-tool -selfSign 1` 签名后执行，满足 OHOS worker 的 HMDFS 执行策略。

该 W3 结果是实际 OHOS worker 的构建和运行证据；WSL/QEMU 的 loader/runtime 限制不再作为本包的阻塞项。

## G0: ✅ PASS
  📦 构建系统: autotools
  ✅ 已知风险 E007 已在配方中处理
     GNU config.guess 脚本不包含 HarmonyOS/__OHOS__ 检测分支。
uname -s 返回 HarmonyOS 无法匹配任何已知系统模式,
configure 在第一阶段就

## G1: ✅ PASS
  ✅ name 声明
  ✅ version 声明
  ✅ source() 方法
  ✅ build() 方法
  ✅ package() 方法
  ✅ package_info() 方法
  ✅ export_sources() 方法
  ✅ 补丁应用调用
  ℹ️ R26: 未检测到静态链接配置（非系统同名库无需静态）
  ✅ conandata.yml 完整
  ✅ test_package/ 存在 (R28)
  ✅ test_package/MANIFEST.yml 存在

## G2: ✅ PASS
  ✅ conan create 成功
  📄 日志: archives/b/bandwidthd/2.0.1-cvs20090917/reports/conan-create.log

## G3: ✅ PASS
  ℹ️ 无 lib/ 目录（纯可执行包）
  ✅ 无系统同名库冲突（R26 通过）

## G4: ✅ PASS
  ⚠️ 无法找到程序包 ID

## L2: ✅ PASS
  ⏭️ 跳过（无 cache 路径）

## L4: ✅ PASS
  ⏭️ 跳过（无 cache 路径）

## L5: ✅ PASS
  ⏭️ 跳过（无 cache 路径）
