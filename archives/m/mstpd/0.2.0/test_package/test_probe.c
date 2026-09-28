/*
 * test_probe.c — mstpd 0.2.0 runtime capability probe (HarmonyOS PC)
 *
 * mstpd is a user-space IEEE 802.1D/802.1Q spanning tree daemon.  Every call
 * below is one that upstream really performs; each is executed once, read-only,
 * and reported as the literal call expression plus rc and errno.  Nothing is
 * created outside the build directory and no privilege is assumed, so a failure
 * line is evidence about the platform rather than about a mistake in this
 * program; the positive controls are what tells the two apart.
 *
 * Upstream call sites:
 *   libnetlink.c:54        socket(AF_NETLINK, SOCK_RAW, NETLINK_ROUTE) + bind
 *   packet.c:167           socket(PF_PACKET, SOCK_RAW, htons(ETH_P_802_2))
 *   ctl_socket_server.c    server_socket(): PF_UNIX SOCK_DGRAM + abstract bind
 *   bridge_track.c /
 *   ctl_main.c:452         scandir("/sys/class/net")
 *   epoll_loop.c:44        epoll_create(128), epoll_ctl(ADD/DEL), epoll_wait
 *   netif_utils.c:64+      ioctl SIOCGIFHWADDR / SIOCGIFFLAGS / SIOCETHTOOL
 *   termios                not used by mstpd; probed because the platform
 *                          census sheet lists it as an uncovered family.
 */
#define _GNU_SOURCE
#include <arpa/inet.h>
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <termios.h>
#include <unistd.h>

#include <net/if.h>
#include <sys/epoll.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/un.h>

#include <linux/ethtool.h>
#include <linux/if_ether.h>
#include <linux/if_packet.h>
#include <linux/netlink.h>
#include <linux/rtnetlink.h>
#include <linux/sockios.h>

/* A successful call leaves a stale errno behind, which would read as a failure
 * in the evidence table, so errno is reported for failures only. */
static void rep(const char *call, long rc)
{
    int e = (rc >= 0) ? 0 : errno;
    printf("PROBE %-56s rc=%-4ld errno=%-4d %s\n", call, rc, e,
           rc >= 0 ? "OK" : strerror(e));
}

static void probe_path(const char *call, const char *path)
{
    struct stat st;
    int rc = stat(path, &st);
    int e = (rc == 0) ? 0 : errno;
    printf("PROBE %-56s path=%-22s rc=%-3d errno=%-4d %s\n", call, path, rc, e,
           rc == 0 ? "OK" : strerror(e));
    if (rc == 0)
        printf("      %s exists, st_mode=0%o\n", path, (unsigned)st.st_mode);
}

int main(void)
{
    setvbuf(stdout, NULL, _IOLBF, 0);

    puts("== netlink route socket (mstpd control channel) ==");
    int nl = socket(AF_NETLINK, SOCK_RAW, NETLINK_ROUTE);
    rep("socket(AF_NETLINK, SOCK_RAW, NETLINK_ROUTE)", nl);
    if (nl >= 0) {
        struct sockaddr_nl local;
        socklen_t len = sizeof(local);
        memset(&local, 0, sizeof(local));
        local.nl_family = AF_NETLINK;
        rep("bind(nl, {AF_NETLINK, pid=0, groups=0})",
            bind(nl, (struct sockaddr *)&local, sizeof(local)));
        memset(&local, 0, sizeof(local));
        len = sizeof(local);
        rep("getsockname(nl)", getsockname(nl, (struct sockaddr *)&local, &len));
        printf("      kernel assigned nl_pid=%u nl_groups=0x%x\n",
               local.nl_pid, local.nl_groups);

        struct {
            struct nlmsghdr nlh;
            struct ifinfomsg ifi;
        } req;
        memset(&req, 0, sizeof(req));
        req.nlh.nlmsg_len = NLMSG_LENGTH(sizeof(struct ifinfomsg));
        req.nlh.nlmsg_type = RTM_GETLINK;
        req.nlh.nlmsg_flags = NLM_F_REQUEST | NLM_F_DUMP;
        req.ifi.ifi_family = AF_UNSPEC;
        ssize_t s = send(nl, &req, req.nlh.nlmsg_len, 0);
        rep("send(nl, RTM_GETLINK|NLM_F_DUMP)", (long)s);
        if (s >= 0) {
            char buf[8192];
            ssize_t r = recv(nl, buf, sizeof(buf), 0);
            rep("recv(nl, dump reply)", (long)r);
            int links = 0, bridges = 0;
            if (r > 0) {
                struct nlmsghdr *h;
                for (h = (struct nlmsghdr *)buf; NLMSG_OK(h, (size_t)r);
                     h = NLMSG_NEXT(h, r)) {
                    if (h->nlmsg_type == NLMSG_DONE)
                        break;
                    if (h->nlmsg_type == NLMSG_ERROR) {
                        struct nlmsgerr *err = (struct nlmsgerr *)NLMSG_DATA(h);
                        printf("      NLMSG_ERROR error=%d %s\n", err->error,
                               strerror(-err->error));
                        break;
                    }
                    if (h->nlmsg_type != RTM_NEWLINK)
                        continue;
                    struct ifinfomsg *ifi = (struct ifinfomsg *)NLMSG_DATA(h);
                    int rem = (int)h->nlmsg_len - (int)NLMSG_LENGTH(sizeof(*ifi));
                    struct rtattr *rt;
                    links++;
                    for (rt = (struct rtattr *)(ifi + 1); RTA_OK(rt, rem);
                         rt = RTA_NEXT(rt, rem)) {
                        if (rt->rta_type == IFLA_INFO_KIND &&
                            strcmp((const char *)RTA_DATA(rt), "bridge") == 0)
                            bridges++;
                    }
                }
            }
            printf("      RTM_GETLINK dump: links=%d bridge_kind=%d\n", links, bridges);
        }
        close(nl);
    }

    puts("== PF_PACKET raw socket (BPDU TX/RX, packet.c:167) ==");
    int pkt = socket(PF_PACKET, SOCK_RAW, htons(ETH_P_802_2));
    rep("socket(PF_PACKET, SOCK_RAW, htons(ETH_P_802_2))", pkt);
    if (pkt >= 0) {
        struct sockaddr_ll sll;
        memset(&sll, 0, sizeof(sll));
        sll.sll_family = AF_PACKET;
        sll.sll_protocol = htons(ETH_P_802_2);
        sll.sll_ifindex = (int)if_nametoindex("lo");
        rep("bind(pkt, {AF_PACKET, lo})", bind(pkt, (struct sockaddr *)&sll, sizeof(sll)));
        close(pkt);
    }
    int pkt_dgram = socket(PF_PACKET, SOCK_DGRAM, htons(ETH_P_802_2));
    rep("socket(PF_PACKET, SOCK_DGRAM, htons(ETH_P_802_2))", pkt_dgram);
    if (pkt_dgram >= 0)
        close(pkt_dgram);

    puts("== AF_UNIX abstract namespace (mstpctl control channel) ==");
    int us = socket(PF_UNIX, SOCK_DGRAM, 0);
    rep("socket(PF_UNIX, SOCK_DGRAM, 0)", us);
    if (us >= 0) {
        int creds = 1;
        rep("setsockopt(us, SOL_SOCKET, SO_PASSCRED, 1)",
            setsockopt(us, SOL_SOCKET, SO_PASSCRED, &creds, sizeof(creds)));
        const char *name = ".mstp_server_probe";
        struct sockaddr_un sa;
        memset(&sa, 0, sizeof(sa));
        sa.sun_family = AF_UNIX;
        sa.sun_path[0] = 0;
        memcpy(sa.sun_path + 1, name, strlen(name) + 1);
        socklen_t sl = (socklen_t)(offsetof(struct sockaddr_un, sun_path) + 1 +
                                   strlen(name) + 1);
        rep("bind(us, abstract .mstp_server_probe)",
            bind(us, (struct sockaddr *)&sa, sl));
        close(us);
    }

    puts("== sysfs bridge enumeration (SYSFS_CLASS_NET) ==");
    probe_path("stat(\"/sys/class/net\")", "/sys/class/net");
    probe_path("stat(\"/sys/class/tty\") [control]", "/sys/class/tty");
    DIR *dp = opendir("/sys/class/net");
    if (dp) {
        int n = 0;
        while (readdir(dp) != NULL)
            n++;
        closedir(dp);
        printf("PROBE opendir(\"/sys/class/net\")  rc=0 entries=%d\n", n);
    } else {
        printf("PROBE opendir(\"/sys/class/net\")  rc=-1 errno=%d %s\n",
               errno, strerror(errno));
    }
    /* upstream lists the class dir with scandir() (ctl_main.c:452), so probe
     * that exact call; a single attribute file is opened by name afterwards,
     * because a denied listing does not by itself deny direct access */
    struct dirent **namelist = NULL;
    int sn = scandir("/sys/class/net", &namelist, NULL, alphasort);
    printf("PROBE scandir(\"/sys/class/net\")  rc=%d errno=%d %s\n", sn,
           sn >= 0 ? 0 : errno, sn >= 0 ? "OK" : strerror(errno));
    if (sn >= 0) {
        for (int i = 0; i < sn; i++) {
            printf("      scandir entry %d: %s\n", i, namelist[i]->d_name);
            free(namelist[i]);
        }
        free(namelist);
    }
    for (unsigned idx = 1; idx <= 3; idx++) {
        char nm[IF_NAMESIZE];
        char path[160];
        if (if_indextoname(idx, nm) == NULL) {
            printf("PROBE if_indextoname(%u)  rc=-1 errno=%d %s\n",
                   idx, errno, strerror(errno));
            continue;
        }
        snprintf(path, sizeof(path), "/sys/class/net/%s/ifindex", nm);
        int fd = open(path, O_RDONLY);
        if (fd < 0) {
            printf("PROBE open(\"%s\")  rc=-1 errno=%d %s\n",
                   path, errno, strerror(errno));
            continue;
        }
        char v[32];
        ssize_t rd = read(fd, v, sizeof(v) - 1);
        int e = (rd > 0) ? 0 : errno;
        if (rd > 0) {
            v[rd] = 0;
            printf("PROBE open+read(\"%s\")  rc=%zd value=%s\n", path, rd, v);
        } else {
            printf("PROBE read(\"%s\")  rc=%zd errno=%d %s\n", path, rd, e, strerror(e));
        }
        close(fd);
    }
    DIR *dp2 = opendir("/sys/class/tty");
    if (dp2) {
        closedir(dp2);
        puts("PROBE opendir(\"/sys/class/tty\") [control]  rc=0 OK");
    } else {
        printf("PROBE opendir(\"/sys/class/tty\") [control]  rc=-1 errno=%d %s\n",
               errno, strerror(errno));
    }

    puts("== pid file / state directories ==");
    probe_path("stat(\"/var/run\")", "/var/run");
    probe_path("stat(\"/run\")", "/run");
    int ar = access("/var/run", W_OK);
    printf("PROBE access(\"/var/run\", W_OK)  rc=%d errno=%d %s\n", ar,
           ar == 0 ? 0 : errno, ar == 0 ? "OK" : strerror(errno));

    puts("== epoll event loop (epoll_loop.c) ==");
    int ep = epoll_create(128);
    rep("epoll_create(128)", ep);
    int fds[2];
    if (pipe(fds) == 0) {
        struct epoll_event ev;
        memset(&ev, 0, sizeof(ev));
        ev.events = EPOLLIN;
        ev.data.fd = fds[0];
        rep("epoll_ctl(ep, EPOLL_CTL_ADD, pipe_rd)",
            epoll_ctl(ep, EPOLL_CTL_ADD, fds[0], &ev));
        rep("epoll_wait(ep, ev, 8, 0)", epoll_wait(ep, &ev, 8, 0));
        rep("epoll_ctl(ep, EPOLL_CTL_DEL, pipe_rd)",
            epoll_ctl(ep, EPOLL_CTL_DEL, fds[0], NULL));
        close(fds[0]);
        close(fds[1]);
    } else {
        rep("pipe(fds)", -1);
    }
    if (ep >= 0)
        close(ep);

    puts("== interface ioctls (netif_utils.c) ==");
    int is = socket(AF_INET, SOCK_DGRAM, 0);
    rep("socket(AF_INET, SOCK_DGRAM, 0)", is);
    if (is >= 0) {
        struct ifreq ifr;
        memset(&ifr, 0, sizeof(ifr));
        strncpy(ifr.ifr_name, "lo", IFNAMSIZ - 1);
        rep("ioctl(SIOCGIFFLAGS, lo) [control]", ioctl(is, SIOCGIFFLAGS, &ifr));
        memset(&ifr, 0, sizeof(ifr));
        strncpy(ifr.ifr_name, "lo", IFNAMSIZ - 1);
        rep("ioctl(SIOCGIFHWADDR, lo)", ioctl(is, SIOCGIFHWADDR, &ifr));
        struct ethtool_value edata;
        memset(&edata, 0, sizeof(edata));
        edata.cmd = ETHTOOL_GLINK;
        memset(&ifr, 0, sizeof(ifr));
        strncpy(ifr.ifr_name, "lo", IFNAMSIZ - 1);
        ifr.ifr_data = (void *)&edata;
        rep("ioctl(SIOCETHTOOL, ETHTOOL_GLINK, lo)", ioctl(is, SIOCETHTOOL, &ifr));
        memset(&ifr, 0, sizeof(ifr));
        strncpy(ifr.ifr_name, "lo", IFNAMSIZ - 1);
        rep("ioctl(SIOCGIFBR, lo) [bridge private]", ioctl(is, SIOCGIFBR, &ifr));
        printf("      if_nametoindex(\"lo\")=%u\n", if_nametoindex("lo"));
        close(is);
    }

    puts("== termios family (census item, not used by upstream mstpd) ==");
    int ptm = posix_openpt(O_RDWR | O_NOCTTY);
    rep("posix_openpt(O_RDWR|O_NOCTTY)", ptm);
    if (ptm >= 0) {
        rep("grantpt(ptm)", grantpt(ptm));
        rep("unlockpt(ptm)", unlockpt(ptm));
        struct termios t;
        int tg = tcgetattr(ptm, &t);
        int te = (tg == 0) ? 0 : errno;
        printf("PROBE tcgetattr(ptm)  rc=%d errno=%d %s\n", tg, te,
               tg == 0 ? "OK" : strerror(te));
        if (tg == 0) {
            cfmakeraw(&t);
            rep("tcsetattr(ptm, TCSANOW, raw)", tcsetattr(ptm, TCSANOW, &t));
        }
        close(ptm);
    }

    puts("PROBE done");
    return 0;
}
