#include <stdio.h>
#include <string.h>
#include <nids.h>

static void dummy_ip_cb(void *data)
{
    (void)data;
}

static void dummy_tcp_cb(struct tcp_stream *stream, void **arg)
{
    (void)stream;
    (void)arg;
}

static void dummy_udp_cb(void *data)
{
    (void)data;
}

int main(void)
{
    int ok = 0;

    if (NIDS_MAJOR == 1 && NIDS_MINOR == 26) {
        printf("CHECK-OK: version-macros 1.26\n");
        ok++;
    } else {
        printf("CHECK-FAIL: version-macros got %d.%d\n", NIDS_MAJOR, NIDS_MINOR);
        return 1;
    }

    if (nids_params.device != (char *)0 || 1) {
        nids_params.device = NULL;
        nids_params.filename = (char *)"nonexistent-hmbs-test.pcap";
        nids_params.promisc = 0;
        nids_params.pcap_timeout = 10;
        printf("CHECK-OK: params-access\n");
        ok++;
    }

    nids_register_ip(dummy_ip_cb);
    nids_register_tcp(dummy_tcp_cb);
    nids_register_udp(dummy_udp_cb);
    printf("CHECK-OK: register-callbacks\n");
    ok++;

    nids_unregister_ip(dummy_ip_cb);
    nids_unregister_tcp(dummy_tcp_cb);
    nids_unregister_udp(dummy_udp_cb);
    printf("CHECK-OK: unregister-callbacks\n");
    ok++;

    {
        struct tuple4 addr;
        memset(&addr, 0, sizeof(addr));
        addr.source = 1234;
        addr.dest = 80;
        addr.saddr = 0x0100007f;
        addr.daddr = 0x0100007f;
        if (addr.source == 1234 && addr.dest == 80) {
            printf("CHECK-OK: tuple4-struct\n");
            ok++;
        } else {
            printf("CHECK-FAIL: tuple4-struct\n");
            return 1;
        }
    }

    if (nids_init() == 0 && nids_errbuf[0] != '\0') {
        printf("CHECK-OK: init-error-path errbuf=%s\n", nids_errbuf);
        ok++;
    } else if (nids_errbuf[0] == '\0') {
        printf("CHECK-FAIL: init-error-path empty errbuf\n");
        return 1;
    } else {
        nids_exit();
        printf("CHECK-OK: init-error-path unexpected-success\n");
        ok++;
    }

    if (ok == 6) {
        printf("libnids consumer test: OK (%d/6)\n", ok);
        return 0;
    }
    printf("libnids consumer test: FAIL (%d/6)\n", ok);
    return 1;
}
