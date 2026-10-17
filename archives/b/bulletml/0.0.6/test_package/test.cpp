// test_package consumer test for bulletml 0.0.6 (libBulletML)
//
// Real consumer verification (R34): parses a BulletML XML document with the
// library's tinyxml-backed parser and drives a BulletMLRunner subclass,
// asserting that the parsed action actually fires bullets through the
// createSimpleBullet / createBullet callbacks.
#include <cstdlib>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <string>
#include <vector>

#include "bulletml/bulletmlparser.h"
#include "bulletml/bulletmlparser-tinyxml.h"
#include "bulletml/bulletmlrunner.h"

namespace {

const char* kSampleXml =
    "<?xml version=\"1.0\"?>\n"
    "<bulletml type=\"vertical\">\n"
    "  <action label=\"top\">\n"
    "    <fire>\n"
    "      <bullet>\n"
    "        <direction>90</direction>\n"
    "        <speed>1.5</speed>\n"
    "      </bullet>\n"
    "    </fire>\n"
    "    <fire>\n"
    "      <bullet>\n"
    "        <direction>180</direction>\n"
    "        <speed>2.0</speed>\n"
    "      </bullet>\n"
    "    </fire>\n"
    "  </action>\n"
    "</bulletml>\n";

// Minimal BulletMLRunner subclass: records every bullet the library asks us
// to create so the test can assert the parser+runner pipeline really works.
class CountingRunner : public BulletMLRunner {
public:
    explicit CountingRunner(BulletMLParser* parser) : BulletMLRunner(parser) {}

    virtual double getBulletDirection() { return 0.0; }
    virtual double getAimDirection() { return 0.0; }
    virtual double getBulletSpeed() { return 1.0; }
    virtual double getDefaultSpeed() { return 1.0; }
    virtual double getRank() { return 0.5; }

    virtual void createSimpleBullet(double /*direction*/, double /*speed*/) {
        simpleBullets_++;
    }
    virtual void createBullet(BulletMLState* /*state*/,
                              double /*direction*/, double /*speed*/) {
        complexBullets_++;
    }
    virtual int getTurn() { return 0; }
    virtual void doVanish() {}

    int simpleBullets() const { return simpleBullets_; }
    int complexBullets() const { return complexBullets_; }

private:
    int simpleBullets_ = 0;
    int complexBullets_ = 0;
};

}  // namespace

int main() {
    // Write the sample BulletML document to a temp file (R1: /tmp may be
    // read-only, so honour $TMPDIR and fall back to the working directory).
    std::string tmpDir = std::getenv("TMPDIR") ? std::getenv("TMPDIR") : ".";
    std::string xmlPath = tmpDir + "/bulletml-test-package.xml";
    {
        std::ofstream out(xmlPath.c_str());
        if (!out) {
            std::fprintf(stderr, "FAIL: cannot write %s\n", xmlPath.c_str());
            return 1;
        }
        out << kSampleXml;
    }

    BulletMLParserTinyXML parser(xmlPath.c_str());
    parser.parse();

    if (parser.getTopActions().empty()) {
        std::fprintf(stderr, "FAIL: no top actions parsed from %s\n",
                     xmlPath.c_str());
        return 1;
    }

    CountingRunner runner(&parser);
    runner.run();

    if (runner.simpleBullets() + runner.complexBullets() == 0) {
        std::fprintf(stderr,
                     "FAIL: runner produced no bullets (simple=%d complex=%d)\n",
                     runner.simpleBullets(), runner.complexBullets());
        return 1;
    }

    std::printf("PASS: parsed %zu top action(s); fired simple=%d complex=%d\n",
                parser.getTopActions().size(), runner.simpleBullets(),
                runner.complexBullets());
    return 0;
}
