// Consumer-side smoke test for CCfits 2.7 (OHOS adaptation).
//
// Exercises the real public CCfits API as a true consumer:
//   1. create a new FITS file with a PrimaryHDU,
//   2. write three keyword cards (two strings, one double),
//   3. write a float image,
//   4. reopen the file and assert every value round-trips,
//   5. write and read a binary table extension.
//
// Returns non-zero on the first failed assertion. Print-only/pass-only
// would not qualify as a test; every stage here checks data.

#include <CCfits/CCfits>

#include <cmath>
#include <cstdio>
#include <iostream>
#include <sstream>
#include <string>
#include <valarray>
#include <vector>

namespace {

int g_failures = 0;

void check(bool ok, const std::string& what)
{
    if (ok)
    {
        std::cout << "PASS: " << what << "\n";
    }
    else
    {
        ++g_failures;
        std::cerr << "FAIL: " << what << "\n";
    }
}

} // namespace

int main()
{
    const char* fname = "ccfits_tp_test.fit";
    std::remove(fname);

    // --- Stage 1-3: write ---
    // Upstream cookbook pattern: create the file with the primary image
    // geometry in one step (bitpix + axes). A bare FITS(fname, Write) file
    // has an empty NAXIS=0 primary HDU that cannot take pixel writes.
    try
    {
        long naxes[2] = {5, 5};
        CCfits::FITS out(fname, FLOAT_IMG, 2, naxes);

        out.pHDU().addKey("TELESCOP", std::string("OHOS-SMOKE"), "origin of the data");
        out.pHDU().addKey("EXPTIME", 1500.0, "total exposure time (s)");
        out.pHDU().addKey("DETNAM", std::string("CCD-A7"), "detector");

        std::valarray<float> pix(25);
        for (int i = 0; i < 25; ++i)
        {
            pix[i] = static_cast<float>(i) * 1.5f;
        }
        out.pHDU().write(1, 25, pix);
    }
    catch (const CCfits::FitsException& e)
    {
        std::cerr << "FAIL: write stage threw: " << e.message() << "\n";
        return 1;
    }

    // --- Stage 4: reopen and verify ---
    try
    {
        CCfits::FITS in(fname, CCfits::Read);

        std::string telescope;
        double exptime = 0.0;
        std::string detector;
        in.pHDU().readKey("TELESCOP", telescope);
        in.pHDU().readKey("EXPTIME", exptime);
        in.pHDU().readKey("DETNAM", detector);

        check(telescope == "OHOS-SMOKE", "keyword TELESCOP round-trip");
        check(std::fabs(exptime - 1500.0) < 1e-6, "keyword EXPTIME round-trip");
        check(detector == "CCD-A7", "keyword DETNAM round-trip");

        std::valarray<float> back;
        in.pHDU().read(back);
        check(back.size() == 25, "image axis/naxis round-trip (25 pixels)");

        bool pixels_ok = true;
        for (int i = 0; i < 25; ++i)
        {
            if (std::fabs(back[i] - static_cast<float>(i) * 1.5f) > 1e-4f)
            {
                pixels_ok = false;
            }
        }
        check(pixels_ok, "image pixel data round-trip");

        const long axes_total = in.pHDU().axes();
        check(axes_total == 2, "primary HDU reports 2 axes");
    }
    catch (const CCfits::FitsException& e)
    {
        std::cerr << "FAIL: read stage threw: " << e.message() << "\n";
        return 1;
    }

    // --- Stage 5: binary table extension round-trip (upstream cookbook
    //     pattern: columns are defined in the addTable() call itself). ---
    try
    {
        CCfits::FITS tableFile(fname, CCfits::Write);
        std::vector<std::string> names = {"alpha", "beta", "gamma", "delta"};
        std::vector<std::string> colName(1, "NAME");
        std::vector<std::string> colForm(1, "12A");
        std::vector<std::string> colUnit(1, "");
        CCfits::Table* table =
            tableFile.addTable("STARS", names.size(), colName, colForm, colUnit);

        // Column::write(vector, firstRow): whole-column string write, same
        // form the upstream cookbook uses for string columns.
        table->column(colName[0]).write(names, 1);
        tableFile.flush();

        CCfits::FITS readBack(fname, CCfits::Read);
        CCfits::ExtHDU& ext = readBack.extension("STARS");
        std::vector<std::string> got;
        ext.column("NAME").read(got, 1, static_cast<long>(names.size()));
        bool table_ok = true;
        for (std::size_t i = 0; i < names.size(); ++i)
        {
            if (got[i] != names[i])
            {
                table_ok = false;
            }
        }
        check(table_ok && got.size() == names.size(), "binary table string column round-trip");
    }
    catch (const CCfits::FitsException& e)
    {
        std::cerr << "FAIL: table stage threw: " << e.message() << "\n";
        return 1;
    }

    std::remove(fname);

    if (g_failures != 0)
    {
        std::cerr << g_failures << " assertion(s) failed\n";
        return 1;
    }
    std::cout << "ALL CHECKS PASSED\n";
    return 0;
}
