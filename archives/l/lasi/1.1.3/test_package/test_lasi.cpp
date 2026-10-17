#include <LASi.h>

#include <iostream>
#include <sstream>
#include <string>

int main() {
    LASi::PostscriptDocument document;
    document.setFont("serif");
    document.setFontSize(18.0);

    double line_spacing = 0.0;
    double advance = 0.0;
    double y_min = 0.0;
    double y_max = 0.0;
    const std::string text = "LASi consumer test";
    document.get_dimensions(text, &line_spacing, &advance, &y_min, &y_max);
    if (line_spacing <= 0.0 || advance <= 0.0 || y_max <= y_min) {
        std::cerr << "FAIL: invalid Pango text metrics\n";
        return 1;
    }

    document.osBody() << "72 720 moveto\n" << LASi::show(text);
    document.osBody() << "showpage\n";
    std::ostringstream output;
    document.write(output, 70.0, 700.0, 500.0, 750.0);
    const std::string postscript = output.str();
    if (postscript.find("%!PS-Adobe") == std::string::npos ||
        postscript.find("%%BoundingBox:") == std::string::npos ||
        postscript.find("showpage") == std::string::npos ||
        postscript.size() < 500U) {
        std::cerr << "FAIL: LASi generated an invalid EPS document\n";
        return 1;
    }

    std::cout << "PASS: LASi metrics and EPS generation API\n";
    return 0;
}
