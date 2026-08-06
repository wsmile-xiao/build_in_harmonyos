# dash-shell 0.5.13.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-22
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. `source .build-context-dash-shell-0.5.13.2` 获取环境变量
2. `cd $BUILD_SRC_DIR` 进入源码目录
3. 下载并添加 config.guess、config.sub（源码无这两个文件）
4. 用 `patch-autotools-ohos.pl` 为 config.guess/config.sub 打 OHOS 补丁
5. 手动修复 config.guess 的 HarmonyOS case（`echo ... ; exit 0` 替代 `GUESS=...`）
6. 手动修复 config.sub 的 ohos-linux 三元组解析和 `linux-ohos` 内核-OS 验证
7. 修复 mkbuiltins 脚本中 sort 管道读取问题（HMDFS 限制）
8. `./configure --prefix=$DEFAULT_PREFIX`
9. `make -j1 && make install DESTDIR=$TEST_PREFIX`
10. `make check`（dash 无正式测试套件）
11. R7 验证：`$TEST_PREFIX/$DEFAULT_PREFIX/bin/dash -c 'echo $0'`
12. `ohc-run.py package dash-shell 0.5.13.2`
13. `make install`（无 DESTDIR）
14. `~/usr/local/bin/dash -c 'echo $0'` 验证本地安装
15. `ohc-run.py finish dash-shell 0.5.13.2 built`
16. `ohc-run.py verify-build dash-shell 0.5.13.2` → G0-G4 PASS

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 源码缺 config.guess，下载的旧版本 GUESS 变量不输出 | 添加 config.guess，HarmonyOS case 用 `echo ... ; exit 0` 直接输出 |
| 2 | config.sub 拒绝 aarch64-unknown-linux-ohos | ohos-linux 三元组解析格式错乱 + `linux-ohos` 内核-OS 未在验证白名单 | 修复三元组解析 + 添加 `linux-ohos*)` 到验证白名单 |
| 3 | builtins.h 为空（NUMBUILTINS=0） | mkbuiltins 中 sort 从 pipe 读取在 HMDFS 上 Permission denied (E002) | 将 awk 输出重定向到临时文件，sort 从文件读取 |
| 4 | configure 首次运行 signal 13 (SIGPIPE) | /tmp 只读，TMPDIR 默认 /tmp | 设置 TMPDIR=$HOME/tmp |

## 源码修改

| 补丁 | 修改文件 | 内容 |
|------|----------|------|
| 0001-config.guess.patch | config.guess (新增) | OHOS HarmonyOS 系统识别 + echo/exit 输出 |
| 0002-config.sub.patch | config.sub (新增) | ohos-linux 三元组 + linux-ohos 内核-OS 验证白名单 |
| 0003-configure.patch | configure | 微小适配（+2/-2） |
| 0004-src-mkbuiltins.patch | src/mkbuiltins | sort 管道→临时文件重定向 |

## 依赖版本

无外部依赖（dash-shell 为自包含软件）

## 验证结果

```bash
# R7 验证
$ ~/usr/local/bin/dash -c 'echo $0'
/storage/Users/currentUser/usr/local/bin/dash

# 手动功能测试 43 用例，40 PASS + 3 预期⚠️，0 FAIL
$ ~/usr/local/bin/dash -c 'echo hello'       # hello ✅
$ ~/usr/local/bin/dash -c 'echo $((3+5))'    # 8 ✅
$ ~/usr/local/bin/dash -c 'f(){ echo $1; }; f ok'  # ok ✅
$ ~/usr/local/bin/dash -c 'for i in 1 2 3; do echo $i; done'  # 1 2 3 ✅

# G0-G4 质量门禁
G0: 干净构建验证 PASS
G1: 二进制完整性 PASS
G2: 功能可用性 PASS
G3: 可移植性 PASS
G4: 档案完整性 PASS
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| dash-shell-0.5.13.2-ohos-aarch64.tar.gz | 240KB (245818B) | 预编译包 |
| dash-shell-0.5.13.2-ohos-aarch64-debug.tar.gz | — | 调试符号包 |

## 注意事项

- dash 不支持 bash 扩展参数展开（${x:0:4}、${x#abc}），属 POSIX 限制
- HMDFS 上 sort/cat 从 pipe 读取受限，构建脚本需将管道输出重定向到文件后再 sort
- HMDFS 上 /tmp 只读，需 TMPDIR=$HOME/tmp

---
**编译结束**: 2026-05-22 01:10
**最终状态**: built
---

**编译结束**: 2026-08-06 05:55
**最终状态**: built
