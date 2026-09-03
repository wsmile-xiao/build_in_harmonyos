#include <cmath>
#include <cstdio>
#include <iostream>
#include <string>
#include <vector>

#include <pdal/Dimension.hpp>
#include <pdal/Options.hpp>
#include <pdal/PointTable.hpp>
#include <pdal/PointView.hpp>
#include <pdal/Stage.hpp>
#include <pdal/pdal_config.hpp>
#include <pdal/io/BufferReader.hpp>
#include <pdal/io/LasReader.hpp>
#include <pdal/io/LasWriter.hpp>

namespace
{

// Points generated programmatically (upstream LasWriterTest::auto_offset uses
// the same BufferReader + registered X/Y/Z dims pattern).
struct Point
{
    double x;
    double y;
    double z;
};

const Point kPoints[] = {
    {125000.00, 0.0, -123.0},
    {74529.00, 1.0, 456.78},
    {1000000.02, 2.0, 945.23},
    {25.00, 3.0, 1.5},
    {534252.35, 5.0, 745.23},
};

int g_failures = 0;

void check(bool ok, const std::string& what)
{
    if (ok)
        std::cout << "[PASS] " << what << std::endl;
    else
    {
        std::cout << "[FAIL] " << what << std::endl;
        ++g_failures;
    }
}

} // namespace

int main()
{
    std::cout << "PDAL version: " << pdal::Config::fullVersionString() << std::endl;

    const std::string filename = "pdal_roundtrip_test.las";

    // ------------------------------------------------------------------
    // 1. Generate a point cloud in memory and write it as LAS.
    // ------------------------------------------------------------------
    {
        using namespace pdal;

        PointTable table;
        table.layout()->registerDims(
            {Dimension::Id::X, Dimension::Id::Y, Dimension::Id::Z});

        BufferReader bufferReader;

        PointViewPtr view(new PointView(table));
        for (std::size_t i = 0; i < sizeof(kPoints) / sizeof(kPoints[0]); ++i)
        {
            view->setField(Dimension::Id::X, i, kPoints[i].x);
            view->setField(Dimension::Id::Y, i, kPoints[i].y);
            view->setField(Dimension::Id::Z, i, kPoints[i].z);
        }
        bufferReader.addView(view);

        Options writerOps;
        writerOps.add("filename", filename);
        // Match the upstream LasWriterTest::auto_offset pattern: large
        // coordinates need an auto offset/scale or the scaled int32 storage
        // in LAS overflows.
        writerOps.add("offset_x", "auto");
        writerOps.add("scale_x", "auto");
        writerOps.add("offset_y", "auto");
        writerOps.add("scale_y", "auto");
        writerOps.add("offset_z", "auto");
        writerOps.add("scale_z", "auto");

        LasWriter writer;
        writer.setOptions(writerOps);
        writer.setInput(bufferReader);

        writer.prepare(table);
        writer.execute(table);
        std::cout << "Wrote " << sizeof(kPoints) / sizeof(kPoints[0])
                  << " points to " << filename << std::endl;
    }

    // ------------------------------------------------------------------
    // 2. Read the LAS file back and verify the roundtrip.
    // ------------------------------------------------------------------
    {
        using namespace pdal;

        Options readerOps;
        readerOps.add("filename", filename);

        PointTable readTable;

        LasReader reader;
        reader.setOptions(readerOps);
        reader.prepare(readTable);
        PointViewSet viewSet = reader.execute(readTable);

        std::size_t total = 0;
        double maxError = 0.0;
        for (const auto& view : viewSet)
        {
            for (PointId idx = 0; idx < view->size(); ++idx)
            {
                if (total < sizeof(kPoints) / sizeof(kPoints[0]))
                {
                    double ex = view->getFieldAs<double>(Dimension::Id::X, idx);
                    double ey = view->getFieldAs<double>(Dimension::Id::Y, idx);
                    double ez = view->getFieldAs<double>(Dimension::Id::Z, idx);
                    // Global point index across all views in the set.
                    const std::size_t ref = total;
                    if (ref < 3)
                        std::cout << "  read [" << ref << "] = (" << ex << ", "
                                  << ey << ", " << ez << ")" << std::endl;
                    double err = std::max(std::max(std::fabs(ex - kPoints[ref].x),
                                                    std::fabs(ey - kPoints[ref].y)),
                                           std::fabs(ez - kPoints[ref].z));
                    maxError = std::max(maxError, err);
                }
                ++total;
            }
        }

        check(total == sizeof(kPoints) / sizeof(kPoints[0]),
              "point count roundtrip (" + std::to_string(total) + " read back)");
        // LAS stores X/Y/Z as scaled integers; allow the default scale error.
        check(maxError < 0.01,
              "coordinate roundtrip max error " + std::to_string(maxError));
    }

    // ------------------------------------------------------------------
    // 3. Sanity: version info API works.
    // ------------------------------------------------------------------
    check(!pdal::Config::fullVersionString().empty(),
          "pdal::Config::fullVersionString() non-empty");

    std::remove(filename.c_str());

    if (g_failures == 0)
    {
        std::cout << "ALL CHECKS PASSED" << std::endl;
        return 0;
    }
    std::cout << g_failures << " CHECK(S) FAILED" << std::endl;
    return 1;
}
