/* test_package/test.c - dhcpd-pools 3.2
 *
 * dhcpd-pools is a command-line tool, so this consumer test invokes the
 * packaged binary and verifies both version output and a minimal pool report.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define EXPECTED_VERSION "dhcpd-pools 3.2"

static int write_file(const char *path, const char *content)
{
    FILE *fp = fopen(path, "w");
    if (fp == NULL) {
        fprintf(stderr, "ERROR: cannot write %s\n", path);
        return 1;
    }
    if (fputs(content, fp) == EOF) {
        fprintf(stderr, "ERROR: cannot populate %s\n", path);
        fclose(fp);
        return 1;
    }
    return fclose(fp) == 0 ? 0 : 1;
}

static int file_contains(const char *path, const char *needle)
{
    char buf[512];
    FILE *fp = fopen(path, "r");
    if (fp == NULL) {
        fprintf(stderr, "ERROR: cannot read %s\n", path);
        return 0;
    }
    while (fgets(buf, sizeof(buf), fp) != NULL) {
        if (strstr(buf, needle) != NULL) {
            fclose(fp);
            return 1;
        }
    }
    fclose(fp);
    return 0;
}

static int run_command(const char *cmd)
{
    int rc = system(cmd);
    if (rc != 0) {
        fprintf(stderr, "ERROR: command failed (%d): %s\n", rc, cmd);
        return 1;
    }
    return 0;
}

int main(void)
{
    const char *tool = getenv("DHCPD_POOLS_PATH");
    char cmd[2048];

    const char *conf =
        "subnet 10.0.0.0 netmask 255.255.255.0 {\n"
        "  pool {\n"
        "    range 10.0.0.1 10.0.0.10;\n"
        "  }\n"
        "}\n";
    const char *leases =
        "lease 10.0.0.1 {\n"
        "  binding state active;\n"
        "  hardware ethernet 00:00:00:00:00:01;\n"
        "}\n"
        "lease 10.0.0.2 {\n"
        "  binding state active;\n"
        "  hardware ethernet 00:00:00:00:00:02;\n"
        "}\n";

    if (tool == NULL || tool[0] == '\0') {
        tool = "dhcpd-pools";
    }

    snprintf(cmd, sizeof(cmd), "\"%s\" --version > version.out 2>&1", tool);
    if (run_command(cmd) != 0) {
        return 1;
    }
    if (!file_contains("version.out", EXPECTED_VERSION) || !file_contains("version.out", "uthash")) {
        fprintf(stderr, "ERROR: version output did not identify dhcpd-pools 3.2 with uthash support\n");
        return 1;
    }

    if (write_file("dhcpd.conf", conf) != 0 || write_file("dhcpd.leases", leases) != 0) {
        return 1;
    }

    snprintf(
        cmd,
        sizeof(cmd),
        "\"%s\" -c dhcpd.conf -l dhcpd.leases --color=never -o dhcpd.out > analysis.out 2>&1",
        tool
    );
    if (run_command(cmd) != 0) {
        return 1;
    }

    if (!file_contains("dhcpd.out", "All networks") ||
        !file_contains("dhcpd.out", "10.0.0.1") ||
        !file_contains("dhcpd.out", "10.0.0.10") ||
        !file_contains("dhcpd.out", "20.000")) {
        fprintf(stderr, "ERROR: dhcpd-pools report did not contain expected pool summary\n");
        return 1;
    }

    printf("test dhcpd-pools 3.2: OK\n");
    return 0;
}
