/* OHOS netfilter compat shim — linux/if.h
 *
 * 真机（HarmonyOS 原生）SDK 的系统 include 里没有内核 UAPI 头
 * <linux/if.h>。上游 src/redir.c 无条件 #include 它，只为拿到
 * struct ifreq / IFNAMSIZ 之类的接口定义，而这些在 musl 的
 * <net/if.h> 里本来就是标准内容。此处直接转发，不做任何裁剪。
 */
#ifndef OHPC_OHOS_SHIM_LINUX_IF_H
#define OHPC_OHOS_SHIM_LINUX_IF_H
#include <net/if.h>
#endif
