/*
 * Consumer test for the libwps package — real API calls against the
 * installed library, headless.
 *
 * Upstream ships no test suite and no sample documents, so this test covers
 * what can be verified without a Works file on disk:
 *
 *  - format detection (`libwps::WPSDocument::isFileFormatSupported`) both
 *    positively and negatively.  The positive cases use a hand-built minimal
 *    Microsoft Works v2 header (first byte < 6, second byte 0xFE, file at
 *    least 0x100 bytes — exactly what WPSHeader::constructHeader and
 *    WPS4Parser::checkHeader inspect), so a real parse of the header path
 *    happens rather than a stub return.  The kind/creator out-parameters
 *    are asserted as well.
 *  - the parse entry point on non-Works input: it must report failure
 *    rather than succeed or crash.
 *
 * A full document round trip would need a genuine Microsoft Works sample,
 * which upstream does not distribute; the conversion tools are instead
 * driven end to end by test_libwps_cli.sh.
 *
 * Exits non-zero as soon as any check fails.
 */

#include <libwps/libwps.h>

#include <cstdio>
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

/* Minimal read-only input stream.  libwps walks this through the public
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

/* A Microsoft Works v2 header as recognized by WPSHeader::constructHeader:
 * byte 0 in [0..5] and byte 1 == 0xFE ("Microsoft Works v2 format
 * detected"), which yields kind=WPS_TEXT, creator=WPS_MSWORKS,
 * majorVersion=2.  WPS4Parser::checkHeader then requires the file to be at
 * least 0x100 bytes long and re-reads the first two bytes with the same
 * conditions.  `size` pads the buffer so the length check passes. */
static std::vector<unsigned char> makeWorksV2(unsigned char firstByte,
                                              size_t size)
{
    if (size < 2)
        size = 2;
    std::vector<unsigned char> header(size, 0);
    header[0] = firstByte;
    header[1] = 0xFE;
    return header;
}

int main()
{
    /* ── format detection: negative cases ──────────────────────────── */
    {
        libwps::WPSKind kind;
        libwps::WPSCreator creator;
        bool needEncoding = false;
        check(libwps::WPSDocument::isFileFormatSupported(
                  nullptr, kind, creator, needEncoding) ==
                  libwps::WPS_CONFIDENCE_NONE,
              "isFileFormatSupported(nullptr) reports no confidence");
    }

    {
        std::vector<unsigned char> empty;
        MemoryStream stream(empty.data(), empty.size());
        libwps::WPSKind kind;
        libwps::WPSCreator creator;
        bool needEncoding = false;
        check(libwps::WPSDocument::isFileFormatSupported(
                  &stream, kind, creator, needEncoding) ==
                  libwps::WPS_CONFIDENCE_NONE,
              "an empty stream reports no confidence");
    }

    {
        const std::string text = "not a microsoft works document";
        MemoryStream stream(
            reinterpret_cast<const unsigned char *>(text.data()),
            text.size());
        libwps::WPSKind kind;
        libwps::WPSCreator creator;
        bool needEncoding = false;
        check(libwps::WPSDocument::isFileFormatSupported(
                  &stream, kind, creator, needEncoding) ==
                  libwps::WPS_CONFIDENCE_NONE,
              "a text file reports no confidence");
    }

    {
        std::vector<unsigned char> data = makeWorksV2(0x02, 0x40);
        data[1] = 0xBB; /* break the Works magic */
        MemoryStream stream(data.data(), data.size());
        libwps::WPSKind kind;
        libwps::WPSCreator creator;
        bool needEncoding = false;
        check(libwps::WPSDocument::isFileFormatSupported(
                  &stream, kind, creator, needEncoding) ==
                  libwps::WPS_CONFIDENCE_NONE,
              "a broken Works magic reports no confidence");
    }

    /* ── format detection: positive cases (Works v2) ───────────────── */
    {
        std::vector<unsigned char> data = makeWorksV2(0x02, 0x200);
        MemoryStream stream(data.data(), data.size());
        libwps::WPSKind kind = libwps::WPS_DATABASE;
        libwps::WPSCreator creator = libwps::WPS_LOTUS;
        bool needEncoding = true;
        check(libwps::WPSDocument::isFileFormatSupported(
                  &stream, kind, creator, needEncoding) ==
                  libwps::WPS_CONFIDENCE_EXCELLENT,
              "a Works v2 header (first byte 0x02, 0x200 bytes) is detected "
              "as excellent");
        check(kind == libwps::WPS_TEXT && creator == libwps::WPS_MSWORKS,
              "the Works v2 header reports kind=WPS_TEXT and "
              "creator=WPS_MSWORKS");
    }

    {
        /* first byte 0 is still < 6: the same Works v2 path with the
         * boundary value (majorVersion stays 2 because firstByte < 4). */
        std::vector<unsigned char> data = makeWorksV2(0x00, 0x100);
        MemoryStream stream(data.data(), data.size());
        libwps::WPSKind kind;
        libwps::WPSCreator creator;
        bool needEncoding = false;
        check(libwps::WPSDocument::isFileFormatSupported(
                  &stream, kind, creator, needEncoding) ==
                  libwps::WPS_CONFIDENCE_EXCELLENT,
              "a Works v2 header with the boundary first byte 0x00 is "
              "detected as excellent");
    }

    {
        /* Same magic but only 0x40 bytes: WPS4Parser::checkHeader requires
         * checkFilePosition(0x100), so this must be rejected — the length
         * gate is part of the detector's contract. */
        std::vector<unsigned char> data = makeWorksV2(0x02, 0x40);
        MemoryStream stream(data.data(), data.size());
        libwps::WPSKind kind;
        libwps::WPSCreator creator;
        bool needEncoding = false;
        check(libwps::WPSDocument::isFileFormatSupported(
                  &stream, kind, creator, needEncoding) ==
                  libwps::WPS_CONFIDENCE_NONE,
              "a Works v2 header that is too short (<0x100 bytes) reports "
              "no confidence");
    }

    /* ── entry points on non-Works input ───────────────────────────── */
    {
        const std::string text = "not a microsoft works document";
        MemoryStream stream(
            reinterpret_cast<const unsigned char *>(text.data()),
            text.size());
        /* The header is rejected before any interface callback, so the null
         * interface is never dereferenced — this checks the parse entry
         * point's error contract, not a document round trip. */
        check(libwps::WPSDocument::parse(&stream,
                                         static_cast<librevenge::RVNGTextInterface *>(nullptr)) !=
                  libwps::WPS_OK,
              "parse() on a non-Works stream reports failure");
    }

    {
        /* A null document interface is rejected at the entry point. */
        std::vector<unsigned char> data = makeWorksV2(0x02, 0x200);
        MemoryStream stream(data.data(), data.size());
        check(libwps::WPSDocument::parse(&stream,
                                         static_cast<librevenge::RVNGTextInterface *>(nullptr)) ==
                  libwps::WPS_UNKNOWN_ERROR,
              "parse() with a null text interface returns "
              "WPS_UNKNOWN_ERROR");
    }

    printf("1..%d\n", checks);
    printf("# %d checks, %d failures\n", checks, failures);
    return failures ? 1 : 0;
}
