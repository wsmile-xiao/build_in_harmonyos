#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <string>
#include <vector>
#include <csv/reader.hpp>

int main(void) {
    // Create a temporary CSV file
    const char* tmpdir = getenv("TMPDIR");
    if (!tmpdir) tmpdir = getenv("HOME");
    if (!tmpdir) tmpdir = "/tmp";
    std::string tmpfile = std::string(tmpdir) + "/test_csv_parser_input.csv";

    {
        std::ofstream ofs(tmpfile);
        if (!ofs) {
            fprintf(stderr, "FAIL: cannot create temp file\n");
            return 1;
        }
        ofs << "name,age,city\n";
        ofs << "Alice,30,Beijing\n";
        ofs << "Bob,25,Shanghai\n";
    }

    // Parse CSV using csv-parser
    csv::Reader reader;
    reader.read(tmpfile);

    auto rows = reader.rows();
    auto cols = reader.cols();

    // Verify column count
    if (cols.size() != 3) {
        fprintf(stderr, "FAIL: expected 3 columns, got %zu\n", cols.size());
        return 1;
    }

    // Verify row count
    if (rows.size() != 2) {
        fprintf(stderr, "FAIL: expected 2 data rows, got %zu\n", rows.size());
        return 1;
    }

    // Verify row 1: Alice,30,Beijing
    if (rows[0]["name"] != "Alice" || rows[0]["age"] != "30" || rows[0]["city"] != "Beijing") {
        fprintf(stderr, "FAIL: row 1 data mismatch\n");
        return 1;
    }

    // Verify row 2: Bob,25,Shanghai
    if (rows[1]["name"] != "Bob" || rows[1]["age"] != "25" || rows[1]["city"] != "Shanghai") {
        fprintf(stderr, "FAIL: row 2 data mismatch\n");
        return 1;
    }

    // Cleanup
    remove(tmpfile.c_str());

    printf("test csv-parser 1.1: OK (parsed %zu rows, %zu cols)\n", rows.size(), cols.size());
    return 0;
}
