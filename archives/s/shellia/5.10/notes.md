# shellia 5.10 适配笔记

## 编译环境
- 构建系统: plain Makefile（无 configure，纯 shell 库无 C 编译）
- 编译日期: 2026-09-18
- 编译器: 无（纯 Shell 脚本库 + rst2man 生成 man 页）
- 状态: published（conan-verify 全绿 + W3 本地 CI 通过）

## 上游确认（重要）
- 任务指定版本 5.10 真实存在：shellia 是 Debian 官方包（deb.debian.org pool），sid/forky 分支版本恰为 5.10
- 谷歌 search-url 初查返回的 Savannah URL（download.savannah.nongnu.org/releases/shellia/）是**误报**：
  search_url.py 的 `code in (200,302)` 判定把 HEAD 302 当成功，但跟随重定向后镜像实际 404
- 决定性线索：archives/b/bootcd/6.11.1/notes.md 记录 "OHOS 缺 shellia（/usr/share/shellia/ia 不存在）"，
  bootcdmk2diskconf 工具依赖 shellia 的 /usr/share/shellia/ia 数据文件
- Debian sources API 确认版本线：5.10（sid/forky）、5.9（trixie）、5.7.6（bookworm）、5.6.5（bullseye）、5.3.2（buster）
- 源码 tar.xz：https://deb.debian.org/debian/pool/main/s/shellia/shellia_5.10.tar.xz
- sha256（dsc 核对）：cdd0d5629cc3033b5ec553ce2d1409e576339c8a429416d650d2a08678d3bebc

## 编译步骤
纯 shell 库，无 configure/CMake。构建仅：
1. 本地验证 `make`（生成 man 页，需 rst2man=python3-docutils；CI 中跳过 man 页生成，仅打包 ia* 库文件）
2. 安装产物 = 8 个 ia* 文件 → share/shellia/（对应上游 /usr/share/shellia/）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | search-url 工具给 Savannah URL 但下载 404 | 工具把 HEAD 302 当"存在"，未跟随重定向验证 | 通过 bootcd 归档线索 + Debian sources API 确认真实上游 |
| 2 | Python urlopen SSL CERTIFICATE_VERIFY_FAILED | 系统 CA 路径未配置到 Python | SSL_CERT_FILE=/etc/ssl/certs/cacert.pem（OHE 环境已有该 CA 文件） |
| 3 | 上游测试大量 ERROR（bash 下 47） | OHOS toybox 与 GNU 工具差异（sed/head/base64/time），tstlib 测试框架假定 GNU coreutils | 3 个运行库补丁修复 ia.*（见下）；测试框架层差异记录为平台限制（详见验证结果） |
| 4 | `SED --unbuffered` 报 Unknown option | toybox sed 不支持 --unbuffered | 0002-ia.basic.patch：去除 --unbuffered（仅缓冲性能差异，转义结果一致） |
| 5 | `base64 -d -w 0` 报 No 'w' with 'd' | toybox base64 decode 模式不支持 -w | 0001-ia.array.patch：decode 时去掉 -w 0（GNU 下 -w 在 decode 无意义） |
| 6 | `touch /dev/null` Operation not permitted | OHOS 平台限制（/dev/null 不可 touch） | 0003-ia.log.patch：ia_logfile=/dev/null 时跳过 touch 探测 |
| 7 | （不纳入补丁）tstlib 修改无法生成补丁 | 上游 tstlib 的 `sed "s/\\n/\r/g"` 含真实 CR 字节，refresh-patch 用系统 `patch --dry-run -p1` 校验必失败（difflib 上下文含 CR 行），finish 重建补丁目录会删掉手工补丁 | 不修改测试框架 tstlib；其 toybox 差异（head -n -1、time -f 等）记录为平台限制，用自研 test_package 断言覆盖核心功能 |

## 源码修改

patches/（3 个，toybox 兼容，均为运行库 ia.* 的必要适配）：
- 0001-ia.array.patch：`base64 -d -w 0` → `base64 -d`
- 0002-ia.basic.patch：`$SED --unbuffered` → `$SED`
- 0003-ia.log.patch：`[ "$ia_logfile" != "/dev/null" ] && ! touch` 守卫

## 依赖版本

无 conan 库依赖（纯 Shell 脚本库）。运行时依赖系统 shell（bash/sh）与 toybox 基础工具；
测试额外依赖 bash、busybox sh（dash/mksh/posh 在 OHOS 不存在 → 平台限制）。

## 验证结果

```bash
# conan-verify shellia 5.10 → G0-G4/L2/L4/L5 全部 PASS（3 补丁真实应用成功）
# test_package：test_shellia.sh 断言 6 项全部 PASS（ia* 库存在+非空 / bash source ia 成功 /
#                 ia_set2var 可解析 / ia_easy_backslash 转义正确 /
#                 ia_arr base64 编解码往返[0001 补丁锁定] / ia_check_logfile /dev/null 守卫[0003 补丁锁定]）

# 上游测试 run_tests（R51 三步法，patch 后实测）：
#   run_tests 驱动 62 个 test.* × 5 种 shell（bash/dash/busybox sh/mksh/posh）
#   bash 下实测：3 OK / 47 ERROR / 12 WARN
#   dash/mksh/posh：OHOS 无该 shell → 平台限制无法运行
#   ERROR 根因分类（均为测试框架 tstlib 对 GNU coreutils 的依赖，toybox 不兼容）：
#     a) tstlib check() 调用 /usr/bin/time -f（toybox time 无 -f）→ 规划显示失败
#     b) tstlib 用 head -n -1 / tail -1 提取（toybox head 不支持负数行号）
#     c) 依赖 dash/mksh/posh 的具体行为差异（shell 本身不存在）
#   WARN（12）：sshd2222 相关测试，sshd2222 不可用（无 ssh）→ 上游脚本主动跳过
#   ia.* 运行库本身的 toybox 差异已由 3 个补丁修复，test_package 断言验证通过
```

## 注意事项
- shellia 是纯 shell 库，conan 包只安装 ia* 到 share/shellia/（下游 bootcd 按 /usr/share/shellia/ia 引用）
- 上游 Makefile 的 all 目标依赖 rst2man（python3-docutils），CI 构建跳过 man 页生成，不属于运行库产物
- 上游 tstlib（测试框架）含真实 CR 字节行，refresh-patch 工具无法为其生成补丁（系统 patch 校验限制）——属工具/上游文件格式的客观限制，不作为补丁提交
---

**编译结束**: 2026-09-19 00:42
**最终状态**: published
