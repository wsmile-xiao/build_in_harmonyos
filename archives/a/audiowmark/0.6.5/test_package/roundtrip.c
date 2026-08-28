#include <stdlib.h>
#include <stdio.h>

int main(void)
{
    const char *message = "0123456789abcdef0011223344556677";
    const char *input = "audiowmark-roundtrip-input.wav";
    const char *output = "audiowmark-roundtrip-output.wav";
    char command[512];

    snprintf(command, sizeof(command), "audiowmark test-gen-noise %s 30 44100", input);
    if (system(command) != 0)
        return 1;

    snprintf(command, sizeof(command), "audiowmark add %s %s %s", input, output, message);
    if (system(command) != 0)
        return 1;

    snprintf(command, sizeof(command), "audiowmark cmp %s %s --expect-matches 1", output, message);
    if (system(command) != 0)
        return 1;

    remove(input);
    remove(output);
    return 0;
}
