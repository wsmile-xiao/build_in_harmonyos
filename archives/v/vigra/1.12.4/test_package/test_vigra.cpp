#include <vigra/stdimage.hxx>
#include <vigra/copyimage.hxx>
#include <vigra/imageinfo.hxx>
#include <iostream>

int main() {
    vigra::BImage img(16, 16);
    img.init(128);
    if (img(8, 8) != 128) {
        std::cerr << "BImage init failed" << std::endl;
        return 1;
    }
    vigra::BImage img2(16, 16);
    vigra::copyImage(vigra::srcImageRange(img), vigra::destImage(img2));
    if (img2(8, 8) != 128) {
        std::cerr << "copyImage failed" << std::endl;
        return 2;
    }
    // vigra::ImageImportInfo / ImageExportInfo are the valid symbols in
    // vigra/imageinfo.hxx (no plain ImageInfo). Use ExportInfo which does
    // not require the file to exist, only stores metadata.
    vigra::ImageExportInfo info("test.png");
    (void)info.getFileName();
    vigra::TinyVector<int, 3> v(1, 2, 3);
    vigra::TinyVector<int, 3> w(4, 5, 6);
    auto sum = v + w;
    if (sum[0] != 5 || sum[1] != 7 || sum[2] != 9) {
        std::cerr << "TinyVector arithmetic failed" << std::endl;
        return 3;
    }
    std::cout << "vigra test passed: BImage copyImage TinyVector ImageExportInfo" << std::endl;
    return 0;
}
