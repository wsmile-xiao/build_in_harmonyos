// test_libgig.cpp — libgig 消费者测试（鸿蒙侧新增，rule12「鸿蒙特有测试」）
//
// 三段断言：
//   ① 版本指纹：被测产物自报的上游版本必须是 4.5.2（防止链接到系统同名库/陈旧产物）
//   ② RIFF 层往返：建含 24 字节自定义块的 RIFF → 存盘 → 重开 → 逐字节比对
//   ③ gig  层往返：新建 .gig（1 样本 / 1 乐器 / 1 区域）→ 存盘 → 重开 → 断言结构
//
// 只使用上游公开头文件与公开 API；不使用测试专用内部符号。
#include <cstdio>
#include <cstring>
#include <string>

#include <RIFF.h>
#include <SF.h>   // 仅为 RIFF_ID() 宏（上游 RiffTests.cpp 同样只用它取该宏）
#include <gig.h>

namespace {

int g_checks = 0;
int g_errors = 0;

void report(bool ok, const std::string& what, const char* file, int line) {
    ++g_checks;
    if (!ok) {
        ++g_errors;
        std::fprintf(stderr, "[FAIL] %s:%d: %s\n", file, line, what.c_str());
    }
}

void check(bool ok, const char* expr, const char* file, int line) {
    report(ok, expr, file, line);
}

void checkEqStr(const std::string& got, const std::string& want,
                const char* file, int line) {
    report(got == want,
           std::string("expected \"") + want + "\", got \"" + got + "\"",
           file, line);
}

void checkEqInt(long long got, long long want, const char* expr,
                const char* file, int line) {
    char buf[160];
    std::snprintf(buf, sizeof(buf), "%s (expected %lld, got %lld)",
                  expr, want, got);
    report(got == want, buf, file, line);
}

bool fileExists(const char* path) {
    FILE* handle = std::fopen(path, "r");
    if (!handle) return false;
    std::fclose(handle);
    return true;
}

long fileSize(const char* path) {
    FILE* handle = std::fopen(path, "rb");
    if (!handle) return -1;
    std::fseek(handle, 0, SEEK_END);
    const long size = std::ftell(handle);
    std::fclose(handle);
    return size;
}

} // namespace

#define CHECK(cond)            check((cond), #cond, __FILE__, __LINE__)
#define CHECK_STR(got, want)   checkEqStr((got), (want), __FILE__, __LINE__)
#define CHECK_INT(got, want)   checkEqInt((got), (want), #got, __FILE__, __LINE__)

int main() {
    // ── ① 版本指纹 ─────────────────────────────────────────────────────
    CHECK_STR(RIFF::libraryVersion(), "4.5.2");
    CHECK_STR(gig::libraryVersion(), "4.5.2");
    CHECK_STR(gig::libraryVersion(), RIFF::libraryVersion());

    // ── ② RIFF 层往返 ──────────────────────────────────────────────────
    const char* rriffPath = "test_libgig.riff";
    std::remove(rriffPath);
    {
        RIFF::File file(RIFF_ID("abcd"));
        RIFF::Chunk* chunk = file.AddSubChunk(RIFF_ID("data"), 24);
        CHECK(chunk != NULL);
        char* buf = static_cast<char*>(chunk->LoadChunkData());
        CHECK(buf != NULL);
        if (buf) {
            for (int i = 0; i < 24; ++i) buf[i] = static_cast<char>(i);
        }
        file.Save(rriffPath);
    }
    CHECK(fileExists(rriffPath));
    CHECK_INT(fileSize(rriffPath), 3 * 4 + 2 * 4 + 24);
    {
        RIFF::File riff(rriffPath);
        RIFF::Chunk* chunk = riff.GetSubChunk(RIFF_ID("data"));
        CHECK(chunk != NULL);
        if (chunk) {
            char* buf = static_cast<char*>(chunk->LoadChunkData());
            CHECK(buf != NULL);
            if (buf) {
                bool identical = true;
                for (int i = 0; i < 24; ++i) {
                    if (buf[i] != static_cast<char>(i)) identical = false;
                }
                CHECK(identical);
            }
        }
    }

    // ── ③ gig 层往返 ───────────────────────────────────────────────────
    const char* gigPath = "test_libgig.gig";
    std::remove(gigPath);
    {
        gig::File file;
        file.pInfo->Name = "HarmonyPC libgig consumer test";

        gig::Sample* sample = file.AddSample();
        CHECK(sample != NULL);
        sample->pInfo->Name = "consumer sample";
        sample->Channels = 1;
        sample->BitDepth = 16;
        sample->FrameSize = 16 / 8 * 1;
        sample->SamplesPerSecond = 44100;
        sample->Resize(3);

        gig::Instrument* instrument = file.AddInstrument();
        CHECK(instrument != NULL);
        instrument->pInfo->Name = "consumer instrument";
        gig::Region* region = instrument->AddRegion();
        CHECK(region != NULL);
        region->SetSample(sample);
        region->KeyRange.low = 0;
        region->KeyRange.high = 1;
        region->VelocityRange.low = 0;
        region->VelocityRange.high = 1;
        region->KeyGroup = 0;
        region->pDimensionRegions[0]->pSample = sample;
        file.Save(gigPath);
    }
    CHECK(fileExists(gigPath));
    CHECK(fileSize(gigPath) > 0);
    {
        RIFF::File riff(gigPath);
        gig::File file(&riff);
        CHECK(file.pInfo != NULL);
        CHECK_STR(file.pInfo->Name, "HarmonyPC libgig consumer test");
        CHECK_INT(file.Instruments, 1);
        CHECK_INT(file.CountInstruments(), 1);
        CHECK_INT(file.CountSamples(), 1);

        gig::Sample* sample = file.GetSample(0);
        CHECK(sample != NULL);
        if (sample) {
            CHECK_STR(sample->pInfo->Name, "consumer sample");
            CHECK_INT(sample->SamplesTotal, 3);
            CHECK_INT(sample->Channels, 1);
            CHECK_INT(sample->BitDepth, 16);
            CHECK_INT(sample->FrameSize, 16 / 8 * 1);
            CHECK_INT(sample->SamplesPerSecond, 44100);
        }
        gig::Instrument* instrument = file.GetInstrument(0);
        CHECK(instrument != NULL);
        if (instrument) {
            CHECK_STR(instrument->pInfo->Name, "consumer instrument");
            CHECK_INT(instrument->CountRegions(), 1);
        }
    }

    std::remove(rriffPath);
    std::remove(gigPath);

    std::printf("libgig consumer test: %d checks, %d errors\n",
                g_checks, g_errors);
    return g_errors == 0 ? 0 : 1;
}
