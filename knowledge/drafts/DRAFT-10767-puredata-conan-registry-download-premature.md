# DRAFT-10767-puredata-conan-registry-download-premature

## 摘要

conan create 在安装 tool_requires/build_requires 的**预编译二进制包**时，从 ohpcd 制品仓
（conan.cnb.cool）拉取 `conan_package.tgz` 传输被中途断开，报：

```
perl/5.42.2: WARN: network: Download failed, check server, possibly try again
Response ended prematurely
perl/5.42.2: ERROR: Exception: <class 'conan.internal.errors.ConanConnectionError'>
Download failed, check server, possibly try again
Response ended prematurely. [Remote: ohpcd]
ERROR: Download failed, check server, possibly try again
```

## 关键判定：这是环境/网络问题，不是配方缺陷

失败发生在 `conan create` 的 **"Downloading binary packages"（依赖安装阶段）**，
位于 recipe 的 `build()` **之前**——配方与源码尚未参与执行。因此：

- 修改 conanfile / 补丁 **不会**影响该下载结果；
- 本地环境只要缓存命中了该依赖二进制，就**不会**复现 → 这是"本地通过、CI 失败"
  最常见的一类核心差异。

## 失败点（CI #59420，puredata/0.54.1 实测）

1. `perl/5.42.2` 的 17MB 二进制包下载两次均 `Response ended prematurely`；
2. 同批其余 4 个小包（autoconf/automake/libtool/m4）全部正常下载 →
   判定为**传输中断**而非制品缺失；
3. 同一包从正常网络路径 `conan download` **15 秒下载成功**（17.0MB），制品仓健康。

> 附带环境差异：CI worker PATH 缺 `curl`，pre-download 步骤报
> `[Errno 2] No such file or directory: 'curl'` 降级（conan 自身下载兜底，非致命，
> 但同样是 worker 环境与本地不一致的证据）。

## 推荐解法（rec_approach: verify-infra-then-retry）

1. **看日志定位阶段**：确认失败在 "Downloading binary packages"、`build()` 之前；
2. **验证制品仓**：全新 `CONAN_HOME` 下 `conan download` 同一包，能下=纯瞬时网络问题；
3. **重跑 CI**：PR 评论 `/rebuild` 触发（R42：CI 评论触发型，**push 本身不触发**）。

```bash
CONAN_HOME=$(mktemp -d) conan remote add ohpcd https://conan.cnb.cool/OpenHarmonyPCDeveloper/Conan/-/packages/
CONAN_HOME=$(mktemp -d) conan download \
  "perl/5.42.2#13c4f5bde5668df0b7268c4d0c01073c:6b129b068851896169fae42d399fa922d239ce8a" -r ohpcd
```

## 兜底解法（fallback: preseed-worker-conan-cache）

worker 到制品仓链路长期不稳时，在网络正常的主机预下载依赖并复制进 worker 缓存，
使 CI 不依赖实时下载；仍持续失败按 R41 外部阻塞止损上报，禁止无限重试。

## 禁止项

- 禁止把该网络错误误诊为配方问题，盲改 conanfile/补丁后重推（浪费 CI 额度）；
- 禁止用 `--build=missing` 试图"从源码补包"——错误是传输中断非缺包，源码编译
  大型工具链（perl）反而更慢更易失败。
