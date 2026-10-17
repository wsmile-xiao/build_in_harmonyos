/*
 * test_pgexporter.c - Smoke test for pgexporter package.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void)
{
    FILE *fp = popen("pgexporter-admin --version 2>&1", "r");
    if (!fp)
    {
        fprintf(stderr, "ERROR: cannot execute pgexporter-admin\n");
        return 1;
    }
    char buf[256] = {0};
    if (fgets(buf, sizeof(buf), fp) == NULL)
    {
        pclose(fp);
        fprintf(stderr, "ERROR: pgexporter-admin produced no output\n");
        return 1;
    }
    pclose(fp);
    if (strstr(buf, "pgexporter") != NULL)
    {
        printf("OK: %s", buf);
        return 0;
    }
    fprintf(stderr, "ERROR: unexpected output: %s\n", buf);
    return 1;
}
