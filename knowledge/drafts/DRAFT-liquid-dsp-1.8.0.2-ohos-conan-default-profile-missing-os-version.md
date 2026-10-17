# DRAFT — OHOS conan 的 `default` profile 缺 `os.version` 导致 `conan create` 直接 Invalid

> 状态：**draft（草稿）**，尚未由主编审核合入正式图谱。
> 关联条目：`DRAFT-glpk-4.65-ohos-conan-os-version-rm-safe`（同族但不同根因）。
> 触发事件：liquid-dsp 1.8.0.2 适配 HarmonyOS PC（aarch64 真机，Conan 2.29.1 OHOS 适配版）。

## 现象

本地直接用 `default` profile 执行 conan create，构型尚未开始即失败：

```text
$ conan create archives/l/liquid-dsp/1.8.0.2 --profile=default
...
======== Computing necessary packages ========
Requirements
    liquid-dsp/1.8.0.2#147c5d5704217ed461c2753918b7d1dc:007139a8b4a9838149292ea93f6e14b41f10f966 - Invalid
ERROR: There are invalid packages:
liquid-dsp/1.8.0.2: Invalid: 'settings.os.version' value not defined
exit code: 6
```

注意失败点是 **Computing necessary packages**，而不是 configure/build：
日志里没有任何编译器输出，也没有 CMake 报错，容易被误判为配方或源码问题。

## 根因

OHOS 适配版 conan 的 `settings.yml` 为 `os=OHOS` 定义了 `version` 子设置，
因此 `package_id` 计算会对 settings 树做 `validate()`：凡是被判定为「已知子设置
但未给出取值」的字段，整个包直接标为 `Invalid`。

本机的 `default` profile 只声明了：

```ini
[settings]
arch=armv8
build_type=Release
compiler=clang
compiler.cppstd=gnu14
compiler.libcxx=libstdc++11
compiler.version=15
os=OHOS          # ← 没有 os.version
```

而仓库自带的 CI profile 是完整的：

```ini
# ci/conan/profiles/ohos-aarch64
os=OHOS
os.version=6.0
arch=armv8
compiler=clang
compiler.version=15
compiler.libcxx=libc++
compiler.cppstd=17
```

## 与 `DRAFT-glpk-4.65-ohos-conan-os-version-rm-safe` 的区别

| 条目 | 场景 | 修复面 |
|---|---|---|
| glpk 草稿 | profile **有** `os.version`，配方 `settings` 未声明该子设置 | 配方里 `rm_safe` |
| **本条目** | profile **本身没有** `os.version` | 修 profile（换用 CI 同源 profile） |

本条目明确**不推荐**在配方里 `rm_safe` 掉 `os.version`：那只是让单个包不再报错，
却掩盖了「本地 profile 与 CI profile 不一致」这一环境事实，后续包会重复踩坑。

## 修复

使用与 CI 同源的 profile，host 与 build 同时指定：

```bash
conan create archives/<letter>/<pkg>/<ver> \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64
```

验证（liquid-dsp 1.8.0.2 实测）：

```text
exit code: 0   elapsed: 240s
1/1 Test #1: autotest .........................   Passed  140.56 sec
liquid-dsp/1.8.0.2: Package '4b977264131a1c74e82bd6bb51b63cc9aadc4cfa' created
[OHOS-1] PASS / [OHOS-2] PASS / [OHOS-3] PASS   → test_package 6/6
```

## 检查清单

1. `conan profile show -pr=default` 确认是否存在 `os.version`。
2. `conan profile show -pr=ohos-aarch64` 确认 `os.version` / `libcxx` / `cppstd`。
3. 本地 verifier、W3、手工复跑一律使用 `ci/conan/profiles/ohos-aarch64`，
   使本地结果与 CI 具备同一环境语义。
4. 不要在配方里 `rm_safe` `os.version` 来"修好"本地复跑。
