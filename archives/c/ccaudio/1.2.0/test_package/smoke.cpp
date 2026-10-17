// ccAudio 消费者测试：以库使用者身份真实调用公开 API——
// 用 AudioFile 写入 RIFF wav 并读回校验头部（编译 / 链接 / 运行 / 退出码判定）
#include <cc++/audio.h>

#include <cstdio>
#include <cstring>
#include <fstream>
#include <string>

int main() {
    const std::string path = "smoke_ccaudio.wav";

    static char annotation[] = "smoke";
    ost::Audio::Info info;
    info.format = ost::Audio::riff;
    info.encoding = ost::Audio::pcm16Stereo;
    info.rate = 44100;
    info.order = 0;
    info.annotation = annotation;

    unsigned char samples[4096];
    memset(samples, 0, sizeof(samples));

    {
        ost::AudioFile out(path.c_str(), &info);
        const int frames = static_cast<int>(sizeof(samples)) /
                           static_cast<int>(out.getFrame(ost::Audio::pcm16Stereo));
        if (out.putSamples(samples, frames) != ost::Audio::errSuccess) {
            printf("FAIL: putSamples returned error\n");
            return 1;
        }
        out.close();
    }

    char hdr[12] = {0};
    {
        std::ifstream in(path.c_str(), std::ios::binary);
        if (!in) {
            printf("FAIL: cannot reopen written wave file\n");
            return 1;
        }
        in.read(hdr, sizeof(hdr));
    }
    remove(path.c_str());

    if (memcmp(hdr, "RIFF", 4) != 0 || memcmp(hdr + 8, "WAVE", 4) != 0) {
        printf("FAIL: bad RIFF/WAVE header\n");
        return 1;
    }
    printf("ccaudio AudioFile RIFF round-trip OK\n");
    return 0;
}
