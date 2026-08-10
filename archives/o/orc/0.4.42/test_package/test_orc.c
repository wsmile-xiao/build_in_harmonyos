#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <orc/orc.h>
#include <orc/orcparse.h>

static int check(int condition, const char *message)
{
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message);
        return 1;
    }
    return 0;
}

int main(void)
{
    int failures = 0;

    orc_init();

    const char *version = orc_version_string();
    failures += check(version != NULL && strstr(version, "0.4.42") != NULL,
                      "orc_version_string reports 0.4.42");

    OrcProgram *program = orc_program_new();
    failures += check(program != NULL, "orc_program_new returns a program");

    if (program != NULL) {
        orc_program_set_name(program, "orc_copy_bytes");
        failures += check(strcmp(orc_program_get_name(program), "orc_copy_bytes") == 0,
                          "program name round-trips");

        int dest = orc_program_add_destination(program, 1, "d1");
        int src = orc_program_add_source(program, 1, "s1");
        failures += check(dest >= 0 && src >= 0, "destination and source are added");

        orc_program_append(program, "copyb", ORC_VAR_D1, ORC_VAR_S1, ORC_VAR_D1);

        OrcCompileResult result = orc_program_compile(program);
        failures += check(result == ORC_COMPILE_RESULT_OK,
                          "program compiles successfully");

        orc_program_free(program);
    }

    const char parsed_code[] = ".function orc_add_s16\n"
        ".dest 2 d1 orc_int16\n.source 2 s1 orc_int16\n.source 2 s2 orc_int16\n"
        "\naddw d1, s1, s2\n";
    OrcProgram **programs = NULL;
    int parsed = orc_parse(parsed_code, &programs);
    failures += check(parsed == 1 && programs != NULL,
                      "orc_parse accepts a simple addw program");
    if (programs != NULL) {
        for (int i = 0; i < parsed; ++i) {
            orc_program_free(programs[i]);
        }
        free(programs);
    }

    if (failures != 0) {
        return 1;
    }

    printf("orc consumer checks passed\n");
    return 0;
}
