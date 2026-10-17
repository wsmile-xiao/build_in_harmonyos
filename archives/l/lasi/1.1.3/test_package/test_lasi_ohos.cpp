#include <LASi.h>

#include <sys/utsname.h>

#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <iterator>
#include <string>

int main() {
    struct utsname platform {};
    if (uname(&platform) != 0 || std::string(platform.sysname) != "HarmonyOS") {
        std::cerr << "FAIL: test is not running on a HarmonyOS kernel\n";
        return 1;
    }
    const char* tmpdir = std::getenv("TMPDIR");
    if (tmpdir == nullptr || tmpdir[0] == '\0') {
        std::cerr << "FAIL: HarmonyOS writable TMPDIR is not configured\n";
        return 1;
    }
    std::ifstream font_probe("/system/fonts/HarmonyOS_Sans_SC.ttf",
                             std::ios::binary);
    if (!font_probe) {
        std::cerr << "FAIL: HarmonyOS system font is unavailable\n";
        return 1;
    }

    const std::string output_path =
        std::string(tmpdir) + "/lasi-harmonyos-unicode.eps";
    LASi::PostscriptDocument document;
    document.setFont("HarmonyOS Sans SC");
    document.setFontSize(20.0);
    const std::string text = "鸿蒙 HarmonyOS — العربية";
    double line_spacing = 0.0;
    double advance = 0.0;
    double y_min = 0.0;
    double y_max = 0.0;
    document.get_dimensions(text, &line_spacing, &advance, &y_min, &y_max);
    if (line_spacing <= 0.0 || advance <= 0.0 || y_max <= y_min) {
        std::cerr << "FAIL: HarmonyOS Unicode shaping returned invalid metrics\n";
        return 1;
    }
    document.osBody() << "36 72 moveto\n" << LASi::show(text)
                      << "showpage\n";
    {
        std::ofstream output(output_path, std::ios::binary);
        if (!output) {
            std::cerr << "FAIL: cannot create EPS in HarmonyOS TMPDIR\n";
            return 1;
        }
        document.write(output, 30.0, 40.0, 600.0, 100.0);
    }
    std::ifstream input(output_path, std::ios::binary);
    const std::string postscript((std::istreambuf_iterator<char>(input)),
                                 std::istreambuf_iterator<char>());
    std::remove(output_path.c_str());
    if (postscript.find("%!PS-Adobe") == std::string::npos ||
        postscript.find("%%BoundingBox:") == std::string::npos ||
        postscript.size() < 500U) {
        std::cerr << "FAIL: HarmonyOS Unicode EPS output is incomplete\n";
        return 1;
    }

    std::cout << "PASS: HarmonyOS system font, Unicode shaping, and TMPDIR\n";
    return 0;
}
