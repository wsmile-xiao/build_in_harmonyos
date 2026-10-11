# E547 — lld 把 GNU ld 专有 -export-dynamic 解析为 -e xport-dynamic，ELF entry=0x0 启动即段错误

> Contributor: Awstme | Status: Draft | Updated: 2026-09-05
> Source: bmagic 7.13.4 适配（BitMagic 上游 tests 三套二进制在 OHOS 启动即 SIGSEGV）

## 错误特征

```text
ld.lld: warning: cannot find entry symbol xport-dynamic; not setting start address
./bmtest
Segmentation fault (core dumped)          # exit 139，亚秒级（0.04s）
$ readelf -h bmtest | grep -i entry
  Entry point address:               0x0
```

注意：构建"成功"（exit 0），失败延迟到运行期——CI 编译门禁全绿但 L2/运行必挂，
容易误判为库本身问题。

## 触发条件

- 构建系统: Makefile / 平台 mk（autotools 同理）；链接参数含 GNU ld 专有单横线长选项 `-export-dynamic`
- 阶段: linking（症状在运行期）
- 工具链: OHOS clang 15 默认链接器 lld（GNU ld 不触发）

## 根因分析

GNU ld 把 `-export-dynamic` 视为 `--export-dynamic` 的等价写法（导出全部符号到
动态符号表）。lld 的驱动按短选项聚类规则把它解析为 `-e xport-dynamic`
（入口符号名为 "xport-dynamic"）；找不到该符号时 lld 仅告警
`cannot find entry symbol` 并把 ELF 入口留为 0x0，二进制一旦执行立即跳转
非法地址 → SIGSEGV。上游在标准 GNU/Linux 上完全正常，属工具链语义差异。

BitMagic 实例：`platforms/aarch64-linux-gnu.mk` 的
`COMMON_LDFLAGS = $(LINKER_DFLAGS) -export-dynamic -rdynamic`。

## 解决方案

### 推荐方案
用 clang driver 正确转译（`-rdynamic` → `-Wl,--export-dynamic`）且语义等价的
`-rdynamic` 替代 `-export-dynamic`，优先 make 顶层变量覆盖，零补丁：

```sh
# BitMagic 实测（上游自带 relink 目标，重链三个测试二进制）：
make -C tests/stress relink OSNAME=aarch64-linux-gnu CXX=clang++ CC=clang LD=clang++ \
     COMMON_LDFLAGS="-rdynamic"
```

### 禁止做法
- ❌ 直接修改上游 mk/Makefile 把 `-export-dynamic` 改成 `--export-dynamic`
  （上游有变量钩子时必须用钩子，见补丁最小化原则）
- ❌ 用 `|| true` / 包一层脚本掩盖段错误（运行证据必须真实）

## 验证
```bash
readelf -h <二进制> | grep 'Entry point address'   # 修复后为非零地址
./bmtest                                           # 正常启动（BitMagic 7.13.4 横幅 + 测试输出）
```

## 关联条目
- 相关: E011（HMDFS umask 077 临时目录不可写）、E160（config.guess 不识别 HarmonyOS）、
  E266（lld 动态依赖 libxml2.so.16 加载失败）
- 本草稿补充：GNU ld 单横线长选项在 lld 上的短选项聚类误解析，是"编译通过、
  运行即崩"类失败的独立根因，与权限/密码条目无关。
