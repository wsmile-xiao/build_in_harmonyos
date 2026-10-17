# lcmaps

## 简介

LCMAPS（Local Credential MAPping Service）— NIKHEF 开发的网格授权框架核心库：基于 PDL（Authorization Definition Language）策略引擎对凭据执行映射规则，通过 dlopen 加载授权插件，并对外提供 poolindex / gss-assist-gridmap 等客户端 API。本仓构建上游原生支持的 **without-GSI** 面（`--disable-gsi-mode`）。

- 官网: https://software.nikhef.nl/security/lcmaps/
- 上游仓库: https://github.com/Nikhef-lcaae/lcmaps
- 许可证: Apache-2.0
- 语言: C

## OHOS 适配

- 构建系统: autotools（tarball 自带 configure，勿 autoreconf）
- 当前编译版本: 1.6.7
- Flavour: without-GSI（默认 GSI 面硬依赖 globus/voms/openssl，仓内无配方）
- 需要的补丁: 0 个
- 详见 `1.6.7/notes.md` 获取适配详情

## 依赖

- **必需依赖**: 无（libc-only：musl dl* 在 libc；pdl_yacc.c/pdl_lex.c 预生成随 tarball，无 flex 依赖）
- **可选依赖**: 无

## 下游消费

- 头文件面: `pkg-config lcmaps-basic-interface`（lib/pkgconfig/lcmaps-basic-interface.pc）
- 链接面: `pkg-config lcmaps-without-gsi`（liblcmaps_without_gsi）
- 框架/插件消费: dlopen liblcmaps_without_gsi.so + dlsym 入口符号
- 下游链: lcmaps-plugins-basic/1.7.1
