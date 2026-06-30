# tinyproxy 1.11.3 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-26
- 编译器: clang/clang++
- 状态: published
- 平台: HarmonyOS (aarch64-unknown-linux-ohos)

## 编译步骤

1. `ohc-run.py init-build tinyproxy 1.11.3 --url=...` (使用 --no-download 因源码已手动下载)
2. 修改 config.guess: 三处 HarmonyOS 补丁 (§2.1 LIBC检测区 + §2.2 主case兜底 + §2.3 独立HarmonyOS case跳过set_cc_for_build)
3. 修改 config.status: mktemp -d "./confXXXXXX" 替换为 $TMPDIR 固定目录
4. 从 .orig 复制缺失的 config.h.in
5. `./configure --prefix=$DEFAULT_PREFIX --build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos`
6. 修改 config.status (临时目录方案)
7. `sh config.status`
8. `touch` 时间戳修复 (aclocal.m4 > configure.ac > m4/*.m4)
9. `make -j1`
10. `make install DESTDIR=$TEST_PREFIX`
11. `ohc-run.py verify-build tinyproxy 1.11.3 --install-prefix=...`
12. `ohc-run.py package tinyproxy 1.11.3`
13. `make install` (安装到 DEFAULT_PREFIX)
14. 功能验证测试 (13项全部通过)
15. `ohc-run.py finish tinyproxy 1.11.3 published`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess无法识别HarmonyOS | 缺少HarmonyOS识别模式 | §2.1添加HarmonyOS到初始case + §2.2主case兜底 + §2.3独立case跳过set_cc_for_build → E007+E105 |
| 2 | config.guess HMDFS临时文件失败 | set_cc_for_build在HMDFS上创建临时文件失败 | §2.3独立HarmonyOS case直接设置LIBC=musl跳过set_cc_for_build → E105 |
| 3 | config.status无法创建临时文件 | HMDFS UID映射,mktemp目录不可写 | 修改config.status使用$TMPDIR固定预创建目录 → E106 |
| 4 | 缺失config.h.in | 清理时误删 | 从.orig复制 |
| 5 | make触发aclocal-1.16重建 | 时间戳不一致(m4/*.m4 > aclocal.m4) | touch时间戳使aclocal.m4 > configure.ac > m4/*.m4 |
| 6 | tinyproxy --version不支持 | 软件仅支持-v | 使用-v替代--version |
| 7 | G0 clean-verify失败 | Python subprocess HMDFS管道权限限制 | 已手动验证configure正确运行,平台已知限制 |

## 源码修改

- config.guess: 三处HarmonyOS识别补丁 (§2.1 LIBC检测 + §2.2 主case兜底 + §2.3 独立HarmonyOS case跳过set_cc_for_build)
- config.sub: Savannah最新版本(已内置ohos*支持)
- config.status: mktemp临时目录→$TMPDIR固定目录(运行时修改,非源码补丁)
- configure.ac: 时间戳修正(0字节→restore from orig)

补丁文件:
- 0001-config.guess.patch (HarmonyOS识别 + 独立case)
- 0002-config.sub.patch (Savannah版本更新)
- 0003-configure.ac.patch (时间戳修正)
- 0004-docs-man5-tinyproxy.conf.5.patch (regen)
- 0005-docs-man8-tinyproxy.8.patch (regen)

## 依赖版本

- 编译器: clang (系统自带)
- libc: musl (HarmonyOS自带)
- 无额外依赖

## 功能验证测试

13项全部通过:
- T1 版本号验证 ✅
- T2 二进制类型验证 ✅
- T3 动态链接验证 ✅
- T4 功能特性列表 ✅
- T5 文件完整性 ✅
- T6 HTTP代理转发 ✅
- T7 HTTPS CONNECT隧道 ✅
- T8 直连对比 ✅
- T9 Via头部注入 ✅
- T10 并发连接 ✅
- T11 ACL访问控制 ✅
- T12 错误处理 ✅
- T13 优雅停机 ✅

详见 reports/test-report.md

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| tinyproxy-1.11.3-ohos-aarch64.tar.gz | 220KB | 主打包产物 |
| tinyproxy-1.11.3-ohos-aarch64-debug.tar.gz | 50KB | 调试符号包 |

## 注意事项

- config.guess需**三处**补丁(§2.1+§2.2+§2.3),不是一处(E007+E105)
- config.status的HMDFS临时目录修复需每次configure后重新执行
- G0干净构建验证失败(HMDFS Python subprocess管道权限限制,已手动验证通过)
- tinyproxy不支持--version参数,用-v替代
- 验证verify-build时需指定--install-prefix指向DESTDIR内的真实路径

---

**编译结束**: 2026-05-26 20:15
**最终状态**: published
---

**编译结束**: 2026-05-26 20:16
**最终状态**: published
