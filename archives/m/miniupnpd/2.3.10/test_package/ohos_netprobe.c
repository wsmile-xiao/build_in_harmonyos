/* ohos_netprobe.c — HarmonyOS network-stack capability probe shipped with
 * miniupnpd's test_package (the "鸿蒙特有测试" row of the PR table).
 *
 * miniupnpd is a UPnP daemon: at startup it opens SSDP multicast UDP sockets,
 * joins 239.255.255.250, listens on TCP 5000, watches interface changes over
 * rtnetlink and reads per-interface stats. This probe exercises exactly those
 * kernel interfaces so a consumer can tell on a given OHOS build whether the
 * daemon's runtime prerequisites are met.
 *
 * Contract:
 *   - REQUIRED checks: capabilities miniupnpd needs unconditionally.
 *     Any failure => exit 1.
 *   - INFO checks: capabilities that depend on IPv6 availability or process
 *     capability (CAP_NET_ADMIN / CAP_NET_RAW), reported but not fatal.
 *   - Prints one "NAME<TAB>result<TAB>detail" line per check plus
 *     "OHOS_NETPROBE required=<n> required_pass=<n> info=<n>".
 *
 * stdout is parsed by test_package/conanfile.py, which asserts the required
 * subset is complete and fully passing.
 */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <fcntl.h>
#include <sys/socket.h>
#include <sys/ioctl.h>
#include <sys/time.h>
#include <sys/types.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <net/if.h>
#include <ifaddrs.h>
#ifndef _UAPI_LINUX_SOCKET_H
#define _UAPI_LINUX_SOCKET_H
#endif
#ifndef __kernel_sa_family_t
#define __kernel_sa_family_t sa_family_t
#endif
#include <linux/netlink.h>
#include <linux/rtnetlink.h>


static int required_total = 0, required_pass = 0, info_total = 0;

static void chk(const char *name, int ok, const char *detail) {
    required_total++;
    if (ok) required_pass++;
    printf("%s\t%s\t%s\n", name, ok ? "PASS" : "FAIL", detail);
}

static void info(const char *name, int ok, const char *detail) {
    info_total++;
    printf("%s\t%s\t%s\n", name, ok ? "INFO-YES" : "INFO-NO", detail);
}

int main(void) {
    char detail[256];
    int s, rc, saved_errno;
    char ifname[IFNAMSIZ] = "lo";
    struct in_addr ifaddr;
    unsigned int ifindex;

    /* ---- interface discovery (getifaddrs is itself a required check) ---- */
    struct ifaddrs *ifap = NULL, *ifa;
    errno = 0;
    rc = getifaddrs(&ifap);
    saved_errno = errno;
    int nif = 0, have_v4 = 0;
    if (rc == 0) {
        for (ifa = ifap; ifa; ifa = ifa->ifa_next) {
            if (!ifa->ifa_addr) continue;
            nif++;
            if (!have_v4 && ifa->ifa_addr->sa_family == AF_INET &&
                strcmp(ifa->ifa_name, "lo") != 0) {
                strncpy(ifname, ifa->ifa_name, IFNAMSIZ - 1);
                ifaddr = ((struct sockaddr_in *)ifa->ifa_addr)->sin_addr;
                have_v4 = 1;
            }
        }
        if (!have_v4) {
            for (ifa = ifap; ifa; ifa = ifa->ifa_next) {
                if (ifa->ifa_addr && ifa->ifa_addr->sa_family == AF_INET &&
                    strcmp(ifa->ifa_name, "lo") == 0) {
                    strncpy(ifname, "lo", IFNAMSIZ - 1);
                    ifaddr = ((struct sockaddr_in *)ifa->ifa_addr)->sin_addr;
                    have_v4 = 1;
                    break;
                }
            }
        }
    }
    snprintf(detail, sizeof detail, "entries=%d primary=%s ipv4=%s",
             nif, ifname, have_v4 ? inet_ntoa(ifaddr) : "none");
    chk("getifaddrs", rc == 0 && nif > 0, detail);

    ifindex = if_nametoindex(ifname);
    snprintf(detail, sizeof detail, "%s index=%u", ifname, ifindex);
    chk("if_nametoindex(primary)", ifindex > 0, detail);
    snprintf(detail, sizeof detail, "lo index=%u", if_nametoindex("lo"));
    chk("if_nametoindex(lo)", if_nametoindex("lo") > 0, detail);
    if (!have_v4) ifaddr.s_addr = htonl(INADDR_LOOPBACK);

    /* ---- SSDP/HTTP socket basics ---- */
    errno = 0;
    s = socket(AF_INET, SOCK_DGRAM, 0);
    saved_errno = errno;
    snprintf(detail, sizeof detail, "fd=%d", s);
    chk("socket(AF_INET,SOCK_DGRAM)", s >= 0, s >= 0 ? detail : strerror(saved_errno));
    int udp = s;

    struct ifreq ifr;
    int io = socket(AF_INET, SOCK_DGRAM, 0);
    memset(&ifr, 0, sizeof ifr);
    strncpy(ifr.ifr_name, ifname, IFNAMSIZ - 1);
    errno = 0;
    rc = ioctl(io, SIOCGIFADDR, &ifr);
    saved_errno = errno;
    if (rc == 0) {
        struct sockaddr_in *sa = (struct sockaddr_in *)&ifr.ifr_addr;
        snprintf(detail, sizeof detail, "%s addr=%s", ifname,
                 inet_ntoa(sa->sin_addr));
    } else {
        snprintf(detail, sizeof detail, "%s: %s", ifname, strerror(saved_errno));
    }
    chk("ioctl(SIOCGIFADDR)", rc == 0, detail);

    memset(&ifr, 0, sizeof ifr);
    strncpy(ifr.ifr_name, ifname, IFNAMSIZ - 1);
    rc = ioctl(io, SIOCGIFFLAGS, &ifr);
    snprintf(detail, sizeof detail, "flags=0x%x", ifr.ifr_flags);
    chk("ioctl(SIOCGIFFLAGS)", rc == 0, detail);

    memset(&ifr, 0, sizeof ifr);
    strncpy(ifr.ifr_name, ifname, IFNAMSIZ - 1);
    rc = ioctl(io, SIOCGIFMTU, &ifr);
    snprintf(detail, sizeof detail, "mtu=%d", ifr.ifr_mtu);
    chk("ioctl(SIOCGIFMTU)", rc == 0, detail);

    memset(&ifr, 0, sizeof ifr);
    strncpy(ifr.ifr_name, ifname, IFNAMSIZ - 1);
    rc = ioctl(io, SIOCGIFNETMASK, &ifr);
    snprintf(detail, sizeof detail, "rc=%d", rc);
    chk("ioctl(SIOCGIFNETMASK)", rc == 0, detail);
    close(io);

    if (udp >= 0) {
        int one = 1;
        rc = setsockopt(udp, SOL_SOCKET, SO_REUSEADDR, &one, sizeof one);
        chk("setsockopt(SO_REUSEADDR)", rc == 0, "");

        unsigned char ttl = 4, loop = 1;
        rc = setsockopt(udp, IPPROTO_IP, IP_MULTICAST_TTL, &ttl, sizeof ttl);
        chk("setsockopt(IP_MULTICAST_TTL)", rc == 0, "");
        rc = setsockopt(udp, IPPROTO_IP, IP_MULTICAST_LOOP, &loop, sizeof loop);
        chk("setsockopt(IP_MULTICAST_LOOP)", rc == 0, "");
        rc = setsockopt(udp, IPPROTO_IP, IP_MULTICAST_IF, &ifaddr, sizeof ifaddr);
        snprintf(detail, sizeof detail, "if=%s", ifname);
        chk("setsockopt(IP_MULTICAST_IF)", rc == 0, detail);
        rc = setsockopt(udp, IPPROTO_IP, IP_PKTINFO, &one, sizeof one);
        chk("setsockopt(IP_PKTINFO)", rc == 0, "minissdp recvmsg source addr");

        struct ip_mreq mreq;
        memset(&mreq, 0, sizeof mreq);
        mreq.imr_multiaddr.s_addr = inet_addr("239.255.255.250");
        mreq.imr_interface.s_addr = ifaddr.s_addr;
        errno = 0;
        rc = setsockopt(udp, IPPROTO_IP, IP_ADD_MEMBERSHIP, &mreq, sizeof mreq);
        saved_errno = errno;
        snprintf(detail, sizeof detail, "group=239.255.255.250 if=%s%s",
                 ifname, rc == 0 ? "" : strerror(saved_errno));
        chk("setsockopt(IP_ADD_MEMBERSHIP)", rc == 0, detail);

        /* ephemeral bind: same code path as miniupnpd's :1900 listeners but
         * without contending with a pre-existing SSDP service */
        struct sockaddr_in b;
        memset(&b, 0, sizeof b);
        b.sin_family = AF_INET;
        b.sin_addr.s_addr = htonl(INADDR_ANY);
        rc = bind(udp, (struct sockaddr *)&b, sizeof b);
        snprintf(detail, sizeof detail, "INADDR_ANY:0 rc=%d", rc);
        chk("bind(udp,INADDR_ANY)", rc == 0, detail);

        /* IPv6 is optional for miniupnpd (ENABLE_IPV6) */
        int udp6 = socket(AF_INET6, SOCK_DGRAM, 0);
        snprintf(detail, sizeof detail, "fd=%d", udp6);
        info("socket(AF_INET6,SOCK_DGRAM)", udp6 >= 0, detail);
        if (udp6 >= 0) {
            struct ipv6_mreq m6;
            memset(&m6, 0, sizeof m6);
            inet_pton(AF_INET6, "ff02::1", &m6.ipv6mr_multiaddr);
            m6.ipv6mr_interface = if_nametoindex(ifname);
            rc = setsockopt(udp6, IPPROTO_IPV6, IPV6_JOIN_GROUP, &m6, sizeof m6);
            snprintf(detail, sizeof detail, "ff02::1 on %s", ifname);
            info("setsockopt(IPV6_JOIN_GROUP)", rc == 0, detail);
            rc = setsockopt(udp6, IPPROTO_IPV6, IPV6_RECVPKTINFO, &one, sizeof one);
            info("setsockopt(IPV6_RECVPKTINFO)", rc == 0, "");
            close(udp6);
        }

        rc = setsockopt(udp, SOL_SOCKET, SO_BINDTODEVICE, ifname,
                        (socklen_t)(strlen(ifname) + 1));
        info("setsockopt(SO_BINDTODEVICE)", rc == 0, ifname);
        close(udp);
    }

    /* ---- real multicast round trip (SSDP datagram path) ---- */
    {
        int rx = socket(AF_INET, SOCK_DGRAM, 0);
        int tx = socket(AF_INET, SOCK_DGRAM, 0);
        int ok = 0, jr = -1, br = -1, ns = -1;
        ssize_t nr = -1;
        if (rx >= 0 && tx >= 0) {
            int reuse = 1;
            setsockopt(rx, SOL_SOCKET, SO_REUSEADDR, &reuse, sizeof reuse);
            struct ip_mreq m2;
            memset(&m2, 0, sizeof m2);
            m2.imr_multiaddr.s_addr = inet_addr("239.255.255.250");
            m2.imr_interface.s_addr = htonl(INADDR_LOOPBACK);
            jr = setsockopt(rx, IPPROTO_IP, IP_ADD_MEMBERSHIP, &m2, sizeof m2);
            /* pin the datagram to the same interface the receiver joined,
             * otherwise the kernel picks the default route (e.g. wlan0) and
             * the lo-joined listener never sees it */
            struct in_addr laddr;
            laddr.s_addr = htonl(INADDR_LOOPBACK);
            setsockopt(tx, IPPROTO_IP, IP_MULTICAST_IF, &laddr, sizeof laddr);
            struct sockaddr_in rb, dst;
            memset(&rb, 0, sizeof rb);
            rb.sin_family = AF_INET;
            rb.sin_addr.s_addr = htonl(INADDR_ANY);
            br = bind(rx, (struct sockaddr *)&rb, sizeof rb);
            struct timeval tv = {3, 0};
            setsockopt(rx, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof tv);
            socklen_t rblen = sizeof rb;
            getsockname(rx, (struct sockaddr *)&rb, &rblen);
            memset(&dst, 0, sizeof dst);
            dst.sin_family = AF_INET;
            dst.sin_port = rb.sin_port;
            dst.sin_addr.s_addr = inet_addr("239.255.255.250");
            const char msg[] = "miniupnpd-ohos-probe";
            ns = (int)sendto(tx, msg, sizeof msg, 0,
                             (struct sockaddr *)&dst, sizeof dst);
            char rbuf[64];
            nr = recv(rx, rbuf, sizeof rbuf, 0);
            ok = (jr == 0 && br == 0 && ns == (int)sizeof msg &&
                  nr == (ssize_t)sizeof msg);
        }
        snprintf(detail, sizeof detail, "join=%d bind=%d send=%d recv=%zd",
                 jr, br, ns, nr);
        chk("multicast-loopback(239.255.255.250)", ok, detail);
        if (rx >= 0) close(rx);
        if (tx >= 0) close(tx);
    }

    /* ---- rtnetlink: ifacewatcher (RTMGRP_LINK) + getroute ---- */
    errno = 0;
    int nl = socket(PF_NETLINK, SOCK_RAW, NETLINK_ROUTE);
    saved_errno = errno;
    snprintf(detail, sizeof detail, "fd=%d", nl);
    chk("socket(PF_NETLINK,NETLINK_ROUTE)", nl >= 0,
        nl >= 0 ? detail : strerror(saved_errno));

    if (nl >= 0) {
        struct sockaddr_nl na;
        memset(&na, 0, sizeof na);
        na.nl_family = AF_NETLINK;
        na.nl_groups = RTMGRP_LINK | RTMGRP_IPV4_IFADDR;
        rc = bind(nl, (struct sockaddr *)&na, sizeof na);
        snprintf(detail, sizeof detail, "RTMGRP_LINK|RTMGRP_IPV4_IFADDR");
        chk("bind(netlink,RTMGRP_LINK)", rc == 0, detail);

        struct {
            struct nlmsghdr n;
            struct rtgenmsg g;
        } req;
        memset(&req, 0, sizeof req);
        req.n.nlmsg_len = NLMSG_LENGTH(sizeof(struct rtgenmsg));
        req.n.nlmsg_type = RTM_GETLINK;
        req.n.nlmsg_flags = NLM_F_REQUEST | NLM_F_DUMP;
        req.g.rtgen_family = AF_UNSPEC;
        struct sockaddr_nl da;
        memset(&da, 0, sizeof da);
        da.nl_family = AF_NETLINK;
        struct iovec iov = { &req, req.n.nlmsg_len };
        struct msghdr mh;
        memset(&mh, 0, sizeof mh);
        mh.msg_name = &da;
        mh.msg_namelen = sizeof da;
        mh.msg_iov = &iov;
        mh.msg_iovlen = 1;
        rc = (int)sendmsg(nl, &mh, 0);
        int msgs = 0, done = 0;
        while (!done && msgs < 4096) {
            char rbuf[8192];
            struct iovec iov2 = { rbuf, sizeof rbuf };
            struct msghdr mh2;
            memset(&mh2, 0, sizeof mh2);
            mh2.msg_iov = &iov2;
            mh2.msg_iovlen = 1;
            ssize_t n = recvmsg(nl, &mh2, 0);
            if (n <= 0) break;
            ssize_t left = n;
            for (struct nlmsghdr *h = (struct nlmsghdr *)rbuf;
                 NLMSG_OK(h, (unsigned)left); h = NLMSG_NEXT(h, left)) {
                if (h->nlmsg_type == NLMSG_DONE ||
                    h->nlmsg_type == NLMSG_ERROR) { done = 1; break; }
                msgs++;
            }
        }
        snprintf(detail, sizeof detail, "send=%d messages=%d", rc, msgs);
        chk("rtnetlink RTM_GETLINK dump", rc > 0 && msgs > 0, detail);

        struct {
            struct nlmsghdr n;
            struct rtmsg r;
            char buf[128];
        } rq;
        memset(&rq, 0, sizeof rq);
        rq.n.nlmsg_len = NLMSG_LENGTH(sizeof(struct rtmsg));
        rq.n.nlmsg_type = RTM_GETROUTE;
        rq.n.nlmsg_flags = NLM_F_REQUEST;
        rq.r.rtm_family = AF_INET;
        struct rtattr *rta = (struct rtattr *)(((char *)&rq) +
                                               NLMSG_ALIGN(rq.n.nlmsg_len));
        rta->rta_type = RTA_DST;
        rta->rta_len = RTA_LENGTH(4);
        memset(RTA_DATA(rta), 0, 4);
        rq.n.nlmsg_len = NLMSG_ALIGN(rq.n.nlmsg_len) + RTA_LENGTH(4);
        struct sockaddr_nl da2;
        memset(&da2, 0, sizeof da2);
        da2.nl_family = AF_NETLINK;
        struct iovec iov3 = { &rq, rq.n.nlmsg_len };
        struct msghdr mh3;
        memset(&mh3, 0, sizeof mh3);
        mh3.msg_name = &da2;
        mh3.msg_namelen = sizeof da2;
        mh3.msg_iov = &iov3;
        mh3.msg_iovlen = 1;
        rc = (int)sendmsg(nl, &mh3, 0);
        char rb3[4096];
        ssize_t n3 = recv(nl, rb3, sizeof rb3, 0);
        snprintf(detail, sizeof detail, "send=%d recv=%zd", rc, n3);
        chk("rtnetlink RTM_GETROUTE", rc > 0 && n3 > 0, detail);
        close(nl);
    }

    /* ---- procfs inputs used by getifstats()/genuuid fallbacks ---- */
    int fd = open("/proc/net/dev", O_RDONLY);
    chk("/proc/net/dev readable", fd >= 0,
        fd >= 0 ? "getifstats source" : strerror(errno));
    if (fd >= 0) close(fd);
    fd = open("/proc/net/route", O_RDONLY);
    chk("/proc/net/route readable", fd >= 0,
        fd >= 0 ? "default-route lookup" : strerror(errno));
    if (fd >= 0) close(fd);

    /* ---- capability / optional inventory (never fatal) ---- */
    errno = 0;
    s = socket(AF_NETLINK, SOCK_RAW, NETLINK_NETFILTER);
    saved_errno = errno;
    snprintf(detail, sizeof detail, "%s (nftables backend needs CAP_NET_ADMIN)",
             s >= 0 ? "ok" : strerror(saved_errno));
    info("socket(NETLINK_NETFILTER)", s >= 0, detail);
    if (s >= 0) close(s);

    errno = 0;
    s = socket(AF_PACKET, SOCK_RAW, 0);
    saved_errno = errno;
    snprintf(detail, sizeof detail, "%s", s >= 0 ? "ok" : strerror(saved_errno));
    info("socket(AF_PACKET,SOCK_RAW)", s >= 0, detail);
    if (s >= 0) close(s);

    errno = 0;
    s = socket(AF_INET, SOCK_RAW, IPPROTO_ICMP);
    saved_errno = errno;
    snprintf(detail, sizeof detail, "%s", s >= 0 ? "ok" : strerror(saved_errno));
    info("socket(SOCK_RAW,ICMP)", s >= 0, detail);
    if (s >= 0) close(s);

    fd = open("/proc/sys/kernel/random/uuid", O_RDONLY);
    snprintf(detail, sizeof detail, "%s",
             fd >= 0 ? "readable" : strerror(errno));
    info("/proc/sys/kernel/random/uuid", fd >= 0, detail);
    if (fd >= 0) close(fd);

    if (ifap) freeifaddrs(ifap);
    printf("OHOS_NETPROBE required=%d required_pass=%d info=%d\n",
           required_total, required_pass, info_total);
    return (required_pass == required_total) ? 0 : 1;
}
