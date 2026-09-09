/* libmnl 1.0.5 consumer smoke test (Conan L1).
 *
 * Exercises real libmnl APIs:
 *   - netlink message construction: mnl_nlmsg_put_header / mnl_attr_put_u32
 *   - attribute round-trip: mnl_nlmsg_get_payload / mnl_attr_get_type /
 *     mnl_attr_get_u32
 *   - netlink socket lifecycle: mnl_socket_open / mnl_socket_bind /
 *     mnl_socket_get_portid / mnl_socket_close
 *
 * No kernel netlink round-trip is required: binding NETLINK_ROUTE with
 * groups=0 is unprivileged and needs no CAP_NET_ADMIN.
 */
/* OHOS: the sysroot ships a bionic-style uapi <linux/socket.h> whose
 * unconditional struct sockaddr_storage collides with musl
 * <sys/socket.h> in BOTH include orders (no __UAPI_DEF_* coordination
 * in this sysroot). The library itself is unaffected because its in-tree
 * build resolves linux uapi headers to bundled copies that define
 * __kernel_sockaddr_storage instead; consumers only get libmnl.h, whose
 * <linux/netlink.h> pulls the sysroot copy.
 * Remedy (same as the libnfnetlink port): pre-define the uapi include
 * guard so sysroot <linux/socket.h> contributes nothing, and supply the
 * single typedef netlink/rtnetlink headers need from it.
 */
#define _UAPI_LINUX_SOCKET_H
typedef unsigned short __kernel_sa_family_t;

#include <stdio.h>

#include <libmnl/libmnl.h>
#include <linux/rtnetlink.h>

int main(void)
{
	char buf[MNL_SOCKET_BUFFER_SIZE];
	struct nlmsghdr *nlh;
	struct nlattr *attr;
	struct mnl_socket *nl;
	unsigned int portid;

	/* 1. Build a netlink message header. */
	nlh = mnl_nlmsg_put_header(buf);
	nlh->nlmsg_type = RTM_NEWLINK;
	nlh->nlmsg_flags = NLM_F_REQUEST | NLM_F_ACK;
	nlh->nlmsg_seq = 1;

	/* 2. Put one u32 attribute and read it back (round-trip). */
	mnl_attr_put_u32(nlh, 1, 0x12345678);

	if (mnl_nlmsg_get_payload_len(nlh) != 8u) { /* nlattr hdr(4) + u32(4) */
		fprintf(stderr, "FAIL: unexpected payload length %u\n",
			(unsigned)mnl_nlmsg_get_payload_len(nlh));
		return 1;
	}

	attr = mnl_nlmsg_get_payload(nlh);
	if (mnl_attr_get_type(attr) != 1) {
		fprintf(stderr, "FAIL: unexpected attribute type %u\n",
			mnl_attr_get_type(attr));
		return 1;
	}
	if (mnl_attr_get_u32(attr) != 0x12345678) {
		fprintf(stderr, "FAIL: attribute round-trip mismatch\n");
		return 1;
	}

	/* 3. Open, bind and close a NETLINK_ROUTE socket. */
	nl = mnl_socket_open(NETLINK_ROUTE);
	if (nl == NULL) {
		perror("FAIL: mnl_socket_open");
		return 1;
	}
	if (mnl_socket_bind(nl, 0, MNL_SOCKET_AUTOPID) < 0) {
		perror("FAIL: mnl_socket_bind");
		mnl_socket_close(nl);
		return 1;
	}
	portid = mnl_socket_get_portid(nl);
	if (mnl_socket_close(nl) < 0) {
		perror("FAIL: mnl_socket_close");
		return 1;
	}

	printf("libmnl 1.0.5 smoke test OK "
	       "(attr round-trip passed, netlink portid=%u)\n", portid);
	return 0;
}
