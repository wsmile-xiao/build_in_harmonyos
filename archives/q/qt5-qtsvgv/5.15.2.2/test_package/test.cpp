/* test_package/test.cpp — qt5-qtsvgv 5.15.2.2 consumer test
 *
 * Links against Qt5Svg, parses a minimal valid SVG document with
 * QSvgRenderer and asserts the parser accepts it (isValid() == true),
 * verifying the SVG parsing/render core works on HarmonyOS PC.
 */
#include <QCoreApplication>
#include <QSvgRenderer>
#include <cstdio>

int main(int argc, char *argv[]) {
    QCoreApplication app(argc, argv);

    // Minimal valid SVG: 16x16 canvas with a filled rect. A well-formed
    // document must be accepted by the parser; an invalid one fails the
    // assertion below (guards against stubbed/regressed parsing paths).
    const QByteArray svgData(
        "<svg xmlns='http://www.w3.org/2000/svg' width='16' height='16'>"
        "<rect width='16' height='16'/></svg>");
    QSvgRenderer renderer(svgData);
    if (!renderer.isValid()) {
        printf("FAILED: valid SVG not parsed by QSvgRenderer\n");
        return 1;
    }

    printf("[ok] Qt5Svg loaded through qt5-qtsvgv, valid SVG parsed (isValid=true)\n");
    printf("Smoke test PASSED.\n");
    return 0;
}
