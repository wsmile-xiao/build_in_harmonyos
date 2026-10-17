# dehydrated 0.7.2 适配笔记（HarmonyOS PC · 纯 Bash 脚本应用打包）

## 定位
- dehydrated 是 dehydrated-io 的 ACME v2 客户端（Let's Encrypt/ZeroSSL 等），
  单个自包含 Bash 脚本（2492 行，bash 4+，一处 `declare -A`）。
- **纯 Bash 应用，无编译产物** → 走脚本打包路径（build_system: none），先例：archives/c/cvsweb/3.0.6。

## 关键适配
- **零补丁**：上游脚本在 OHOS 运行时无需修改，`patches_applied: []`。
- **自检即验证**：build() 做两步——`bash -n` 语法自检 + `--version` 冒烟
  （后者真实执行脚本内置 check_dependencies：grep/mktemp/diff/sed/awk/curl/cut/head/tail/hexdump/openssl + sed ERE 可用性探测），并 grep 核对版本输出。
- **test_package**：消费者视角校验 bin/dehydrated 存在/可执行/shebang、bash -n、
  --version 冒烟并核对 "Dehydrated version: 0.7.2"（6 项断言）。
- 上游无任何测试套件（见下方 discovery），如实声明 `upstream_tests: []`。

## 运行时依赖闭包（设备实测，2026-09-09）
bash 5.3.0（/data/service/hnp/bin/bash）、curl 8.8.0（/usr/bin/curl）、
openssl 3.0.9（/usr/bin/openssl，OPENSSLDIR=/system/etc）、gawk 5.4.0、
toybox 0.8.12（sed/grep/diff/mktemp/cut/head/tail）、hexdump（/data/service/hnp/bin）。
设备默认 PATH 已含 /data/service/hnp/bin 与 /usr/bin，闭包齐备。

## 风险点与实测结论
| # | 风险 | 实测/处置 |
|---|------|-----------|
| 1 | 脚本第 2485 行 `OSTYPE="$(uname)"`，设备返回 "HarmonyOS" != "Linux"，`_sed()`（line 852）走 `sed -E` 分支 | toybox sed 0.8.12 对 `-E`（ERE）实测可用（含 `\|` 交替），`--version` 冒烟中 `_sed` 路径已真实执行 |
| 2 | 证书操作时经 `openssl version -d` 探测 openssl.cnf（line 548） | 设备 openssl 3.0.9 → OPENSSLDIR=/system/etc；探测逻辑无需适配，仅签发证书时使用 |
| 3 | `getent` 在 OHOS 缺失 | 仅影响可选 DEHYDRATED_USER/DEHYDRATED_GROUP 降权特性（默认为空不触发），--version/自检不受影响 |
| 4 | OHOS hnp bash 在部分执行上下文（含 SSH 会话）getcwd() 失败 → 启动时内置 `PWD` 未定义，脚本 `set -u` 下 load_config `${PWD}`（line 348）报 "unbound variable" | 自检/测试显式传 `PWD=<目录>` 环境变量规避（已实测修复）；CI L2 直跑脚本最坏情况为 warn 级（非阻塞），conan build/test 上下文已显式传 PWD |
| 5 | 上游源在 github.com，设备直连偶发 curl exit 52 | CI mirror-fallback 会自动加 gh-proxy 镜像（conandata 保持官方 URL 不动）；设备侧已实测 gh-proxy 下载并校验 SHA256 一致 |

## 上游测试 discovery（NO_UPSTREAM_TESTS）

- **discovery.status**: EVIDENCE_COMPLETE
- **结论**: 上游（dehydrated-io/dehydrated，v0.7.2 与 master）不发布任何测试套件，无可运行的官方测试。
- **已检查入口/证据**:
  1. 官方 release 归档 v0.7.2 全量文件清单（15 项）：dehydrated 脚本、README.md、CHANGELOG、LICENSE、.gitignore、.github/FUNDING.yml、docs/（11 个 md 文档 + man 页 + examples{config,domains.txt,hook.sh} + logo.png）——无 test/、无 Makefile、无 CI workflow、无测试运行器配置。
  2. README.md、CHANGELOG 全文 grep "test"：零命中（无测试入口/开发测试说明）。
  3. docs/examples/hook.sh 为部署 hook 示例（deploy_cert 等），非测试套件。
  4. .github/ 仅 FUNDING.yml（无 workflows/）。
  5. 上游 master 分支结构同 v0.7.2（Scout 调查：无 test/、无 Makefile、无 CI workflow）。
- **替代验证（已实际执行）**: `bash -n` 语法自检 + `./dehydrated --version` 冒烟
  （VERSION 硬编码于脚本第 20 行，输出 "Dehydrated version: 0.7.2"；
  --version 内部真实执行 check_dependencies 全部依赖探测）。
- **证据路径**: 本机归档与清单 `D:/ohos_zcode/runs-v2/dehydrated-0.7.2/scout/`
  （release-tar-listing.txt、tag-tar-listing.txt、upstream-src/）；
  设备归档副本 `/storage/Users/currentUser/tmp/oh-device-porting-v2/dehydrated-0.7.2/`
  （SHA256=7ea5a75bfcdf04bbb6ef88d03f89dec8101a2d3ea1dd467d8c42cbb0339ed5cb，与本地、Scout 三方一致）。

## 编译步骤

```bash
conan create archives/d/dehydrated/0.7.2 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64

# 配方内 build()：纯 Bash 脚本无编译，仅做自检
cd $source_folder && bash -n dehydrated && bash dehydrated --version
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/dehydrated | 主脚本（755，#!/usr/bin/env bash） |
| licenses/LICENSE | MIT 许可证 |
| share/doc/dehydrated/ | README.md、CHANGELOG、docs/（md 文档、man 页、examples） |

## 注意事项

- R38：package_type="application" 且产出到 bin/ → commands.json 已声明（binary: false，脚本应用）。
- R26：纯脚本无 .so 产物，系统同名库隔离不适用。
- 实际签发证书需网络与 ACME 账户语义（用户态使用场景），本包交付可运行脚本与文档；
  test_package 验证脚本可执行性与内置依赖闭包，不做真实 ACME 网络请求。
- CI 跑后须核验 conandata.yml 与 HEAD 逐字节一致（E415：mirror-fallback 原地改写需恢复）。

---

**编译结束**: 2026-09-09
**最终状态**: built
