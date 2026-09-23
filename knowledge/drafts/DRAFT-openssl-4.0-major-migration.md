# DRAFT：openssl 3.x → 4.x 大版本跟进迁移链（4 差异 + 补丁重生 + 宏激活）

> Contributor: j669539 | Status: Draft | Updated: 2026-09-13
> Source: PR #7905【依赖项】feat(openssl-4): 4.0.1 适配 HarmonyOS PC（平台任务 #7306）
> CI: #37482 / #37636 / #5591 全绿；上游测试套件 Files=363, Tests=4079, Result: PASS

## 背景

openssl 4.0.1 是 openssl 包的 4.x 大版本跟进件：以 3.5.6.1 系列配方为底稿
（Configure 目标注入 / 交叉编译参数 / no-asm 选项等经验全在，知识条目
E006/E220/E235 均为 3.x 时代沉淀），但 4.0 上游对构建系统做了结构性变更。
本次适配逐项记录了 3.x → 4.x 的构建差异，形成可复用的大版本迁移判定链。

## 差异 1：engines 整体移除（断裂形态取决于配方写法）

### 现象

```text
# 3.x 配方若有手动安装目标：
make: *** No rule to make target 'install_engines'.  Stop.
# 3.x 配方若只是断言/清理 engines：
grep ENGINESDIR Makefile   # 无输出——变量消失（只剩 OPENSSLDIR/MODULESDIR）
```

### 根因

OpenSSL 4.0 上游移除了 engines/ 目录：`no-engine` 选项恒为禁用态（幂等），
生成的 Makefile **不再有 ENGINESDIR 变量**。3.x 时代配方中围绕 engines 的
断言/安装/清理逻辑全部失效：
- 显式调用 `install_engines` → Make 直接报错（显性断裂）；
- 只打包清理 engines 目录 → 静默 no-op（**隐性断裂**，CI 不报错，产物语义变了）。

### 修复

- 用 `install_sw` 平迁（4.x 内部展开为 `install_dev install_modules
  install_runtime`，无 install_engines）；**不要手动列子目标**。
- 打包清理改为 `lib/ossl-modules`（MODULESDIR 派生自 `--libdir=/lib`）+
  上游 cmake/pkgconfig 元数据（Conan 提供可重定位消费元数据）。

## 差异 2：install_sw 目标分解

3.x 的 `install_sw = install_devs install_engines install_runtime`；
4.x 为 `install_dev install_modules install_runtime`（且 install_devs →
install_dev 改名）。直接用 `install_sw` 聚合目标可平迁；引用旧子目标名的
配方会断。

## 差异 3：no-pinshared 新选项（静态打包必传）

### 现象

静态构建（no-shared）链接出的 libcrypto.a/libssl.a 被下游共享库消费后，
下游 .so 的卸载/重载语义异常（被 pin 住）。

### 根因

4.x 静态构建**默认 pin 共享库**（链接器 -z nodelete 类标志），且
`no-shared` **不隐含** `no-pinshared`——与 3.x 行为不同。Conan 静态打包
（R26 系统同名库隔离场景）必须显式传 `no-pinshared`，否则下游共享库静态
链入 libcrypto 后被意外 pin。

### 修复

Configure 参数追加 `no-pinshared`（见 conanfile.py configure_args）。

## 差异 4：CLI 嵌入路径断言迁移（ENGINESDIR → MODULESDIR）

- 3.x：断言 `ENGINESDIR: "/..."`；
- 4.x：ENGINESDIR 概念不存在，断言改为 `OPENSSLDIR: "/ssl"` +
  `MODULESDIR: "/lib/ossl-modules"`。
- test_package 的 CLI 冒烟脚本需同步迁移断言目标，否则脚本在 4.x 上
  找不到 ENGINESDIR 输出而误报失败（或误判通过——取决于断言写法）。

## 补丁迁移：上下文漂移 + 重新生成（非丢弃）

3.5.6.1 的两个源码补丁（apps/speed.c 裸 FD_SET 改走有界帮手函数；
sockets.h 的 musl 有界 fd_set 实现）在 4.0.1 树上 `patch -p1 --dry-run`
全部 FAILED：

| 补丁 | 3.x 上下文 | 4.0.1 漂移点 |
|------|-----------|--------------|
| 0001 speed.c | SM2_SECONDS/FFDH_SECONDS defines 环绕 | 这些 defines 上游已移除 |
| 0001 speed.c | 异步等待循环附近 BIO_printf | 改为 BIO_puts |
| 0002 sockets.h | openssl_fdset 块位置 | 上游新增 VXWORKS/TANDEM 分支，块下移 |

**底层问题在 4.0.1 仍存在**（apps/ 中仅剩 speed.c:1565 一处裸 FD_SET，
其余 30 处上游已用 openssl_fdset），因此正确动作是**按 4.0.1 树重新生成
补丁**而非丢弃。判定方法：grep 新树找问题模式是否残留。

## 宏激活陷阱：OHOS SDK clang 不预定义 __MUSL__

`__MUSL__` 守卫的有界 fd_set 帮手函数（补丁 0002 实现）在 OHOS 交叉编译
下**不会自动激活**——OHOS SDK clang 只预定义 `__OHOS__`/`__OHOS_FAMILY__`。
不注入 `-D__MUSL__` 时回落裸 `FD_SET` 宏 → musl 下展开受检宏引用 libc 私有
`__fd_chk` 符号（E235 链条）。本配方在 `_build_environment()` 中对 OHOS
路径的 CC 命令追加 `-D__MUSL__`（与 Windows 交叉路径同款处理）。

**验证签名**：`llvm-nm -u` 检查 libcrypto.a / libssl.a / CLI / apps 对象
零 `__fd_chk` 引用——这是 4.0.1 交付前的硬断言（manifest verification
记录四处均为 0）。

## 大版本迁移方法论（跨库通用）

1. **旧知识逐项复验**：3.x 有效的知识条目（E006 no-asm / E235 熵源策略）
   在新版本复验后才能复用——本例两者在 4.0.1 均有效，但 E220 相关的
   `__MUSL__` 宏语义在 OHOS SDK 下需要额外注入（历史经验的新边界）。
2. **补丁 dry-run 是第一道闸**：老补丁在新树上 dry-run 失败 ≠ 问题消失，
   先 grep 问题模式确认存续，再决定重生成或丢弃。
3. **Makefile 变量/目标清单 diff**：Configure 后 diff 3.x/4.x 生成 Makefile
   的目标与变量（ENGINESDIR 消失、install_sw 分解、MODULESDIR 新增），
   配方中引用处逐一处理——显性断裂 Make 会报错，**隐性断裂（静默 no-op）
   只能靠打包产物清单 diff 抓**。
4. **默认选项语义漂移**：no-shared 不再隐含 no-pinshared——每个 no-* 选项
   在新版本重新查 Configure 文档（`perl Configure list` 与官方 NEWS.md）。

## 验证证据（PR #7905 / CI #37482、#37636、#5591）

- conan create EXIT=0；包 150 文件（2 静态库 + CLI，无 .so、无上游 cmake/pc）
- `llvm-nm -u`：libcrypto.a / libssl.a / CLI / apps 对象 **零 `__fd_chk`**
- 上游测试套件（aarch64 OHOS 设备实跑）：**Files=363, Tests=4079, PASS**
  （309 scripts ok / 53 skipped / 0 FAILED——skip 全部为构建选项门控
  FIPS-only/Windows-only/enable-tfo/rc5/LMS/legacy-PBE/ACVP，无 musl/OHOS 特有）
- test_package：C 消费者（RAND_bytes + SHA-256 已知答案 + SSL_CTX_new）
  PASS；CLI 冒烟（version/OPENSSLDIR/MODULESDIR/SHA-256/random）PASS
- 设备实跑 `openssl version -a`：`OpenSSL 4.0.1 9 Jun 2026`，
  `Seeding source: getrandom-syscall`

## 红线（forbid）

- 禁止因 3.x 补丁 dry-run 失败就直接删除补丁而不查问题存续性
- 禁止在 4.x 上沿用 ENGINESDIR 断言（概念已不存在）
- 禁止静态打包不传 no-pinshared（下游 .so 被 pin 的隐患）
- 禁止假设 OHOS SDK clang 预定义 __MUSL__（只预定义 __OHOS__ 系）
