# lsusb-laniksj 1.1.9 适配笔记

## 基本信息
- 上游: https://github.com/LanikSJ/lsusb
- 版本: 1.1.9 (2026-08-08 进入 Homebrew)
- 语言: 纯 Bash 脚本（单文件 445 行）
- License: MIT
- 构建: 无构建系统（无 Makefile/configure；Homebrew 直接安装脚本）

## 上游分析

### 构建系统
**无**。仓库只含 `lsusb` 脚本本体、`man/lsusb.8` 手册页与 GitHub CI 配置。
Homebrew formula（lsusb-laniksj.rb）做的事 = chmod +x + 拷贝到 bin。
因此 Conan 配方采用 scripts-only 模式（pipes-sh / dehydrated 先例）。

### libusb 依赖
**无**。脚本不调用 libusb，也不链接任何 C 库——它通过解析
`system_profiler` 文本输出模拟 Linux lsusb。本任务标题中的"libusb 依赖"
经源码核验为不存在，无需处理。

### USB/Linux 特有 API
**无 C API 调用**。脚本访问的 macOS 专有命令：
- `sw_vers -productVersion`（macOS 版本探测，选 SPUSBHostDataType/SPUSBDataType）
- `system_profiler $host_type`（USB 设备数据源；`-v` 直接透传其输出）
- `ioreg -p IOUSB -l -x`（Tahoe 无设备号时从 IO Registry 查 bus address）

### CLI 行为（实测矩阵，2026-09-20 于 HarmonyOS PC 目标环境）
| 调用 | 输出 | 退出码 |
|------|------|--------|
| `lsusb` | 空（无 USB 设备数据） | 0 |
| `lsusb -V` | `lsusb for macOS 1.1.9` | 0 |
| `lsusb -h` | Usage + 选项帮助 → stderr | 0 |
| `lsusb -s 001` | 空 | 1（过滤无匹配） |
| `lsusb -d 05ac:1234` | 空 | 1（过滤无匹配） |
| `lsusb -d 05ac`（无冒号） | Usage（语法错误） | 1 |
| `lsusb -t` | 空树 | 0 |
| `lsusb -v` | 空（system_profiler 不存在） | 0 |
| `lsusb -p` | 空 | 0 |
| `lsusb -x`（非法选项） | `lsusb: invalid option -- 'x'` + Usage → stderr | 0（上游 help() 固定 exitcode=0） |

无 `-s/-d` 过滤时即使无设备也退出 0（对齐 Linux lsusb）；带过滤则无匹配
退出 1——与 Linux lsusb 语义一致。

### 上游测试体系
**上游无正式测试套件**（0 个）。仓库无 test/ 目录、无 tests: 配置；
唯一"测试"是 CI workflow `.github/workflows/lsusb-test.yml`：
`macos-latest` 上运行一次 `./lsusb`（冒烟级别，仅验证默认调用可运行）。

## 适配过程

### HarmonyOS 适配要点
1. **零补丁**：脚本在 OHOS 上无需任何源码修改即可运行——所有 macOS
   专有命令探测均带 `2>/dev/null` 且失败路径优雅降级。
2. **解释器**：脚本 `#!/usr/bin/env bash` 且依赖 `shopt -s extglob` +
   `<<<` here-string + `getopts`，必须用真 Bash 执行；
   `/system/bin/sh`（mksh）不支持 extglob。CI worker 上 Bash 位于
   `/data/service/hnp/bin`（不在 PATH），用 `BASH` env → `which bash` →
   绝对路径兜底链解析（dehydrated 先例）。
3. **HMDFS chmod**：build()/package() 中显式 `os.chmod(0o755)`。
4. **下载**：设备直连 github.com 超时频发，conandata.yml 官方源在前 +
   gh-proxy 镜像 fallback（R39）。

### 上游测试执行记录（全部真实执行，无凭判断跳过）
| 上游测试 | 执行方式 | 结果 |
|----------|----------|------|
| `./lsusb`（CI 冒烟，macos-latest） | `conan create` build() 内 `bash lsusb` + test_package 再次执行 | ✅ 通过（无 USB 数据环境下降级为空输出、退出 0，与 macOS 无设备时行为一致） |
| （上游无其他测试） | — | 上游正式测试计数 = 0（CI 冒烟为唯一测试性检查） |

上游测试**不依赖真实 USB 设备**：脚本数据源是 `system_profiler` 文本输出，
在无该命令的环境（HarmonyOS）直接得到空数据集，行为确定可断言。

## 源码修改
无（零补丁适配）。

## 验证结果

```bash
# conan create --profile ohos-aarch64（本地目标环境，见 reports/）
bash -n lsusb                          # 语法 OK
bash lsusb                             # 上游 CI 冒烟，exit 0
bash lsusb -V | grep "lsusb for macOS 1.1.9"   # 版本冒烟 OK
python3 test_lsusb.py <pkg_root>       # 24/24 断言通过
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | scripts-only 配方（application，package_id 清空） |
| conandata.yml | 官方源 + gh-proxy 镜像，sha256 已填 |
| test_package/ | 上游冒烟真实执行 + HarmonyOS 专项测试 + CLI 矩阵（24 断言） |
| commands.json | 声明 lsusb 命令（R38 tool 类型） |

## 注意事项
- `-v` 在 OHOS 上输出为空（system_profiler 缺失），这是上游设计行为，
  不是适配缺陷；`-d/-s` 过滤无匹配时退出 1 亦为 Linux lsusb 对齐语义。
- 若未来在 OHOS 上需要真实 USB 设备列举，应改用 usbutils（libusb 路线，
  已有归档）；本包仅提供脚本语义的 lsusb。

---

**conan create 验证**（2026-09-20，ohos-aarch64 host/build profile）:

```
conan create archives/l/lsusb-laniksj/1.1.9 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64
→ rc=0，export → source → build（bash -n + ./lsusb + -V 版本冒烟）→ package（4 文件）
→ test_package 24/24 断言通过（0 失败）
包 ID: da39a3ee5e6b4b0d3255bfef95601890afd80709（scripts-only，settings 清空）
```

**编译结束**: 2026-09-20
**最终状态**: built
