#include <stdio.h>
#include <string.h>

#include <vo-aacenc/cmnMemory.h>
#include <vo-aacenc/voAAC.h>

int main(void)
{
    VO_AUDIO_CODECAPI api = {0};
    VO_MEM_OPERATOR memory = {cmnMemAlloc, cmnMemFree, cmnMemSet, cmnMemCopy,
                              cmnMemCheck, cmnMemCompare, cmnMemMove};
    VO_CODEC_INIT_USERDATA user_data = {VO_IMF_USERMEMOPERATOR, &memory};
    AACENC_PARAM params = {44100, 64000, 1, 1};
    VO_HANDLE handle = 0;
    short pcm[1024] = {0};
    unsigned char aac[20480] = {0};
    VO_CODECBUFFER input = {(VO_U8 *)pcm, sizeof(pcm), 0};
    VO_CODECBUFFER output = {aac, sizeof(aac), 0};
    VO_AUDIO_OUTPUTINFO info = {0};

    if (voGetAACEncAPI(&api) != VO_ERR_NONE || api.Init(&handle, VO_AUDIO_CodingAAC, &user_data) != VO_ERR_NONE)
        return 1;
    if (api.SetParam(handle, VO_PID_AAC_ENCPARAM, &params) != VO_ERR_NONE ||
        api.SetInputData(handle, &input) != VO_ERR_NONE ||
        api.GetOutputData(handle, &output, &info) != VO_ERR_NONE || output.Length == 0) {
        api.Uninit(handle);
        return 2;
    }
    api.Uninit(handle);
    puts("AAC frame encoded");
    return 0;
}
