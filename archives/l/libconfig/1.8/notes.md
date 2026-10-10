# libconfig 1.8 - 编译进度

> 归档创建: 2026-10-08（依赖项任务 #14962，认领人 j669539）
> 任务分支: feat/libconfig-1.8

## 一、基本信息
| 项目 | 值 |
|------|-----|
| 软件 | libconfig |
| 版本 | 1.8（main 已有 1.7.3，本件为版本升级） |
| 状态 | ✅ built |
| 构建系统 | autotools（configure 由 autoreconf -f 引导生成） |
| 源码 | https://github.com/hyperrealm/libconfig archive/refs/tags/v1.8.tar.gz |

## 二、与 1.7.3 配方的差异（增量适配）
1. **源码形态变化**：v1.8 GitHub release 不再提供 tarball 资产（v1.7.3 有），只能用
   git tag archive。tag archive 不含预生成 configure/Makefile.in/.info，
   配方在 build() 用 `autoreconf -f` 引导生成。
   - 用 `-f` 而非 `-fi`：`-i` 会让 automake/libtoolize 覆盖 aux-build/config.guess
     和 config.sub，导致 E007 补丁失效（stock 脚本不认识 HarmonyOS）。
2. **新增构建依赖**：CI 镜像只有 autoconf 套件（/data/service/hnp/bin），
   无 automake/libtoolize → tool_requires automake/1.18 + libtool/2.5.4
   （abiword-plugin-*/argp-standalone 同款方案）。
3. **E007 补丁重做**：v1.8 携带的 config.guess/config.sub 是 2024-01-01 版
   （1.7.3 是旧版），补丁按新版锚点重新生成：
   - 0001: config.guess 顶部 case 加 `*:HarmonyOS:*:*` 分支（uname -s=HarmonyOS
     时直接输出 aarch64-unknown-linux-ohos 等，不走编译器探测）
   - 0002: config.sub OS 列表加 `ohos*`，kernel-os 组合校验加 `linux-ohos*-`
   - 不传 --build/--host（E007 红线：会导致误判交叉编译）
4. **E114 umask 处理位置变化**：1.7.3 是对 tarball 内预生成 configure 打补丁；
   1.8 的 configure 是构建时生成的，改为 build() 里 `_drop_umask_077()` 文本替换
   （abiword 同款运行时修法）。
5. **--disable-doc / --disable-examples**：tag archive 无预生成 .info，doc/ 目标
   需要 makeinfo（镜像无此工具）→ 关闭 doc；examples/c 的 example1..4 被上游注册为
   automake TESTS，运行时按相对路径读 example.cfg，VPATH 构建下报 file I/O error
   （3/4 失败，实测）→ 关闭 examples。
6. **上游测试 13 → 16**：v1.8 新增 SettingLookups / ReadStream / BinaryAndHex
   三个 tinytest 用例。

## 三、测试
- build() 不跑 make check（examples 的 VPATH 相对路径问题，见差异 5）
- test_package：vendored 上游 16 用例（对安装后的 libconfig.a 重编译重跑，
  CWD=upstream/tests/ 保证 testdata 相对路径）+ 消费者 10 断言（1 ctest + 9 test.sh）

## 四、源码修改清单
| 文件 | 原因 | 方式 | 补丁状态 |
|------|------|------|---------|
| aux-build/config.guess | E007 HarmonyOS 识别 | 0001 patch | 已提交 |
| aux-build/config.sub | E007 linux-ohos 三元组 | 0002 patch | 已提交 |
| configure（生成物） | E114 umask 077 | build() 运行时替换 | 不入库 |

## 五、结束记录
- 最终状态: built
- 结束时间: 2026-10-08
