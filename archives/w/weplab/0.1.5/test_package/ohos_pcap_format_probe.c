#include <pcap.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>

/*
 * ohos_pcap_format_probe.c — OHOS libpcap consumer-surface probe for weplab 0.1.5.
 *
 * weplab's only platform runtime dependency is libpcap.  Its real usage in
 * the 0.1.5 sources is:
 *
 *   capture.c : pcap_open_live, pcap_datalink (guards against anything other
 *               than DLT_IEEE802_11 / DLT_PRISM_HEADER), pcap_next, pcap_loop,
 *               pcap_close
 *   wep.c     : pcap_open_offline (NULL + errbuf error branch -> exit 2),
 *               pcap_dump_open / pcap_dump / pcap_dump_flush / pcap_dump_close
 *               for writing capture output
 *   main.c    : pcap_lib_version
 *
 * This probe exercises exactly that surface on HarmonyOS PC aarch64.  It does
 * not assert() — every probe has a real pass/fail criterion, prints a
 * machine-readable verdict line and tallies it, and the harness reads the
 * verdicts.  Probes whose API has no return value (pcap_close) are executed
 * as cleanup and deliberately NOT counted as passes.
 *
 * Probe numbering is stable (the harness refers to "probe N"):
 *   1: pcap_lib_version() returns a non-empty string (the library loads).
 *   2: DLT_IEEE802_11 and DLT_PRISM_HEADER are both positive and distinct —
 *      capture.c discriminates between exactly these two values.
 *   3: pcap_open_dead(DLT_IEEE802_11, 65535) returns a valid pcap_t
 *      (headless stand-in for pcap_open_live).
 *   4: pcap_datalink() on that handle reports DLT_IEEE802_11.
 *   5: the capture-file WRITE path (pcap_dump_open + pcap_dump +
 *      pcap_dump_flush + pcap_dump_close) produces a well-formed savefile:
 *      24-byte global header + 16-byte record header + 16-byte payload.
 *   6: the capture-file READ path (pcap_open_offline + pcap_datalink +
 *      pcap_next) re-opens that savefile, sees DLT_IEEE802_11 and returns
 *      the very packet that was written (caplen == 16).
 *   7: pcap_open_offline() on a nonexistent path returns NULL and fills
 *      errbuf — the error branch weplab's OpenPcapFile() depends on before
 *      printing errbuf and exiting 2.
 *   8: pcap_datalink_name_to_val() on an unknown name returns -1, the
 *      documented boundary contract of the libpcap name table.
 */

#define PROBE_DUMP_FILE "ohos_probe_dump.pcap"
#define PROBE_DATA_LEN 16

/* pcap savefile layout: 24-byte global header + 16-byte record header. */
#define PCAP_GLOBAL_HEADER_LEN 24
#define PCAP_RECORD_HEADER_LEN 16

static long file_size(const char *path)
{
    struct stat st;
    if (stat(path, &st) != 0) {
        return -1;
    }
    return (long)st.st_size;
}

int main(void)
{
    int pass = 0;
    int fail = 0;

    /* Probe 1: library version string (main.c queries it). */
    const char *ver = pcap_lib_version();
    if (ver != NULL && ver[0] != '\0') {
        printf("WEPPCAP_TEST_PASS probe=1 lib_version_present\n");
        pass++;
    } else {
        printf("WEPPCAP_TEST_FAIL probe=1 lib_version_missing\n");
        fail++;
    }

    /* Probe 2: the two link-layer constants capture.c compares against. */
    if (DLT_IEEE802_11 > 0 && DLT_PRISM_HEADER > 0 &&
        DLT_IEEE802_11 != DLT_PRISM_HEADER) {
        printf("WEPPCAP_TEST_PASS probe=2 dlt_constants_ok "
               "ieee802_11=%d prism=%d\n",
               DLT_IEEE802_11, DLT_PRISM_HEADER);
        pass++;
    } else {
        printf("WEPPCAP_TEST_FAIL probe=2 dlt_constants_bad "
               "ieee802_11=%d prism=%d\n",
               DLT_IEEE802_11, DLT_PRISM_HEADER);
        fail++;
    }

    /* Probe 3: open_dead creates a pcap_t (headless capture stand-in). */
    pcap_t *p = pcap_open_dead(DLT_IEEE802_11, 65535);
    if (p != NULL) {
        printf("WEPPCAP_TEST_PASS probe=3 pcap_t_created\n");
        pass++;
    } else {
        printf("WEPPCAP_TEST_FAIL probe=3 pcap_open_dead_null\n");
        fail++;
        /* No handle — the remaining probes cannot run. */
        printf("WEPPCAP_SMOKE_DONE passed=%d failed=%d\n", pass, fail);
        return fail > 0 ? 1 : 0;
    }

    /* Probe 4: datalink enquiry returns the requested link layer. */
    int dl = pcap_datalink(p);
    if (dl == DLT_IEEE802_11) {
        printf("WEPPCAP_TEST_PASS probe=4 datalink_matches dlt=%d\n", dl);
        pass++;
    } else {
        printf("WEPPCAP_TEST_FAIL probe=4 datalink_mismatch dlt=%d expected=%d\n",
               dl, DLT_IEEE802_11);
        fail++;
    }

    /* Probe 5: write one packet through the pcap savefile write path. */
    u_char payload[PROBE_DATA_LEN];
    memset(payload, 0, sizeof(payload));
    struct pcap_pkthdr out_hdr;
    memset(&out_hdr, 0, sizeof(out_hdr));
    out_hdr.ts.tv_sec = 1;
    out_hdr.caplen = PROBE_DATA_LEN;
    out_hdr.len = PROBE_DATA_LEN;

    (void)remove(PROBE_DUMP_FILE);
    pcap_dumper_t *dumper = pcap_dump_open(p, PROBE_DUMP_FILE);
    if (dumper == NULL) {
        printf("WEPPCAP_TEST_FAIL probe=5 dump_open_null err=%s\n",
               pcap_geterr(p));
        fail++;
    } else {
        pcap_dump((u_char *)dumper, &out_hdr, payload);
        int flush_rc = pcap_dump_flush(dumper);
        pcap_dump_close(dumper);
        long written = file_size(PROBE_DUMP_FILE);
        long expected = PCAP_GLOBAL_HEADER_LEN + PCAP_RECORD_HEADER_LEN +
                        PROBE_DATA_LEN;
        if (flush_rc == 0 && written == expected) {
            printf("WEPPCAP_TEST_PASS probe=5 dump_write_ok size=%ld\n",
                   written);
            pass++;
        } else {
            printf("WEPPCAP_TEST_FAIL probe=5 dump_write_bad flush_rc=%d "
                   "size=%ld expected=%ld\n",
                   flush_rc, written, expected);
            fail++;
        }
    }

    /* Probe 6: read the packet back through the offline read path. */
    char read_errbuf[PCAP_ERRBUF_SIZE];
    memset(read_errbuf, 0, sizeof(read_errbuf));
    pcap_t *reader = pcap_open_offline(PROBE_DUMP_FILE, read_errbuf);
    if (reader == NULL) {
        printf("WEPPCAP_TEST_FAIL probe=6 offline_open_null err=%s\n",
               read_errbuf[0] != '\0' ? read_errbuf : "(empty)");
        fail++;
    } else {
        int reader_dlt = pcap_datalink(reader);
        struct pcap_pkthdr in_hdr;
        memset(&in_hdr, 0, sizeof(in_hdr));
        const u_char *packet = pcap_next(reader, &in_hdr);
        if (reader_dlt == DLT_IEEE802_11 && packet != NULL &&
            in_hdr.caplen == PROBE_DATA_LEN) {
            printf("WEPPCAP_TEST_PASS probe=6 offline_read_packet "
                   "dlt=%d caplen=%u\n",
                   reader_dlt, (unsigned)in_hdr.caplen);
            pass++;
        } else {
            printf("WEPPCAP_TEST_FAIL probe=6 offline_read_bad dlt=%d "
                   "packet=%s caplen=%u expected_len=%d\n",
                   reader_dlt, packet != NULL ? "non-null" : "null",
                   (unsigned)in_hdr.caplen, PROBE_DATA_LEN);
            fail++;
        }
        pcap_close(reader);
    }

    /* Probe 7: the offline-open error branch weplab's OpenPcapFile() uses
     * (it prints errbuf and exits 2 when the handle comes back NULL). */
    char missing_errbuf[PCAP_ERRBUF_SIZE];
    memset(missing_errbuf, 0, sizeof(missing_errbuf));
    pcap_t *missing =
        pcap_open_offline("/nonexistent-weplab-probe-input.pcap",
                          missing_errbuf);
    if (missing == NULL && missing_errbuf[0] != '\0') {
        printf("WEPPCAP_TEST_PASS probe=7 offline_missing_null err=%s\n",
               missing_errbuf);
        pass++;
    } else {
        printf("WEPPCAP_TEST_FAIL probe=7 offline_missing_unexpected "
               "handle=%s errbuf_empty=%d\n",
               missing == NULL ? "null" : "non-null",
               missing_errbuf[0] == '\0');
        fail++;
        if (missing != NULL) {
            pcap_close(missing);
        }
    }

    /* Capture-file scratch cleanup.  pcap_close() returns void and has no
     * observable success criterion, so releasing the dead handle is cleanup,
     * not a counted probe (R9/R34: no print-only passes). */
    pcap_close(p);
    (void)remove(PROBE_DUMP_FILE);

    /* Probe 8: boundary contract of the link-layer name table. */
    int bad = pcap_datalink_name_to_val("NOT_A_REAL_LINK_TYPE");
    if (bad == -1) {
        printf("WEPPCAP_TEST_PASS probe=8 unknown_name_returns_minus1\n");
        pass++;
    } else {
        printf("WEPPCAP_TEST_FAIL probe=8 unknown_name_returns=%d expected=-1\n",
               bad);
        fail++;
    }

    printf("WEPPCAP_SMOKE_DONE passed=%d failed=%d\n", pass, fail);
    return fail > 0 ? 1 : 0;
}
