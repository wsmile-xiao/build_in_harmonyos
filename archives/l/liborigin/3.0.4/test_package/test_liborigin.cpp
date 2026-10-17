// Consumer test for the packaged liborigin 3.0.4.
//
// 链接安装后的 liborigin，读取上游测试夹具 tests/examples/data+graph-7.0.opj，
// 断言解析出的结构、列信息与数据值（与上游参考输出
// tests/examples/data+graph-7.0.opj.1.dat.orig 一致）。
#include <OriginFile.h>

#include <cmath>
#include <cstdio>
#include <string>

namespace {

int checks = 0;
int failures = 0;

void check(bool ok, const char *what)
{
    ++checks;
    if (ok) {
        std::printf("CHECK OK   %s\n", what);
    } else {
        std::printf("CHECK FAIL %s\n", what);
        ++failures;
    }
}

} // namespace

int main(int argc, char *argv[])
{
    if (argc < 2) {
        std::printf("usage: %s <file.opj>\n", argv[0]);
        return 2;
    }

    check(liboriginVersionString() == std::string("3.0.4"),
          "liboriginVersionString() == 3.0.4");
    check(liboriginVersionMajor() == 3 && liboriginVersionMinor() == 0 &&
              liboriginVersionBugfix() == 4,
          "liboriginVersionMajor/Minor/Bugfix == 3.0.4");
    check(liboriginVersion() == ((3u << 24) | (0u << 16) | (4u << 8)),
          "liboriginVersion() numeric encoding");

    OriginFile opj(argv[1]);
    check(opj.parse(), "OriginFile::parse() on real .opj");
    check(std::fabs(opj.version() - 7.0) < 1e-9, "project file version == 7.0");
    check(opj.spreadCount() == 1, "spreadCount() == 1");
    check(opj.datasetCount() == 2, "datasetCount() == 2");
    check(opj.graphCount() == 1, "graphCount() == 1");
    check(opj.matrixCount() == 0, "matrixCount() == 0");
    check(opj.excelCount() == 0, "excelCount() == 0");
    check(opj.functionCount() == 0, "functionCount() == 0");
    check(opj.noteCount() == 0, "noteCount() == 0");
    check(opj.project() != nullptr, "project() tree available");

    Origin::SpreadSheet sheet = opj.spread(0);
    check(sheet.name == "Data1", "spreadsheet name == Data1");
    check(sheet.columns.size() == 2, "spreadsheet column count == 2");
    check(sheet.maxRows == 30, "spreadsheet maxRows == 30");
    check(sheet.columns[0].name == "A" && sheet.columns[1].name == "B",
          "column names A/B");
    check(sheet.columns[0].type == Origin::SpreadColumn::X,
          "column A declared as X");
    check(sheet.columns[1].type == Origin::SpreadColumn::Y,
          "column B declared as Y");

    const double expected_x[4] = {1.0, 2.0, 3.0, 4.0};
    const double expected_y[4] = {2.0, 4.0, 5.0, 6.0};
    bool rows_ok = true;
    for (int i = 0; i < 4; ++i) {
        Origin::variant vx(sheet.columns[0].data[i]);
        Origin::variant vy(sheet.columns[1].data[i]);
        if (vx.type() != Origin::variant::V_DOUBLE ||
            vy.type() != Origin::variant::V_DOUBLE ||
            std::fabs(vx.as_double() - expected_x[i]) > 1e-12 ||
            std::fabs(vy.as_double() - expected_y[i]) > 1e-12) {
            rows_ok = false;
        }
    }
    check(rows_ok, "first four data rows match the upstream reference values");

    bool tail_missing = sheet.columns[0].data.size() >= 30 &&
                        sheet.columns[1].data.size() >= 30;
    for (size_t i = 4; i < sheet.columns[0].data.size() && tail_missing; ++i) {
        Origin::variant vx(sheet.columns[0].data[i]);
        Origin::variant vy(sheet.columns[1].data[i]);
        if (!(vx.type() == Origin::variant::V_DOUBLE && vx.as_double() == _ONAN) ||
            !(vy.type() == Origin::variant::V_DOUBLE && vy.as_double() == _ONAN)) {
            tail_missing = false;
        }
    }
    check(tail_missing, "remaining rows carry the missing-value marker (_ONAN)");

    Origin::SpreadColumn &dataset = opj.dataset(0);
    check(dataset.data.size() == sheet.columns[0].data.size(),
          "dataset(0) mirrors spreadsheet column A");

    if (failures != 0) {
        std::printf("TEST_PACKAGE_FAILED (%d/%d checks failed)\n", failures, checks);
        return 1;
    }
    std::printf("TEST_PACKAGE_OK (%d checks)\n", checks);
    return 0;
}
