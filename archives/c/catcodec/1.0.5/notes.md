# catcodec 1.0.5 适配笔记 (HarmonyOS PC / OpenHarmony compile-agent)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Makefile 是 GNU Make 直接构建（无 autotools/cmake），scaffold 默认 autotools 模板不适用 | conan-init 模板按 registry 默认生成 | 按 Makefile 重写 build()：`make -j1 SHELL=<HNP bash> CXX=<conan conf clang++>`（R33，不裸用 ${CXX}） |
| 2 | 设备 /system/bin/sh (mksh) 对 printf \x 转义处理不可靠、make 配方默认 /bin/sh 不可用 | HarmonyOS 无标准 POSIX sh | make 显式传 SHELL=/data/service/hnp/bin/bash；test 用 bash 包裹 |
| 3 | 版本号注入：Makefile 用 `$(shell ./findversion.sh | cut)` + sed 生成 src/rev.cpp | 上游 VCS 版本机制 | 无需处理：非 VCS checkout 时 findversion.sh 直接输出 1.0.5；make 一次通过 |
| 4 | 测试数据：上游无任何测试/样例 .cat/WAV | 上游仅 manpage 描述格式 | test.sh 程序化构造严格 RIFF/PCM WAV（bash printf 二进制生成）+ .sfo，编码→解码→cmp 字节一致 |
| 5 | WAV 头构造易错 | 11025=0x2B11 等小端手写错误 | 探测脚本先行验证全部 11 用例通过后再固化到 test.sh |
| 6 | 全零 .cat 头是"0 样本"合法空目录（解码成功 rc=0） | count/8 语义 | 损坏 .cat 用例用 count>=8 + 主体截断构造，确定性触发拒绝 |

## 源码修改
无（零补丁：patches/ 为空，无平台宏）

## 依赖版本
无第三方依赖（仅 libc/C++ 标准库 + clang 15.0.4 / GNU Make 4.4.1）

## 验证结果
- 探索编译：make -j1 一次通过；./catcodec 输出 "catcodec version 1.0.5"
- 测试套件：11 用例 / 28 断言全部通过（详见 test_package/test.sh 与 PR 描述）

## 注意事项
- 构建产物仅 bin/catcodec 一个 ELF（application/tool 包，无需库/头文件）
- tool 类型必须声明软件级 commands.json（R38），已创建
- conandata.yml 保持官方 URL（cdn.openttd.org），sha256 以 .tarball-sha256 下载验证为准
---

**编译结束**: 2026-09-05 14:06
**最终状态**: published
