# DRAFT 知识条目（md 成对版）— 真机隔离 job 的 conan-home 默认只有 conancenter：必须写入 ohpcd remotes.json

> Status: DRAFT | 来源: tetraproc/0.9.2 真机 shadow CI 2026-10-04（r2 第 3 轮）

## 使用说明

真机隔离 job（`ohos-prepare-isolated-conan-job.sh`）新建的 `conan-home/`
**不会继承**本机或全局 conan 缓存的 remote 配置，默认 `remotes.json` 只有一个
**启用的 conancenter**。凡依赖只发布在 ohpcd 制品仓的包（libx11、clthreads、
clxclient、fftw3f、xorgproto 等几乎所有内部适配包），依赖解析必然失败。
本条给出一次性修复写法与判定指纹。

## 适用范围

- 所有真机 shadow CI 隔离 job（新建 conan-home 的场景）。
- 不适用：job 复用已有 conan-home、或 CI runner 脚本已预配 remote 的环境。

## 输入 / 输出

- 输入：`<job>/conan-home/remotes.json`（当前内容）、依赖列表。
- 输出：conancenter 禁用 + ohpcd 启用的 remotes.json；依赖能从 ohpcd 下载。

## 症状（失败指纹）

```text
libx11/1.8.13: Checking remote: conancenter
Connecting to remote 'conancenter' anonymously
ERROR: Package 'libx11/1.8.13' not resolved: Unable to find 'libx11/1.8.13'
       in remotes. Required by '<pkg>/<ver>'
```

判定要点：报错发生在 **Computing dependency graph** 阶段、且"Checking remote"
只出现 conancenter——不是依赖真的缺失（ohpcd 上都在），是 job 没配 ohpcd。

## 修复（写入 remotes.json，注意避免 heredoc：设备 /tmp 只读）

用本地生成 + scp 传输（**必须无 BOM**，`Set-Content -Encoding utf8` 在
Windows PowerShell 5 会带 BOM 导致 JSON 解析失败；用 UTF8Encoding($false)）：

```json
{"remotes":[
  {"name":"conancenter","url":"https://center2.conan.io","verify_ssl":true,"disabled":true},
  {"name":"ohpcd","url":"https://conan.cnb.cool/OpenHarmonyPCDeveloper/Conan/-/packages/","verify_ssl":true}
]}
```

（URL 以实际制品仓地址为准；conancenter 保留但 disabled，与成功 job 的配置一致。）

## 示例（本次实证）

- 修复前：`libx11/1.8.13 not resolved`（r2 第 2 轮 fail）。
- 写入 remotes.json 后：同轮日志出现大量 `Downloaded (ohpcd)`，
  libx11/clxclient/fftw3f 等 15 个依赖全部就位（r2 第 3 轮依赖解析通过）。

## 查重边界

- `opencsg-1.8.2-shadow-ci-isolated-job-hnp-toolchain-path`：讲 hnp 工具链
  不在 PATH（Error 127 找不到 cmake），非 remote 配置。
- `libsv-1.2-shadow-ci-runner-toolchain-path`：同为 PATH/工具链主题。
- `DRAFT-device-shadow-ci-repo-source-pruned-missing-ci`：讲 repo-source 缺 ci/。
  本条讲依赖解析的 remote 面——三个失败面互不相同、可同时发生。
