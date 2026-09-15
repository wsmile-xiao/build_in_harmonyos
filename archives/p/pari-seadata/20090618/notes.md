# pari-seadata 20090618 — 适配笔记

## 这个包是什么
PARI/GP 的 **seadata**：`ellsea`/`ellap` 计算有限域上椭圆曲线 Frobenius 迹所需的
模多项式数据表（p < 500 的 `sea<p>` 文件）。源自 ECHIDNA 数据库（David R. Kohel，
悉尼大学）。是 PARI 的可选数据包，本身**不含任何代码**。

## 版本与来源（R39 官方源）
- conan 版本取干净的日期式 `20090618`（= 上游 2009-06-18 发布的 seadata；
  Debian 源包对该日期的编码为 `0.20090618`）。
- 官方源：`https://pari.math.u-bordeaux.fr/pub/pari/packages/seadata.tgz`
  - size 19214199，sha256 `c9282a52…195833`，FTP Last-Modified 2009-06-18。
  - 与 Debian `pari-seadata_0.20090618-3` 的 `.orig.tar.gz` **逐字节一致**（同 size 同 sha256）。
  - 选官方 first-party URL，不用 deb.debian.org 的 Debian 重打包（PF7 黑名单）。

## 依赖结论（W0，前置核验已在上阶段完成）
- `Architecture: all`，**无任何强制第三方库依赖**：
  - Build-Depends 仅 `debhelper-compat (=13)`（Debian 打包工具，conan 侧不需要）；
    安装用 `make`/`gzip`（系统工具，CI clean 环境已具备）。
  - 运行期 `Depends: ${misc:Depends}`（解析为空）；仅 `Suggests: pari-gp`（软依赖，消费者）。
- 结论：可直接适配，无依赖前置阻塞。R36 不适用（无待发布依赖）。

## 构建/测试入口（实证无自动化测试）
- 上游 tarball：53 条目 = `data/seadata/{sea0,sea2,...,sea499}`（51 个 GP 文本数据文件）+ README。
  `grep -icE 'Makefile|configure|CMake|test|\.c$|\.h$|\.gp$|\.py$'` = **0**。
- Debian `rules`：`build-stamp: touch build-stamp`（不编译）；`install: dh_install + gzip`
  （**无 check/test 目标**）。
- 真实功能入口是消费方 gp：`gp -q` 内 `ellsea`/`ellap` 读取本目录数据（属 pari 包验证职责）。
- 基线指纹（用于 test_package 内容校验）：
  - sea* 文件数 = 51；总字节 = 40782207；拼接 sha256 =
    `c055c577d25f7f0e1a9cf90d699df846b4ecde5b7cb64debae1dc2f50f1aa738`
  - 单文件：sea0 `97c988c3…`，sea499 `b024b8f6…`，README `f9a9d827…`
  - 全部 `sea<p>` 为 ASCII，首字符 `[`（GP 向量语法）。

## 打包决策
- `build()` 空操作（无代码可编）。
- `package()`：`copy *` 把 `seadata/` 落到 `<pkg>/res/pari/seadata/`（对应 Debian
  `dh_install seadata /usr/share/pari`）。保留上游未压缩文件（不引 gzip 构建工具，
  PARI 可直读）。
- `package_type="application"` + 软件级 `commands.json`（`binary:false`）：
  与已入库 ca-certificates 同型，确保 conan create 真正执行 package()，res/ 产物由
  test_package 内容级校验（51 文件 + 拼接 sha256）实质覆盖。
- `package_info`：`cpp_info.libs=[]`、`cpp_info.resdirs=["res"]`、`set_property("pari:seadata_rel","res/pari/seadata")`（不用 1.x `user_info`，避免弃用告警）
  指给下游 gp 拼 `share_path`。
- OHOS 适配：纯数据无平台代码，无需 `__OHOS__` 分支、无 patch；R32 用
  `os in ("Linux","OHOS")` 校验。属 R40 之外的非“深度适配”库（图形/UI/多媒体/底层）。

## test_package（R34）
`test_verify.py` 对真实打包内容校验：目录存在 + README + 51 个 sea<p> + 逐文件 GP 格式
且非空 + 拼接 sha256 == 基线。丢/错任一字节即返回非 0，conan test 阶段拦截。
---

**编译结束**: 2026-09-06 19:56
**最终状态**: built
