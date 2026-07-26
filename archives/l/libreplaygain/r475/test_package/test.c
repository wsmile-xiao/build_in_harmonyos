#include <stdio.h>
#include <replaygain/gain_analysis.h>

int main(void)
{
    Float_t samples[64] = {0};

    if (gain_init_analysis(44100) != INIT_GAIN_ANALYSIS_OK) {
        if (fputs("gain_init_analysis failed\n", stderr) == EOF) {
            return 3;
        }
        return 1;
    }
    if (gain_analyze_samples(samples, NULL, 64, 1) != GAIN_ANALYSIS_OK) {
        if (fputs("gain_analyze_samples failed\n", stderr) == EOF) {
            return 3;
        }
        return 2;
    }

    if (puts("libreplaygain analysis test: OK") == EOF) {
        return 3;
    }
    return 0;
}
