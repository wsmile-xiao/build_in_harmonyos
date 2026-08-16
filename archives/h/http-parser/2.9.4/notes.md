# http-parser 2.9.4 适配笔记

## 任务身份
- 平台: http-parser / 2.9.4 / Issue #2219 / 分支 feat/http-parser-2.9.4 / 路径 A
- 上游: nodejs/http-parser v2.9.4 (tag 源码, commit 2343fd6b5214b2ded2cdcf76de2bf60903bb90cd)
- 归档: archives/h/http-parser/2.9.4, Conan 引用 http-parser/2.9.4
- 关联: restinio 0.6.19 (Issue #2205) 依赖本包

## 源码核验
- 下载: https://github.com/nodejs/http-parser/archive/refs/tags/v2.9.4.tar.gz
- SHA256: 467b9e30fd0979ee301065e70f637d525c28193449e1b13fbcb1b1fab3ad224f
  （与 OpenWrt libhttp-parser、Buildroot libhttpparser、xmake-repo http_parser、
    FreeBSD ports distinfo 交叉核验一致）
- 许可证: MIT (LICENSE-MIT, Copyright Joyent, Inc. and other Node contributors)

## 构建系统
- 纯 Makefile，无 configure；CC?=gcc / AR?=ar，可覆盖
- 静态库: `make package` → libhttp_parser.a（ar rcs）
- 共享库: `make library` → libhttp_parser.so.2.9.4 (SONAME libhttp_parser.so.2.9)
- 安装: `make install` → http_parser.h + 共享库 + soname 软链
- CFLAGS 固定 -Wall -Wextra -Werror；HNP clang15 编译零告警，无需补丁

## 适配要点
- R33: 编译器/归档器从 Conan conf 获取（tools.build:compiler_executables），
  不用 shell 环境变量
- R9: make -j1
- 静态对象加 -fPIC（CFLAGS_FAST_EXTRA=-fPIC）：静态 libhttp_parser.a 的对象
  可被下游（restinio 等）吸收进共享库，避免 R_AARCH64 relocation 问题（同 zlib）
- 非系统同名库，默认静态；shared 选项映射 `make library`
- 上游 `make test` 集成进 build()，test_g(strict)/test_fast 在 OHOS 真机直接运行

## 上游测试
- 入口: `make test` → test_g (HTTP_PARSER_STRICT=1) + test_fast (STRICT=0)
- test.c: main() 依次执行 26 个 test_* 函数组（API/URL/头字段/溢出/请求响应扫描等），
  内含 50 处 assert()，失败打印 ***...*** 并退出非 0
- 测试不修改任何上游断言、数据、skip 条件

## 消费者测试 (test_package)
- test_http_parser.c 真实调用被测库 API（非 mock）：
  版本/请求解析/响应解析/chunked/parse_url/辅助 API
- 6 个测试组，53 个断言；失败返回非 0，全部通过打印 PASS

## 未完成项
- conan-verify / finish built / pre_pr_audit 结果见对应阶段记录
- 未经授权不执行 commit、push、PR、/ai review、/rebuild、任务平台提审
---

**编译结束**: 2026-08-16 09:41
**最终状态**: built
