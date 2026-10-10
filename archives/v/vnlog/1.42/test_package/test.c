#include <stdio.h>
#include <string.h>
#include <vnlog/vnlog-parser.h>

int main(void)
{
    /* HarmonyOS PC's default /tmp can be read-only, so use CTest's writable cwd. */
    FILE *fp = fopen("vnlog-test-input.vnl", "w+");
    if (fp == NULL)
        return 1;
    if (fputs("# name score\nalpha 7\nbeta 11\n", fp) == EOF)
        return 2;
    rewind(fp);

    vnlog_parser_t parser;
    if (vnlog_parser_init(&parser, fp) != VNL_OK)
        return 3;
    const char *const *score = vnlog_parser_record_from_key(&parser, "score");
    if (score == NULL)
        return 4;
    if (vnlog_parser_read_record(&parser, fp) != VNL_OK || strcmp(*score, "7") != 0)
        return 5;
    if (vnlog_parser_read_record(&parser, fp) != VNL_OK || strcmp(*score, "11") != 0)
        return 6;
    if (vnlog_parser_read_record(&parser, fp) != VNL_EOF)
        return 7;
    vnlog_parser_free(&parser);
    fclose(fp);
    remove("vnlog-test-input.vnl");
    return 0;
}
