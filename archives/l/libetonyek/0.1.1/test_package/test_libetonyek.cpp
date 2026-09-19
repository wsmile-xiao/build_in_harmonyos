/*
 * Consumer test for the libetonyek 0.1.1 package — real API calls against
 * the installed library, headless.
 *
 * libetonyek's positive path needs a genuine iWork document, and upstream
 * ships neither a sample nor an in-memory builder for one.  This test
 * therefore verifies what a consumer can check without such a file, and
 * the *positive* parsing coverage stays with upstream's own suite
 * (src/test/: the cppunit aggregate `test` over the nine KEY* suites),
 * which the recipe runs as a hard gate through `make check` in build().
 *
 * Covered here:
 *  - the detection entry point's contract on unusable input (, empty,
 *    plain text, a truncated ZIP header)
 *  - the document-type output parameter: it must stay TYPE_UNKNOWN when
 *    detection fails, i.e. the library must not classify garbage
 *  - parse()'s failure contract on unsupported input
 *  - the enum surface a consumer compiles against
 *
 * 0.1.1 API note (verified against src/lib/EtonyekDocument.cpp of this
 * tarball): unlike 0.1.13, this release does NOT guard isSupported()
 * against a null stream — the null pointer is wrapped in a
 * RVNGInputStreamPtr_t and dereferenced inside detect(), which crashes.
 * The null-input case is therefore deliberately absent from this test
 * (passing null is outside the supported contract of 0.1.1); the empty
 * stream below exercises the same "nothing to read" path safely.
 *
 * Exits non-zero as soon as any check fails.
 */

#include <libetonyek/EtonyekDocument.h>
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

/* Minimal read-only input stream, from the public librevenge interface (this
 * also shows a consumer can hand libetonyek its own stream type). */
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

int main()
{
    /* ── the enum surface a consumer compiles against ──────────────── */
    check(libetonyek::EtonyekDocument::CONFIDENCE_NONE == 0,
          "CONFIDENCE_NONE is the zero value (detection starts from 'not supported')");
    check(libetonyek::EtonyekDocument::RESULT_OK == 0,
          "RESULT_OK is the zero value of the result enum");
    check(libetonyek::EtonyekDocument::TYPE_UNKNOWN == 0,
          "TYPE_UNKNOWN is the zero value of the document-type enum");

    /* ── detection contract on unusable input ──────────────────────── */
    /* No isSupported(nullptr) case: 0.1.1 does not guard against a null
     * stream (see the API note above) — the empty-stream case below covers
     * the "nothing to read" path that 0.1.1 actually supports. */
    {
        MemoryStream empty(nullptr, 0);
        check(libetonyek::EtonyekDocument::isSupported(&empty) ==
                  libetonyek::EtonyekDocument::CONFIDENCE_NONE,
              "an empty stream is not supported");
    }

    {
        const std::string text = "This is plain text, not an iWork document.";
        MemoryStream stream(
            reinterpret_cast<const unsigned char *>(text.data()),
            text.size());
        libetonyek::EtonyekDocument::Type type =
            libetonyek::EtonyekDocument::TYPE_KEYNOTE; /* pre-set, must be reset */
        check(libetonyek::EtonyekDocument::isSupported(&stream, &type) ==
                  libetonyek::EtonyekDocument::CONFIDENCE_NONE,
              "plain text is not supported");
        check(type == libetonyek::EtonyekDocument::TYPE_UNKNOWN,
              "a rejected stream is not classified (type stays TYPE_UNKNOWN)");
    }

    {
        /* A ZIP local-file header ("PK\x03\x04") is what an iWork package
         * looks like at byte 0, but nothing follows it.  Detection must not
         * be fooled into reporting support. */
        const unsigned char zipStub[8] = {'P', 'K', 0x03, 0x04,
                                          0x00, 0x00, 0x00, 0x00};
        MemoryStream stream(zipStub, sizeof(zipStub));
        check(libetonyek::EtonyekDocument::isSupported(&stream) ==
                  libetonyek::EtonyekDocument::CONFIDENCE_NONE,
              "a truncated ZIP header is not accepted as an iWork package");
    }

    /* ── parse() error contract ────────────────────────────────────── */
    {
        const std::string text = "not an iwork document";
        MemoryStream stream(
            reinterpret_cast<const unsigned char *>(text.data()),
            text.size());
        /* Detection fails before any generator callback, so the null
         * interface is never dereferenced: this checks parse()'s error
         * contract, not a document round trip. */
        /* parse() is overloaded on the three librevenge generator
         * interfaces, so a bare nullptr is ambiguous — name the overload. */
        check(!libetonyek::EtonyekDocument::parse(
                  &stream,
                  static_cast<librevenge::RVNGTextInterface *>(nullptr)),
              "parse() on an unsupported stream reports failure");
    }

    printf("1..%d\n", checks);
    printf("# %d checks, %d failures\n", checks, failures);
    return failures ? 1 : 0;
}
