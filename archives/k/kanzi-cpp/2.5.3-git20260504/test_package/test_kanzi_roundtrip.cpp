// Consumer test: in-memory round-trip through the public C++ stream API.
// Exercises CompressedOutputStream (HUFFMAN + RLT+TEXT) and
// CompressedInputStream from <kanzi/io/...>. Deterministic: fixed 64 KiB
// input, no randomness. Any CHECK failure prints a message and exits 1.
#include <cstring>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

#include <kanzi/io/CompressedInputStream.hpp>
#include <kanzi/io/CompressedOutputStream.hpp>

static int g_checks = 0;

#define CHECK(cond, msg)                                              \
    do {                                                              \
        ++g_checks;                                                   \
        if (!(cond)) {                                                \
            std::cerr << "CHECK FAILED (" << g_checks << "): "        \
                      << msg << std::endl;                            \
            return 1;                                                 \
        }                                                             \
    } while (0)

int main()
{
    // Build a deterministic, compressible 64 KiB payload: repeated text
    // lines plus a binary counter pattern.
    const std::string line =
        "Kanzi is a modern lossless data compressor. 0123456789\n";
    std::string payload;
    payload.reserve(65536);
    for (int i = 0; i < 900; ++i) {
        payload += line;
        payload.push_back(static_cast<char>(i & 0xFF));
    }
    payload.resize(65536, 'x');
    const uint32_t length = static_cast<uint32_t>(payload.size());

    std::vector<kanzi::byte> original(length);
    std::memcpy(original.data(), payload.data(), length);

    // Compress into an in-memory stream (single job: no thread pool).
    std::stringbuf buffer;
    std::iostream ios(&buffer);
    kanzi::CompressedOutputStream cos(ios, 1, "HUFFMAN", "RLT+TEXT",
                                      32768);
    cos.write(reinterpret_cast<const char*>(original.data()), length);
    cos.close();
    const uint64_t written = cos.getWritten();
    std::cout << "original=" << length << " compressed=" << written
              << std::endl;
    CHECK(written > 0, "compressed stream is empty");
    CHECK(written < length, "compressible payload did not shrink");

    // Decompress back and compare byte for byte.
    // NOTE: follow the upstream TestCompressedStream pattern — keep reading
    // until a short read (EOF probe). Exiting the loop as soon as
    // total==length skips the trailing EOF read and leaves
    // cis.getRead() (compressed bytes consumed, (_ibs->read()+7)>>3)
    // short of cos.getWritten(), which trips the counter check even
    // though the payload is fully restored.
    std::vector<kanzi::byte> restored(length);
    ios.seekg(0);
    kanzi::CompressedInputStream cis(ios, 1);
    uint32_t total = 0;
    std::streamsize lastGot = 0;
    while (total < length) {
        const uint32_t want = length - total;
        cis.read(reinterpret_cast<char*>(restored.data()) + total, want);
        std::streamsize got = cis.gcount();
        lastGot = got;
        if (got <= 0)
            break;
        total += static_cast<uint32_t>(got);
        if (static_cast<uint32_t>(got) != want)
            break;
    }
    // EOF probe: force consumption of stream trailer/padding so the
    // compressed-byte counter advances to the final value, mirroring
    // upstream's extra read that returns 0 at end of stream.
    if (total == length) {
        char eofProbe = 0;
        cis.read(&eofProbe, 1);
        lastGot = cis.gcount();
        std::cout << "eofProbe gcount=" << lastGot << std::endl;
    }
    cis.close();
    const uint64_t readBack = cis.getRead();
    std::cout << "decompressed=" << total << " readBack=" << readBack
              << std::endl;
    CHECK(total == length, "decompressed size mismatch");
    CHECK(readBack == written, "read/written byte counters differ");
    CHECK(std::memcmp(original.data(), restored.data(), length) == 0,
          "round-trip payload differs");

    std::cout << "roundtrip OK (" << g_checks << " checks)" << std::endl;
    return 0;
}
