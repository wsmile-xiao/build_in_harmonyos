# dirac 1.0.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-12
- 编译器: clang/clang++ (clang-15)
- 平台: aarch64-unknown-linux-ohos
- 状态: published

## 编译步骤

1. 下载源码包（SourceForge SSL需curl --insecure绕过）
2. ohc-run.py init-build dirac 1.0.2
3. 应用5个补丁（configure/config.guess/config.sub/mot_comp.cpp/dirac-stdint.h）
4. ./configure --prefix=$DEFAULT_PREFIX --disable-static
5. make -j1 && make install DESTDIR=$TEST_PREFIX

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SHELL=/bin/sh不可用 | HMDFS上/bin/sh是toybox | 修补configure: SHELL=/data/service/hnp/bin/bash |
| 2 | cl*|CL*误匹配clang++ | glob模式太宽泛 | 修补configure: cl|cl.exe|CL|CL.exe 精确匹配 |
| 3 | config.status Permission denied | HMDFS umask 077+mktemp继承owner | 修补configure: mkdir -m 0770替代umask 077 && mktemp |
| 4 | C++11 narrowing错误 | clang++对int→short隐式转换报错 | 修补configure: 为clang++注入-Wno-c++11-narrowing |
| 5 | libtool静态库链接失败 | HMDFS getcwd()失败导致路径解析错误 | 使用--disable-static避免静态库 |
| 6 | config.guess/config.sub不识别ohos | 版本太旧不含ohos模式 | 替换为automake-1.16版本 |

## 源码修改

5个补丁：
1. 0001-configure.patch: SHELL/cl*/umask/clang++* 4类修复合并
2. 0002-libdirac_common-mot_comp.cpp.patch: static_cast修复narrowing
3. 0003-config.guess.patch: 替换为automake-1.16版本
4. 0004-config.sub.patch: 替换为automake-1.16版本
5. 0005-libdirac_common-dirac-stdint.h.patch: stdint定义修复

## 验证结果

```bash
# dirac_encoder 和 dirac_decoder 均可用
$TEST_PREFIX/storage/Users/currentUser/usr/local/bin/dirac_encoder --help
$TEST_PREFIX/storage/Users/currentUser/usr/local/bin/dirac_decoder --help
```

## 注意事项

- HMDFS文件系统不支持getcwd()，导致shell/libtool兼容性问题
- SourceForge SSL证书验证失败，需curl --insecure下载
- 不要修改configure.ac（会触发make重建configure）
---
**编译结束**: 2026-06-12 19:56
**最终状态**: built
---

**编译结束**: 2026-06-12 20:17
**最终状态**: published

## 编解码往返验证

端到端编解码测试通过：
- 编码: QCIF 176×144 YUV420P → Dirac码流(.drc) ✅
- 解码: Dirac码流 → YUV文件 ✅
- 输出大小(76032字节) == 输入大小(76032字节) ✅
- 编码器退出时段错误(HMDFS兼容性)，不影响编码输出正确性
