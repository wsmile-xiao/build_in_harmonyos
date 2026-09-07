# bitlbee-facebook 1.2.2 — 上游测试记录

> 本文件记录 bitlbee-facebook 1.2.2 上游测试的**实测核验结果**——
> 如实回填（rule 4——不伪造通过率）。

## 上游测试统计（本地实测核验）

| 项目 | 数值 |
|------|------|
| 测试目录 | **无**（tar tzf 实测：源码包共 44 个条目（38 个文件），不存在 tests/ 目录） |
| 测试文件数 | **0** |
| 测试框架 | 无 |
| 上游 CI | `.github/workflows/ci.yml`：克隆 bitlbee → `make install install-dev` → `autogen.sh && ./configure && make`——**纯编译验证，无任何测试步骤** |

## 运行方式

```sh
# autotools 标准入口（本地实测）：
make check
# 输出：Nothing to be done for 'check-am' —— 上游未定义任何 check 目标
```

- 实测核验（rule 4）：
  1. `tar tzf bitlbee-facebook-1.2.2.tar.gz | wc -l` → 44 个条目
     （38 个纯文件）；
     `tar tzf ... | grep -i test` → 无匹配（无 tests/、无 test_*.c）
  2. 源码树 facebook/ 目录：8 个 .c（facebook.c 与 api/data/http/json/
     thrift/util 前缀模块）+ 头文件 + marshaller.list——纯实现代码
  3. 上游 CI（ci.yml）三步全为编译动作，无测试 job
  4. 本地 `make check` → "Nothing to be done for 'check-am'"——
     automake 未生成任何测试目标
- **结论：上游无测试套件**（bitlbee-facebook 是 dlopen 插件，上游
  依赖 bitlbee 宿主运行时环境做端到端验证，未提供独立测试）

## 适配后消费者验证（R34）

上游无测试 → 消费者验证以**真实加载插件模块**为准：
`test_package/run_test.c`（桩宿主 + dlopen）：

- 桩宿主导出 bitlbee 插件 API 全符号面（register_protocol/
  root_command_add 带调用计数 + 54 个存在性桩 + SET_INVALID 数据符号），
  `-rdynamic` 后以 `dlopen(facebook.so, RTLD_NOW)` 加载包内产物——
  全部重定位必须解析（NEEDED 仅 libc.so，glib/json-glib/ffi/pcre2/zlib
  已静态嵌入）；
- 调用 `init_plugin_info()` 验证 plugin_info ABI：`abi_version=1`、
  `name="facebook"`、`version="1.2.2"`；
- 调用 `init_plugin()` 验证协议注册行为：`register_protocol`×1、
  `root_command_add`×3（与上游 facebook.c:1236-1274 源码一致）；
- L1e 破坏性反证：包内 facebook.so 缺失 → test_package 硬失败
  （conanfile 存在性检查 + dlopen ENOENT 双保险，实测 exit=1）。

实测结果：6/6 断言通过（见 notes.md 验证结果节）。
