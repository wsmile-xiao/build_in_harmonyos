/*
 * Consumer test for the libwpd package — real API calls against the
 * installed library, headless.
 *
 * Upstream ships no test suite and no sample documents, so this test covers
 * what can be verified without a WordPerfect file on disk:
 *
 *  - format detection (`libwpd::WPDocument::isFileFormatSupported`) both positively
 *    and negatively.  The positive cases use a hand-built minimal WPX header
 *    (0xFF "WPC" + document pointer + product/file/version bytes), which is
 *    exactly what the detector inspects, so a real parse of the header path
 *    happens rather than a stub return.
 *  - the parse entry point on non-WordPerfect input: it must report failure
 *    rather than succeed or crash.
 *  - `verifyPassword` on non-WordPerfect input.
 *
 * A full document round trip would need a genuine WordPerfect sample, which
 * upstream does not distribute; the conversion tools are instead driven end
 * to end by test_libwpd_cli.sh.
 *
 * Exits non-zero as soon as any check fails.
 */

#include <libwpd/libwpd.h>
#include <librevenge-stream/RVNGStream.h>

#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

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

/* Minimal read-only input stream.  libwpd walks this through the public
 * librevenge API, so implementing the interface here also proves that a
 * consumer can feed the library its own stream type. */
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

/* Header offsets the detector uses (src/lib/WPXFileStructure.h). */
static const size_t kMagicOffset = 1;
static const size_t kDocumentPointerOffset = 4;
static const size_t kProductTypeOffset = 8;
static const size_t kFileTypeOffset = 9;
static const size_t kMajorVersionOffset = 10;
static const size_t kMinorVersionOffset = 11;

static std::vector<unsigned char> makeWpxHeader(unsigned char fileType,
                                                unsigned char majorVersion)
{
    std::vector<unsigned char> header(32, 0);
    header[0] = 0xff;
    header[kMagicOffset + 0] = 'W';
    header[kMagicOffset + 1] = 'P';
    header[kMagicOffset + 2] = 'C';
    /* document pointer: a little-endian offset past the header */
    const size_t documentOffset = 32;
    header[kDocumentPointerOffset + 0] =
        static_cast<unsigned char>(documentOffset & 0xff);
    header[kDocumentPointerOffset + 1] =
        static_cast<unsigned char>((documentOffset >> 8) & 0xff);
    header[kProductTypeOffset] = 0x01; /* WordPerfect product */
    header[kFileTypeOffset] = fileType;
    header[kMajorVersionOffset] = majorVersion;
    header[kMinorVersionOffset] = 0x00;
    return header;
}

int main()
{
    /* ── negative cases ────────────────────────────────────────────── */
    check(libwpd::WPDocument::isFileFormatSupported(nullptr) == libwpd::WPD_CONFIDENCE_NONE,
          "isFileFormatSupported(nullptr) reports no confidence");

    {
        MemoryStream empty(nullptr, 0);
        check(libwpd::WPDocument::isFileFormatSupported(&empty) == libwpd::WPD_CONFIDENCE_NONE,
              "an empty stream reports no confidence");
    }

    {
        const std::string text = "This is plain text, not a WordPerfect file.";
        MemoryStream garbage(
            reinterpret_cast<const unsigned char *>(text.data()),
            text.size());
        check(libwpd::WPDocument::isFileFormatSupported(&garbage) ==
                  libwpd::WPD_CONFIDENCE_NONE,
              "a text file reports no confidence");
    }

    {
        /* Correct magic but a file type the detector does not handle. */
        std::vector<unsigned char> header = makeWpxHeader(0x00, 0x02);
        MemoryStream stream(header.data(), header.size());
        check(libwpd::WPDocument::isFileFormatSupported(&stream) ==
                  libwpd::WPD_CONFIDENCE_NONE,
              "WPC magic with an unknown file type reports no confidence");
    }

    {
        std::vector<unsigned char> header = makeWpxHeader(0x0a, 0x09);
        MemoryStream stream(header.data(), header.size());
        check(libwpd::WPDocument::isFileFormatSupported(&stream) ==
                  libwpd::WPD_CONFIDENCE_NONE,
              "a WordPerfect file type with an unhandled version reports no confidence");
    }

    /* ── positive cases: the detector must accept well-formed headers ─ */
    {
        std::vector<unsigned char> header = makeWpxHeader(0x0a, 0x02);
        MemoryStream stream(header.data(), header.size());
        check(libwpd::WPDocument::isFileFormatSupported(&stream) ==
                  libwpd::WPD_CONFIDENCE_EXCELLENT,
              "a WP6+ header (file type 0x0a, major version 0x02) is detected as excellent");
    }

    {
        std::vector<unsigned char> header = makeWpxHeader(0x0a, 0x00);
        MemoryStream stream(header.data(), header.size());
        check(libwpd::WPDocument::isFileFormatSupported(&stream) ==
                  libwpd::WPD_CONFIDENCE_EXCELLENT,
              "a WP5 header (major version 0x00) is detected as excellent");
    }

    /* ── entry points on non-WordPerfect input ─────────────────────── */
    {
        const std::string text = "not a wordperfect document";
        MemoryStream stream(
            reinterpret_cast<const unsigned char *>(text.data()),
            text.size());
        /* The header is rejected before any interface callback, so the null
         * interface is never dereferenced — this checks the parse entry
         * point's error contract, not a document round trip. */
        check(libwpd::WPDocument::parse(&stream, nullptr, nullptr) != libwpd::WPD_OK,
              "parse() on a non-WordPerfect stream reports failure");
    }

    {
        const std::string text = "not a wordperfect document";
        MemoryStream stream(
            reinterpret_cast<const unsigned char *>(text.data()),
            text.size());
        check(libwpd::WPDocument::verifyPassword(&stream, "secret") !=
                  libwpd::WPD_PASSWORD_MATCH_OK,
              "verifyPassword() on a non-WordPerfect stream never reports a match");
    }

    printf("1..%d\n", checks);
    printf("# %d checks, %d failures\n", checks, failures);
    return failures ? 1 : 0;
}
