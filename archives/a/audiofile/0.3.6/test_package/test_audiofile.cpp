#include <audiofile.h>

#include <cstdio>
#include <cstring>

int main()
{
    const char *path = "audiofile-roundtrip.wav";
    const short samples[] = {100, -100, 200, -200, 300, -300};

    AFfilesetup setup = afNewFileSetup();
    if (!setup)
        return 1;
    afInitFileFormat(setup, AF_FILE_WAVE);
    afInitChannels(setup, AF_DEFAULT_TRACK, 2);
    afInitSampleFormat(setup, AF_DEFAULT_TRACK, AF_SAMPFMT_TWOSCOMP, 16);
    AFfilehandle writer = afOpenFile(path, "w", setup);
    afFreeFileSetup(setup);
    if (!writer)
        return 2;
    if (afWriteFrames(writer, AF_DEFAULT_TRACK, samples, 3) != 3 || afCloseFile(writer) != 0)
        return 3;

    AFfilehandle reader = afOpenFile(path, "r", nullptr);
    if (!reader)
        return 4;
    int sample_format = 0;
    int sample_width = 0;
    const bool metadata_matches =
        afGetFileFormat(reader, nullptr) == AF_FILE_WAVE &&
        afGetChannels(reader, AF_DEFAULT_TRACK) == 2 &&
        afGetFrameCount(reader, AF_DEFAULT_TRACK) == 3;
    afGetSampleFormat(reader, AF_DEFAULT_TRACK, &sample_format, &sample_width);
    short actual[6] = {};
    const bool samples_match =
        afReadFrames(reader, AF_DEFAULT_TRACK, actual, 3) == 3 &&
        std::memcmp(samples, actual, sizeof(samples)) == 0;
    const int close_result = afCloseFile(reader);
    std::remove(path);

    return metadata_matches && sample_format == AF_SAMPFMT_TWOSCOMP &&
                   sample_width == 16 && samples_match && close_result == 0
               ? 0
               : 5;
}
