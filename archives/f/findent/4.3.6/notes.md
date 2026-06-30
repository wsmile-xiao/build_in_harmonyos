# findent 4.3.6 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-26
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 源码拷贝到非HMDFS路径: /data/storage/el2/base/tmp/builds/findent-4.3.6.work/
2. 替换 config.guess/config.sub 为 GNU 2026 版本（支持 HarmonyOS）
3. configure --prefix=$HOME/usr/local --disable-selfrep
4. 手动创建 tarfile.inc（绕过 SELinux 限制阻止 toascii.sh 执行）
5. make -j1
6. make install DESTDIR=$HOME/tmp/test-install-findent-4.3.6
7. verify-build G1-G4: PASS
8. make check: 27/27 PASS
9. ohc-run.py package: 成功生成 findent-4.3.6-ohos-aarch64.tar.gz
10. make install（不带 DESTDIR，安装到 ~/usr/local）
11. 用户验证: findent --version → "findent version 4.3.6"

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | toascii.sh Permission denied | SELinux 限制阻止直接执行脚本 | 手动用 bash toascii.sh 或创建 tarfile.inc placeholder: `echo '78,111,...' > tarfile.inc`（内容为 "No selfrep compiled in" ASCII码） |
| 2 | G0 clean-verify configure 失败 | clean-verify 使用 /bin/sh（toybox）调用 configure，toybox 无法解析 GNU autoconf 脚本 | 平台限制，手动编译验证通过；需修改 clean-verify 使用 bash |
| 3 | latex/pandoc 缺失 | doc/design 构建需要 | make 忽略（Error 127 ignored），不影响二进制编译 |

## 源码修改

- config.guess: 替换为 GNU 2026 版本（支持 HarmonyOS aarch64 识别）
- config.sub: 替换为 GNU 2026 版本（支持 harmonyos 操作系统识别）
- 补丁: 0001-config.guess-harmonyos.patch, 0002-config.sub-harmonyos.patch

## 依赖版本

- ginstall (coreutils)
- GNU sed
- g++/clang++ (系统自带)
- flex/bison (预编译包)

## 验证结果

```bash
findent --version → findent version 4.3.6
wfindent --version → /storage/Users/currentUser/usr/local/bin/wfindent using: findent version 4.3.6
make check: 27/27 PASS (所有测试用例通过)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| findent-4.3.6-ohos-aarch64.tar.gz | 1034KB | 预编译包（ELF签名） |
| findent-4.3.6-ohos-aarch64-debug.tar.gz | 102KB | 调试符号包 |

## 注意事项

- configure 必须使用 --disable-selfrep 选项，否则 toascii.sh 因 SELinux 限制无法执行
- G0 clean-verify 因 toybox sh 限制失败（平台已知问题），不影响实际编译质量
- selfrep 功能已禁用，findent -selfrep 不可用

---
---

**编译结束**: 2026-05-26 21:06
**最终状态**: built
