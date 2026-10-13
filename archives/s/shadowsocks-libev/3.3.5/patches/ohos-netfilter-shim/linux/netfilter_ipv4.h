/* OHOS netfilter compat shim — linux/netfilter_ipv4.h
 *
 * 真机 SDK 无此内核 UAPI 头。上游 src/redir.c 只需要
 * SO_ORIGINAL_DST（getsockopt 取 REDIRECT 前的原始目的地址）。
 * 该常量在所有 Linux 系内核上都是 80，这里给出定义。
 * SOL_IP 由 <netinet/in.h>（musl）提供，无需重复定义。
 */
#ifndef OHPC_OHOS_SHIM_LINUX_NETFILTER_IPV4_H
#define OHPC_OHOS_SHIM_LINUX_NETFILTER_IPV4_H
#include <netinet/in.h>
#ifndef SO_ORIGINAL_DST
#define SO_ORIGINAL_DST 80
#endif
#endif
