// test_package consumer validation for ctrack (header-only library).
// Uses ONLY the public header ctrack.hpp and the public API:
//   - CTRACK / CTRACK_NAME macros
//   - ctrack::result_get_summary_table()
//   - ctrack::result_as_string()
// Verifies observable results: function names recorded, call counts match,
// and the summary table contains the tracked business functions.
#include <iostream>
#include <string>
#include "ctrack.hpp"

// Business-like functions that an upper-layer component would profile.
static double compute_series(int n) {
    CTRACK_NAME("compute_series");
    double acc = 0.0;
    for (int i = 1; i <= n; ++i) {
        acc += 1.0 / static_cast<double>(i);
    }
    return acc;
}

static double compute_product(int n) {
    CTRACK_NAME("compute_product");
    double acc = 1.0;
    for (int i = 1; i <= n; ++i) {
        acc *= 1.0 + 1.0 / static_cast<double>(i);
    }
    return acc;
}

int main() {
    const double s = compute_series(1000);
    const double p = compute_product(1000);

    if (s <= 0.0 || p <= 0.0) {
        std::cerr << "FATAL: business functions returned invalid results" << std::endl;
        return 1;
    }

    ctrack::ctrack_result_settings st;
    auto tables = ctrack::result_get_tables(st);

    int found_series = 0;
    int found_product = 0;
    for (const auto &row : tables.summary.rows) {
        // Search visible name in the formatted function name string.
        if (row.function_name.find("compute_series") != std::string::npos) {
            found_series = row.calls;
        } else if (row.function_name.find("compute_product") != std::string::npos) {
            found_product = row.calls;
        }
    }

    const bool ok = (found_series == 1) && (found_product == 1);
    if (!ok) {
        std::cerr << "FATAL: ctrack summary missing expected entries "
                  << "(series=" << found_series << ", product=" << found_product << ")"
                  << std::endl;
        return 1;
    }

    const std::string report = ctrack::result_as_string();
    if (report.find("Summary") == std::string::npos ||
        report.find("Details") == std::string::npos) {
        std::cerr << "FATAL: result_as_string() output malformed" << std::endl;
        return 1;
    }

    std::cout << "test_ctrack OK: series=" << found_series
              << " calls, product=" << found_product
              << " calls, summary/detail tables valid" << std::endl;
    // Print a short snippet as observable proof of the public API output.
    std::cout << report.substr(0, 400) << std::endl;
    return 0;
}