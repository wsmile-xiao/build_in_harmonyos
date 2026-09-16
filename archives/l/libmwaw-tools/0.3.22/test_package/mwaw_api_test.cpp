// Substantive API test for libmwaw:
// calls MWAWDocument::isFileFormatSupported() on in-memory streams and
// asserts on the classification result. Requires librevenge-stream headers.
//
// The librevenge 0.0.5 package does not ship RVNGMemoryStream, so a minimal
// in-memory RVNGInputStream is implemented here.
#include <cstdio>
#include <cstdlib>

#include "librevenge-stream/RVNGStream.h"
#include "libmwaw/libmwaw.hxx"

#define CHECK(cond) \
    do { \
        if (!(cond)) { \
            std::fprintf(stderr, "FAIL: %s (line %d)\n", #cond, __LINE__); \
            return 1; \
        } \
    } while (0)

using librevenge::RVNGInputStream;
using librevenge::RVNG_SEEK_CUR;
using librevenge::RVNG_SEEK_END;
using librevenge::RVNG_SEEK_SET;
using librevenge::RVNG_SEEK_TYPE;

namespace
{

class MemoryStream final : public RVNGInputStream
{
public:
    MemoryStream(const unsigned char *data, size_t size)
        : m_data(data)
        , m_size(size)
        , m_pos(0)
    {}

    bool isStructured() override { return false; }
    unsigned subStreamCount() override { return 0; }
    const char *subStreamName(unsigned) override { return ""; }
    bool existsSubStream(const char *) override { return false; }
    RVNGInputStream *getSubStreamByName(const char *) override { return nullptr; }
    RVNGInputStream *getSubStreamById(unsigned) override { return nullptr; }

    const unsigned char *read(unsigned long numBytes, unsigned long &numBytesRead) override
    {
        if (m_pos >= m_size)
        {
            numBytesRead = 0;
            return nullptr;
        }
        size_t avail = m_size - m_pos;
        size_t n = numBytes < avail ? numBytes : static_cast<unsigned long>(avail);
        numBytesRead = static_cast<unsigned long>(n);
        m_pos += n;
        return m_data + m_pos - n;
    }

    int seek(long offset, RVNG_SEEK_TYPE seekType) override
    {
        long base = 0;
        switch (seekType)
        {
            case RVNG_SEEK_SET:
                base = 0;
                break;
            case RVNG_SEEK_CUR:
                base = static_cast<long>(m_pos);
                break;
            case RVNG_SEEK_END:
                base = static_cast<long>(m_size);
                break;
        }
        long target = base + offset;
        if (target < 0 || target > static_cast<long>(m_size))
            return -1;
        m_pos = static_cast<size_t>(target);
        return 0;
    }

    long tell() override { return static_cast<long>(m_pos); }
    bool isEnd() override { return m_pos >= m_size; }

private:
    const unsigned char *m_data;
    size_t m_size;
    size_t m_pos;
};

} // namespace

int main()
{
    // MWAWDocument is declared in the global namespace (the librevenge
    // namespace in MWAWDocument.hxx only forward-declares its stream types).
    using MWAWDocument = ::MWAWDocument;
    using Type = MWAWDocument::Type;
    using Kind = MWAWDocument::Kind;
    using Confidence = MWAWDocument::Confidence;

    // 1. A stream with a random (non-Mac) payload must NOT be recognized
    //    as a supported MWAW format.
    {
        const char payload[] = "this is definitely not a Mac document payload, 1234567890";
        MemoryStream stream(reinterpret_cast<const unsigned char *>(payload), sizeof(payload) - 1);
        Type type = Type::MWAW_T_UNKNOWN;
        Kind kind = Kind::MWAW_K_UNKNOWN;
        Confidence conf = MWAWDocument::isFileFormatSupported(&stream, type, kind);
        CHECK(conf == Confidence::MWAW_C_NONE);
        CHECK(type == Type::MWAW_T_UNKNOWN);
        std::printf("PASS: non-Mac payload rejected (confidence=NONE)\n");
    }

    // 2. An empty stream must also be rejected gracefully
    //    (exercises the early-exit parsing path without crashing).
    {
        const unsigned char empty[] = {0};
        MemoryStream stream(empty, 0);
        Type type = Type::MWAW_T_UNKNOWN;
        Kind kind = Kind::MWAW_K_UNKNOWN;
        Confidence conf = MWAWDocument::isFileFormatSupported(&stream, type, kind);
        CHECK(conf == Confidence::MWAW_C_NONE);
        std::printf("PASS: empty stream rejected (confidence=NONE)\n");
    }

    // 3. A crafted CDF (OLE2 compound document) header — the container used
    //    by MacWrite/ClarisWorks files — must be classified with a valid
    //    enum result (no crash), whatever the confidence is.
    {
        unsigned char buf[512] = {0};
        buf[0] = 0xD0; buf[1] = 0xCF; buf[2] = 0x11; buf[3] = 0xE0;
        buf[4] = 0xA1; buf[5] = 0xB1; buf[6] = 0x1A; buf[7] = 0xE1;
        buf[24] = 0x00; buf[25] = 0x03; buf[26] = 0x00; buf[27] = 0x00; // v3
        buf[30] = 0x09; buf[31] = 0x00;                                  // sector size 512
        MemoryStream stream(buf, sizeof(buf));
        Type type = Type::MWAW_T_UNKNOWN;
        Kind kind = Kind::MWAW_K_UNKNOWN;
        Confidence conf = MWAWDocument::isFileFormatSupported(&stream, type, kind);
        std::printf("INFO: CDF header classified as confidence=%d type=%d\n",
                    static_cast<int>(conf), static_cast<int>(type));
        CHECK(conf >= Confidence::MWAW_C_NONE && conf <= Confidence::MWAW_C_EXCELLENT);
    }

    std::printf("PASS: libmwaw API test completed\n");
    return 0;
}
