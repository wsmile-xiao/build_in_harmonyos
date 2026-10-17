// Consumer test for the xlslib library: creates a workbook, adds a sheet
// with label/number/blank cells, dumps a real .xls file and verifies the
// output is a non-empty file.  Each check maps to one assertion.
#include <xlslib.h>

#include <cstdio>
#include <cstring>

int main() {
    using namespace xlslib_core;

    int rc = 0;
    workbook wb;
    worksheet* sh = wb.sheet("sheet");
    if (!sh) {
        std::fprintf(stderr, "xlslib assertion 1: workbook.sheet() returned NULL\n");
        return 1;
    }
    sh->label(1, 1, "hello");
    sh->number(2, 1, 3.14);
    sh->blank(3, 1);

    int err = wb.Dump("test.xls");
    if (err != NO_ERRORS) {
        std::fprintf(stderr, "xlslib assertion 2: wb.Dump failed with code %d\n", err);
        return 2;
    }

    FILE* f = std::fopen("test.xls", "rb");
    if (!f) {
        std::fprintf(stderr, "xlslib assertion 3: test.xls was not created\n");
        return 3;
    }
    std::fseek(f, 0, SEEK_END);
    long sz = std::ftell(f);
    std::fclose(f);
    if (sz <= 0) {
        std::fprintf(stderr, "xlslib assertion 4: test.xls is empty\n");
        return 4;
    }

    std::printf("xlslib API assertions: 4 passed\n");
    std::fflush(stdout);
    (void)rc;
    return 0;
}
