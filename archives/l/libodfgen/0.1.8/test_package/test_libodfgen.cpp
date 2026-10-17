/*
 * Consumer test for the libodfgen package — real API calls against the
 * installed library, headless.
 *
 * libodfgen is an exporter: a consumer drives an RVNGTextInterface-shaped
 * generator and the library emits OpenDocument XML through an
 * OdfDocumentHandler.  This test implements that handler (it is public API)
 * and asserts on what the library actually produces, so it verifies the
 * document generation path end to end: root element, paragraph and span
 * structure, text content, style plumbing and a well-formed closing tag.
 *
 * Upstream's own suite (test/, 11 programs, run as `make launch_all` during
 * the build) exercises the same generators more broadly; this test is the
 * consumer-side check that the installed package is usable from outside.
 *
 * Exits non-zero as soon as any check fails.
 */

#include <libodfgen/libodfgen.hxx>

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

/* Minimal OdfDocumentHandler: records everything the generator emits.
 * Note the libodfgen headers declare no namespace — the generators, the
 * handler interface and the OdfStreamType enum all live in the global
 * namespace (verified against inc/libodfgen/*.hxx). */
class CapturingHandler : public OdfDocumentHandler
{
public:
    void startDocument() override { m_data += "<?xml"; }
    void endDocument() override {}
    void startElement(const char *name,
                      const librevenge::RVNGPropertyList &props) override
    {
        m_data += "<";
        m_data += name;
        librevenge::RVNGPropertyList::Iter i(props);
        for (i.rewind(); i.next();) {
            m_data += " ";
            m_data += i.key();
            m_data += "=\"";
            m_data += i()->getStr().cstr();
            m_data += "\"";
        }
        m_data += ">";
    }
    void endElement(const char *name) override
    {
        m_data += "</";
        m_data += name;
        m_data += ">";
    }
    void characters(const librevenge::RVNGString &text) override
    {
        m_data += text.cstr();
    }

    const std::string &data() const { return m_data; }

private:
    std::string m_data;
};

int main()
{
    CapturingHandler handler;
    OdtGenerator generator;
    generator.addDocumentHandler(&handler, ODF_FLAT_XML);

    generator.startDocument(librevenge::RVNGPropertyList());

    librevenge::RVNGPropertyList paragraph;
    generator.openParagraph(paragraph);

    librevenge::RVNGPropertyList span;
    span.insert("style:font-name", "Courier");
    span.insert("fo:font-size", 13, librevenge::RVNG_POINT);
    generator.openSpan(span);
    generator.insertText("hello odfgen");
    generator.closeSpan();

    generator.closeParagraph();

    librevenge::RVNGPropertyList list;
    list.insert("text:min-label-width", 0.2, librevenge::RVNG_INCH);
    list.insert("style:num-format", "1");
    generator.openOrderedListLevel(list);
    generator.openListElement(librevenge::RVNGPropertyList());
    generator.openSpan(librevenge::RVNGPropertyList());
    generator.insertText("first item");
    generator.closeSpan();
    generator.closeListElement();
    generator.closeOrderedListLevel();

    generator.endDocument();

    const std::string &out = handler.data();

    check(!out.empty(), "the generator emitted a document");
    check(out.find("office:document") != std::string::npos,
          "the emitted document has the office:document root element");
    check(out.find("</office:document>") != std::string::npos,
          "the emitted document is closed (endDocument emitted the closing tag)");
    check(out.find("text:p") != std::string::npos,
          "the paragraph was emitted as a text:p element");
    check(out.find("hello odfgen") != std::string::npos,
          "the text written through insertText() appears in the output");
    check(out.find("Courier") != std::string::npos,
          "the span's font style was carried into the output");
    check(out.find("text:list") != std::string::npos,
          "the ordered list structure was emitted");
    check(out.find("first item") != std::string::npos,
          "the list item text appears in the output");

    /* The ODS/ODG/ODP backends are exercised by upstream's own suite
     * (test/testTextbox1.cxx drives all four generators), which the recipe
     * runs as a hard gate in build().  Repeating a hand-written ODS call
     * sequence here would assert my guess at the required call order rather
     * than the library's behaviour, so the consumer test stays on the ODT
     * path it can verify end to end. */

    printf("1..%d\n", checks);
    printf("# %d checks, %d failures\n", checks, failures);
    return failures ? 1 : 0;
}
