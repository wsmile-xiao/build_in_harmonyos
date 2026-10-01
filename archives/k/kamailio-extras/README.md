# kamailio-extras

Kamailio SIP 服务器 **extras 模块集**（31 个运行时加载模块 `.so`），面向 HarmonyOS PC
（aarch64 / OHOS）适配的 Conan 包。

| 项 | 值 |
|---|---|
| 上游 | [kamailio/kamailio](https://github.com/kamailio/kamailio) 6.0.6 |
| 源码包 | `kamailio-6.0.6_src.tar.gz`（kamailio.org 官方发布源） |
| 构建体系 | 经典 Makefile 体系（`src/Makefile` + `Makefile.defs`） |
| 补丁 | **0 补丁**（平台差异全部经 make 命令行变量表达） |
| 依赖 | `hiredis/1.2.0`（cnxcc 构建期依赖，静态链入）、`libevent/2.1.13`（cnxcc 构建期依赖，**动态**：由 conan 依赖链提供运行时 `.so`，部署需 `LD_LIBRARY_PATH`） |
| 打包内容 | `lib/kamailio/modules/*.so`（31 个模块） |

## 这是什么

Alpine 把 kamailio 拆成 `kamailio` 主包与多个子包，`kamailio-extras` 子包对应
31 个"无额外依赖的扩展模块"。本包与之对齐（清单与 Alpine `main/kamailio`
APKBUILD 的 `_mod_list_extras`（pkgver=6.0.6）逐项一致）：

```
auth_diameter  auth_xkeys   call_control  call_obj    cnxcc      dmq
dmq_usrloc     domainpolicy file_out      influxdbc   log_custom msrp
nosip          pdb          pvtpl         qos         rtjson     sca
seas           sms          ss7ops        sst         statsd     tcpops
timer          tmrec        tsilo         uac_redirect xhttp     xhttp_rpc
xprint
```

模块 `.so` 由 kamailio 主程序运行时 `loadmodule` 加载，**不作为链接库**供下游
`conan install` 直接链接；`cpp_info.libs` 为空，`libdirs` 指向模块目录。

## 使用

```bash
conan install --requires=kamailio-extras/6.0.6 -pr:h ohos-aarch64 --build=missing
```

将包内 `lib/kamailio/modules/` 部署到目标机后，在 kamailio 配置中按需加载：

```
loadmodule "lib/kamailio/modules/xprint.so"
```

## 同族包

kamailio 6.0.6 的其他模块以独立包发布（`kamailio-tls`、`kamailio-xml`、
`kamailio-snmpstats`、`kamailio-uuid`、`kamailio-outbound`、`kamailio-debugger`
等），均采用同一套适配方法（`OS=harmonyos` + `extra_defs` 宏集 + 只编目标模块）。

## 已知平台限制

- **`mkfifo(2)` 返回 EPERM**：`jsonrpcs` 模块的 FIFO transport 在 OHOS 上无法创建
  FIFO（`jsonrpcs_fifo.c:72 Can't create FIFO: Operation not permitted`）。
  extras 包内不含 `jsonrpcs`（属主包），此处仅作平台事实记录。

适配细节、上游测试清点与实测结果见 [`6.0.6/notes.md`](6.0.6/notes.md)。
