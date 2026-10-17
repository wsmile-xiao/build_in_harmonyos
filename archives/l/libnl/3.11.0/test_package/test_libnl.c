/*
 * test_package/test_libnl.c — libnl 3.11.0 消费者验证
 *
 * 目的（R34：实质测试，非 print-only 空壳）：
 *   1. 编译面：公开头 <netlink/...> 在 OHOS/musl 下可编译；
 *   2. 链接面：6 个交付子库（nl-3 / nl-route-3 / nl-genl-3 / nl-nf-3 /
 *      nl-idiag-3 / nl-xfrm-3）逐个可取到导出符号；
 *   3. 运行面：调用不触碰 netlink 内核的纯用户态 API 并断言返回值。
 *
 * 刻意避开需要 CAP_NET_ADMIN / netlink 内核交互的调用（nl_connect、
 * nl_cache_refill 等），这些在 OHOS 用户态沙箱必然失败，属环境限制而非适配缺陷。
 */
#include <stdio.h>
#include <string.h>

#include <netlink/netlink.h>
#include <netlink/version.h>
#include <netlink/addr.h>
#include <netlink/socket.h>
#include <netlink/route/rtnl.h>
#include <netlink/genl/genl.h>
#include <netlink/netfilter/ct.h>
#include <netlink/idiag/idiagnl.h>
#include <netlink/xfrm/ae.h>

static int checks;
static int failures;

static void check(int cond, const char *what)
{
	checks++;
	printf("  [%s] %s\n", cond ? "ok" : "FAIL", what);
	if (!cond)
		failures++;
}

int main(void)
{
	char buf[64];

	printf("libnl test_package — compile-time version: %s\n", LIBNL_VERSION);

	/* 1) 编译期版本宏必须与配方版本一致 */
	check(strcmp(LIBNL_VERSION, "3.11.0") == 0, "LIBNL_VERSION == \"3.11.0\"");

	/* 2) nl-3（核心）：地址族名表往返一致（纯用户态查表） */
	{
		char *af = nl_af2str(AF_INET, buf, sizeof(buf));
		printf("  nl_af2str(AF_INET) = %s\n", af ? af : "(null)");
		check(af != NULL, "nl_af2str(AF_INET) != NULL");
		if (af != NULL) {
			char name[64];
			strncpy(name, af, sizeof(name) - 1);
			name[sizeof(name) - 1] = '\0';
			check(nl_str2af(name) == AF_INET,
			      "nl_str2af(nl_af2str(AF_INET)) == AF_INET（名表往返）");
		}
		check(nl_str2af("no-such-family") < 0,
		      "nl_str2af(\"no-such-family\") < 0（错误路径）");
	}

	/* 3) nl-3（核心）：套接字句柄分配/释放（不创建 netlink socket） */
	{
		struct nl_sock *sk = nl_socket_alloc();
		check(sk != NULL, "nl_socket_alloc() != NULL");
		if (sk != NULL)
			nl_socket_free(sk);
	}

	/* 4) nl-route-3：路由类型名转换（纯用户态查表，缓冲有界） */
	{
		char *rtn = nl_rtntype2str(RTN_UNICAST, buf, sizeof(buf));
		printf("  nl_rtntype2str(RTN_UNICAST) = %s\n", rtn ? rtn : "(null)");
		check(rtn != NULL && rtn[0] != '\0', "nl_rtntype2str(RTN_UNICAST) 非空");
	}

	/* 5) nl-idiag-3：inet_diag 状态名转换（纯用户态查表） */
	{
		char *st = idiagnl_state2str(1, buf, sizeof(buf));
		printf("  idiagnl_state2str(1) = %s\n", st ? st : "(null)");
		check(st != NULL, "idiagnl_state2str(1) != NULL");
	}

	/* 6) nl-nf-3：conntrack 对象分配/释放（纯用户态） */
	{
		struct nfnl_ct *ct = nfnl_ct_alloc();
		check(ct != NULL, "nfnl_ct_alloc() != NULL");
		if (ct != NULL)
			nfnl_ct_put(ct);
	}

	/* 7) nl-genl-3 / nl-xfrm-3：取导出符号地址证明确实链接到该子库
	 *    （不调用：这些 API 需要 nl_sock / netlink 内核交互） */
	check((void *)genl_op2name != NULL, "nl-genl-3 符号 genl_op2name 可链接");
	check((void *)xfrmnl_ae_flags2str != NULL,
	      "nl-xfrm-3 符号 xfrmnl_ae_flags2str 可链接");

	printf("libnl 3.11.0 test_package: %s (%d checks, %d failure(s))\n",
	       failures == 0 ? "PASS" : "FAIL", checks, failures);
	return failures == 0 ? 0 : 1;
}
