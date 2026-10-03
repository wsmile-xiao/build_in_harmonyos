# kamailio-db

Kamailio SIP 服务器 **DB-backend 模块集**（33 个运行时加载模块 `.so`），面向 HarmonyOS PC
（aarch64 / OHOS）适配的 Conan 包。

| 项 | 值 |
|---|---|
| 上游 | [kamailio/kamailio](https://github.com/kamailio/kamailio) 6.0.6 |
| 源码包 | `kamailio-6.0.6.tar.gz`（GitHub 官方仓库 tag 归档；官网 src 包不含 `test/`） |
| 构建体系 | 经典 Makefile 体系（`src/Makefile` + `Makefile.defs`） |
| 补丁 | **0 补丁**（平台差异全部经 make 命令行变量表达） |
| 依赖 | **无强制第三方依赖**（33 模块 `LIBS=` 全空，仅 `dispatcher` 用系统 `-lm`） |
| 打包内容 | `lib/kamailio/modules/*.so`（33 个模块） |

## 这是什么

Alpine 把 kamailio 拆成 `kamailio` 主包与多个子包，`kamailio-db` 子包对应
*"Kamailio modules using a database backend"* —— **使用**数据库后端 API 的 33 个模块。
本包与之对齐（清单与 Alpine `main/kamailio` APKBUILD 的 `_mod_list_db`（pkgver=6.0.6）逐项一致）：

```
acc  alias_db  auth_db  avpops  cfg_db  db_cluster  db_flatstore  dialog  dispatcher
domain  drouting  group  htable  imc  matrix  mohqueue  msilo  mtree  pdt
permissions  pipelimit  prefix_route  p_usrloc  registrar  sipcapture  siptrace
speeddial  sqlops  topos_htable  uac  uri_db  userblocklist  usrloc
```

> **不含**具体 DB 驱动：`db_mysql` / `db_postgres` / `db_unixodbc` / `db_sqlite` / `db_text` /
> `db_berkeley` 属**独立子包**（Alpine `_db_driver`、Debian `kamailio-*-modules`）。运行时需另装
> 对应驱动子包才能实际持久化。

## OHOS 适配要点

- `make cfg OS=linux SCTP=0 DEFS_RM="-DHAVE_RESOLV_RES"` —— OHOS 上 `uname -s`=`HarmonyOS`
  无专属分支，须显式按 Linux ABI 构建；`SCTP=0`（sysroot 无 `netinet/sctp.h`）、
  去掉 `HAVE_RESOLV_RES`（OHOS libc 无 `_res`）。
- 该口径与 OHOS 上 core **完全一致**：kamailio 加载模块时校验目标标识 `(aarch64/linux)`
  与编译标志集合，不一致会以 `module version/flags mismatch` 拒绝加载。
- 0 补丁：33 模块源码无平台条件编译。
- `-j1`：OHOS SELinux 禁止用户进程创建 FIFO，GNU make jobserver 依赖 FIFO 传令牌。

## 产物与验证

- 33 个 `.so`：ELF64 / AArch64 / ET_DYN，`DT_NEEDED` 仅 `libc.so`，无 RPATH/RUNPATH，
  导出契约名与模块名一致，目标标识 `kamailio 6.0.6 (aarch64/linux)`。
- `conan create`：rc=0，`test_package` 37 项断言全通过（含鸿蒙专项 `[H1][H2][H5][H6][H7]`，
  真实 dlopen 33 个 `.so`）。
- `conan-verify`：G0-G4 / L2·L4·L5 → PASS。
- 上游 `test/unit`：49/49 全量执行（OK=5 / FAIL=9 / SKIP=35 / TIMEOUT=0，FAIL 均为平台限制、
  上游用例陈旧或缺独立 DB 驱动子包，详见 `6.0.6/notes.md`）。

## 使用

```bash
conan install --requires=kamailio-db/6.0.6@ohpcd/stable \
  -pr:h=ci/conan/profiles/ohos-aarch64
# 模块位于 <package_folder>/lib/kamailio/modules/*.so，供 kamailio 运行时 loadmodule 加载
# 消费方 core 必须同口径：OS=linux SCTP=0 DEFS_RM=-DHAVE_RESOLV_RES
```
