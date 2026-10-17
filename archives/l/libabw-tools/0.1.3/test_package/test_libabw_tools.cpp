/*
 * Consumer test for the libabw-tools package — real API calls against the
 * libabw library shipped with the tools, headless.
 *
 * Upstream ships no test suite and no sample documents, so this test builds
 * its own inputs.  libabw's format detection inflates the stream
 * (`inflateInit2(&strm, 16 + MAX_WBITS)`, i.e. gzip) and then requires the
 * first XML element to be <abiword> or <awml>.  The positive fixtures below
 * are therefore gzip streams generated ahead of time, embedded as byte
 * arrays, so the test needs nothing from the filesystem and stays
 * deterministic.
 *
 * Exits non-zero as soon as any check fails.
 */

#include <libabw/libabw.h>
#include <librevenge-stream/RVNGStream.h>

#include <cstdio>
#include <cstring>
#include <string>

static int checks = 0;
static int failures = 0;

static void check(bool condition, const char *what)
{
    checks++;
    if (condition)
        printf("ok %d - %s\n", checks, what);
    else {
        failures++;
        printf("not ok %d - %s\n", checks, what);
    }
}

/* Minimal read-only input stream: libabw consumes the public librevenge
 * interface, so implementing it here also shows a consumer can hand the
 * library its own stream type. */
class MemoryStream : public librevenge::RVNGInputStream
{
public:
    MemoryStream(const unsigned char *data, size_t size)
        : m_data(data), m_size(size), m_pos(0) {}

    bool isStructured() override { return false; }
    unsigned subStreamCount() override { return 0; }
    const char *subStreamName(unsigned) override { return nullptr; }
    bool existsSubStream(const char *) override { return false; }
    librevenge::RVNGInputStream *getSubStreamByName(const char *) override
    {
        return nullptr;
    }
    librevenge::RVNGInputStream *getSubStreamById(unsigned) override
    {
        return nullptr;
    }

    const unsigned char *read(unsigned long numBytes,
                              unsigned long &numBytesRead) override
    {
        if (m_pos >= m_size) {
            numBytesRead = 0;
            return nullptr;
        }
        unsigned long available = static_cast<unsigned long>(m_size - m_pos);
        numBytesRead = numBytes < available ? numBytes : available;
        const unsigned char *result = m_data + m_pos;
        m_pos += numBytesRead;
        return result;
    }

    int seek(long offset, librevenge::RVNG_SEEK_TYPE seekType) override
    {
        long target = offset;
        if (seekType == librevenge::RVNG_SEEK_CUR)
            target = static_cast<long>(m_pos) + offset;
        else if (seekType == librevenge::RVNG_SEEK_END)
            target = static_cast<long>(m_size) + offset;
        if (target < 0 || static_cast<size_t>(target) > m_size)
            return 1;
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

/* gzip("<?xml version="1.0" encoding="UTF-8"?><abiword></abiword>") */
static const unsigned char kAbiwordDocument[] = {
    0x1f, 0x8b, 0x08, 0x00, 0x00, 0x00, 0x00, 0x00, 0x02, 0xff, 0xb3, 0xb1,
    0xaf, 0xc8, 0xcd, 0x51, 0x28, 0x4b, 0x2d, 0x2a, 0xce, 0xcc, 0xcf, 0xb3,
    0x55, 0x32, 0xd4, 0x33, 0x50, 0x52, 0x48, 0xcd, 0x4b, 0xce, 0x4f, 0xc9,
    0xcc, 0x4b, 0xb7, 0x55, 0x0a, 0x0d, 0x71, 0xd3, 0xb5, 0x50, 0xb2, 0xb7,
    0xb3, 0x49, 0x4c, 0xca, 0x2c, 0xcf, 0x2f, 0x4a, 0xb1, 0xb3, 0xd1, 0x87,
    0xb1, 0x00, 0x4e, 0x73, 0x10, 0x9b, 0x39, 0x00, 0x00, 0x00,
};

/* gzip("<?xml version="1.0" encoding="UTF-8"?><awml></awml>") */
static const unsigned char kAwmlDocument[] = {
    0x1f, 0x8b, 0x08, 0x00, 0x00, 0x00, 0x00, 0x00, 0x02, 0xff, 0xb3, 0xb1,
    0xaf, 0xc8, 0xcd, 0x51, 0x28, 0x4b, 0x2d, 0x2a, 0xce, 0xcc, 0xcf, 0xb3,
    0x55, 0x32, 0xd4, 0x33, 0x50, 0x52, 0x48, 0xcd, 0x4b, 0xce, 0x4f, 0xc9,
    0xcc, 0x4b, 0xb7, 0x55, 0x0a, 0x0d, 0x71, 0xd3, 0xb5, 0x50, 0xb2, 0xb7,
    0xb3, 0x49, 0x2c, 0xcf, 0xcd, 0xb1, 0xb3, 0xd1, 0x07, 0x53, 0x00, 0xef,
    0xf3, 0xf7, 0x78, 0x33, 0x00, 0x00, 0x00,
};

/* gzip("<?xml version="1.0" encoding="UTF-8"?><notabiword></notabiword>") */
static const unsigned char kOtherDocument[] = {
    0x1f, 0x8b, 0x08, 0x00, 0x00, 0x00, 0x00, 0x00, 0x02, 0xff, 0xb3, 0xb1,
    0xaf, 0xc8, 0xcd, 0x51, 0x28, 0x4b, 0x2d, 0x2a, 0xce, 0xcc, 0xcf, 0xb3,
    0x55, 0x32, 0xd4, 0x33, 0x50, 0x52, 0x48, 0xcd, 0x4b, 0xce, 0x4f, 0xc9,
    0xcc, 0x4b, 0xb7, 0x55, 0x0a, 0x0d, 0x71, 0xd3, 0xb5, 0x50, 0xb2, 0xb7,
    0xb3, 0xc9, 0xcb, 0x2f, 0x49, 0x4c, 0xca, 0x2c, 0xcf, 0x2f, 0x4a, 0xb1,
    0xb3, 0xd1, 0x47, 0xe2, 0x00, 0x00, 0x33, 0xc0, 0x09, 0xde, 0x3f, 0x00,
    0x00, 0x00,
};

static bool detect(const unsigned char *data, size_t size)
{
    MemoryStream stream(data, size);
    return libabw::AbiDocument::isFileFormatSupported(&stream);
}

int main()
{
    /* ── negative cases ────────────────────────────────────────────── */
    check(!libabw::AbiDocument::isFileFormatSupported(nullptr),
          "isFileFormatSupported(nullptr) reports false");

    {
        MemoryStream empty(nullptr, 0);
        check(!libabw::AbiDocument::isFileFormatSupported(&empty),
              "an empty stream is not supported");
    }

    {
        const std::string text = "This is plain text, not an AbiWord file.";
        check(!detect(reinterpret_cast<const unsigned char *>(text.data()),
                      text.size()),
              "uncompressed text is not supported");
    }

    {
        /* Uncompressed XML with the right root is accepted too: in
         * libabw 0.1.3 the ABWZlibStream constructor falls back to the
         * raw input stream when the gzip inflate fails (m_input is set to
         * the original input), so both shapes are valid AbiWord inputs.
         * 0.1.4's ABWZlibStream.cpp carries the same constructor. */
        const std::string xml =
            "<?xml version=\"1.0\"?><abiword></abiword>";
        check(detect(reinterpret_cast<const unsigned char *>(xml.data()),
                     xml.size()),
              "uncompressed <abiword> XML is accepted (the stream falls back to raw data)");
    }

    {
        const unsigned char garbage[16] = {0x00, 0x01, 0x02, 0x03, 0x04, 0x05,
                                           0x06, 0x07, 0x08, 0x09, 0x0a, 0x0b,
                                           0x0c, 0x0d, 0x0e, 0x0f};
        check(!detect(garbage, sizeof(garbage)),
              "arbitrary binary data is not supported");
    }

    check(!detect(kOtherDocument, sizeof(kOtherDocument)),
          "a gzip XML document with a foreign root element is not supported");

    /* ── positive cases ───────────────────────────────────────────── */
    check(detect(kAbiwordDocument, sizeof(kAbiwordDocument)),
          "a gzip XML document with an <abiword> root is supported");
    check(detect(kAwmlDocument, sizeof(kAwmlDocument)),
          "a gzip XML document with an <awml> root is supported");

    /* ── parse entry point on unsupported input ───────────────────── */
    {
        const std::string text = "not an abiword document";
        MemoryStream stream(
            reinterpret_cast<const unsigned char *>(text.data()),
            text.size());
        /* Detection fails before any interface callback, so the null
         * interface is never dereferenced: this checks parse()'s error
         * contract, not a document round trip. */
        check(!libabw::AbiDocument::parse(&stream, nullptr),
              "parse() on an unsupported stream reports failure");
    }

    printf("1..%d\n", checks);
    printf("# %d checks, %d failures\n", checks, failures);
    return failures ? 1 : 0;
}
