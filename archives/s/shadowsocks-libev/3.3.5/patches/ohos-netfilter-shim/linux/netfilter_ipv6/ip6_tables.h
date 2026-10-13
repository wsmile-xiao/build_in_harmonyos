/* OHOS netfilter compat shim — linux/netfilter_ipv6/ip6_tables.h
 *
 * 真机 SDK 无此内核 UAPI 头。上游 src/redir.c 只需要
 * IP6T_SO_ORIGINAL_DST（IPv6 版原始目的地址 getsockopt 选项号）。
 * 上游自己也有 #ifndef IP6T_SO_ORIGINAL_DST / #define ... 80 的兜底，
 * 但那是**常量**兜底，头文件本身缺失仍会在 #include 处直接失败。
 */
#ifndef OHPC_OHOS_SHIM_LINUX_NETFILTER_IPV6_IP6_TABLES_H
#define OHPC_OHOS_SHIM_LINUX_NETFILTER_IPV6_IP6_TABLES_H
#ifndef IP6T_SO_ORIGINAL_DST
#define IP6T_SO_ORIGINAL_DST 80
#endif
#endif
