#include <stdio.h>
#include <vo-aacenc/voAAC.h>

int main(void)
{
    VO_AUDIO_CODECAPI api = {0};
    VO_S32 result = voGetAACEncAPI(&api);

    if (result != VO_ERR_NONE) {
        if (fprintf(stderr, "voGetAACEncAPI failed: %ld\n", (long)result) < 0) {
            return 3;
        }
        return 1;
    }
    if (api.Init == NULL || api.SetInputData == NULL ||
        api.GetOutputData == NULL || api.Uninit == NULL) {
        if (fputs("voGetAACEncAPI returned an incomplete function table\n",
                  stderr) == EOF) {
            return 3;
        }
        return 2;
    }

    if (puts("libvo-aacenc API test: OK") == EOF) {
        return 3;
    }
    return 0;
}
