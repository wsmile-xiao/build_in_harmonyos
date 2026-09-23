# dash-binsh 0.5.13.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-15
- 编译器: clang/clang++ 15.0.4 (OHOS aarch64)
- 状态: built

## 编译步骤

1. `source .build-context-dash-binsh-0.5.13.1` 获取环境变量
2. 源码: http://gondor.apana.org.au/~herbert/dash/files/dash-0.5.13.1.tar.gz (sha256 d9271bce09c127d9866e25c011582ddc75ab988958a04bc4d8553a3b8f30e370)
3. 下载并添加 config.guess、config.sub（源码无这两个文件）
4. 用 `patch-autotools-ohos.pl` 思路为 config.guess/config.sub 打 OHOS 补丁（HarmonyOS case + ohos-linux 三元组）
5. `./configure --prefix=$DEFAULT_PREFIX`
6. `make -j1 && make install DESTDIR=$TEST_PREFIX`
7. `make check`（dash 无正式测试套件，目标为空）
8. R7 验证: `$TEST_PREFIX/$DEFAULT_PREFIX/bin/dash -c 'echo $0'`
9. conan-init 生成配方,修正为 application 类型 + bindirs=bin
10. conan-verify: G1-G4 + W3 本地 CI 全通过
11. test_package 消费者用例 5 项断言 PASS

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 源码缺 config.guess | 添加 config.guess,OHOS case 用 `echo ... ; exit 0` 直接输出 |
| 2 | config.sub 拒绝 aarch64-unknown-linux-ohos | ohos-linux 三元组未在验证白名单 | 修复三元组解析 + `linux-ohos*` 白名单 |
| 3 | builtins.h 生成异常 | mkbuiltins 中 sort 从 pipe 读取在 HMDFS 上受限 | awk 输出重定向到临时文件,sort 从文件读取 |
| 4 | configure 临时目录 umask 077 失败 | HMDFS 权限语义差异 | 补丁改 umask 007 |
| 5 | /tmp 只读 | 平台限制 | TMPDIR=$HOME/tmp |
| 6 | refresh-patch 把构建产物当补丁 | 规则扫描把生成 .c/.h 当新增源码 | 用 edit-tracker 只追踪真实源码修改 |

## 源码修改

| 补丁 | 修改文件 | 内容 |
|------|----------|------|
| 0001-config.guess.patch | config.guess (新增) | OHOS HarmonyOS 系统识别 + echo/exit 输出 |
| 0002-config.sub.patch | config.sub (新增) | ohos-linux 三元组 + linux-ohos 内核-OS 验证白名单 |
| 0003-configure.patch | configure | 临时目录 umask 077→007 |
| 0004-src-mkbuiltins.patch | src/mkbuiltins | sort 管道→临时文件重定向 |

## 依赖版本

无外部依赖（dash 为自包含软件）

## 验证结果

```bash
# R7 验证
$ ~/usr/local/bin/dash -c 'echo $0'
/storage/Users/currentUser/usr/local/bin/dash

# 消费者用例 (test_package/test.sh, 5/5 PASS)
$ bash test.sh
PASS 1: arithmetic expansion -> 8
PASS 2: function/param expansion -> ok
PASS 3: for loop -> 1 2 3
PASS 4: command substitution -> subst-ok
PASS 5: $0 -> dash

# conan-verify G1-G4 + W3 本地 CI
conan create: PASS
W3 build_and_test.sh: PASS
```

## 注意事项

- dash 不支持 bash 扩展参数展开（${x:0:4} 等），属 POSIX 限制
- HMDFS 上 sort/cat 从 pipe 读取受限，构建脚本需将管道输出重定向到文件后再 sort
- OHOS 上 /system/bin/sh 无法执行 ELF，test_package 用 bash wrapper 调用被测二进制
- config.guess/config.sub 为新增文件补丁，格式必须是 `--- /dev/null` 才能被 Conan patch 应用

---
**编译结束**: 2026-09-15
**最终状态**: built
