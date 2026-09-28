// Consumer use case for ctrack (header-only library).
// Simulates a business upper-layer component: it consumes ONLY the
// installed/exported public header (include/ctrack.hpp), the public API
// (CTRACK_NAME macro, result_get_summary_table/result_as_string) and
// normal link targets. It verifies a business-meaningful public API call
// plus its observable result (tracked entries with expected call counts).
#include <cmath>
#include <iostream>
#include <map>
#include <string>
#include "ctrack.hpp"

// Business component under profiling.
static double price_volatility(const std::map<std::string, double> &prices) {
    CTRACK_NAME("price_volatility");
    if (prices.empty()) return 0.0;
    double mean = 0.0;
    for (const auto &kv : prices) mean += kv.second;
    mean /= static_cast<double>(prices.size());
    double var = 0.0;
    for (const auto &kv : prices) var += (kv.second - mean) * (kv.second - mean);
    return std::sqrt(var / static_cast<double>(prices.size()));
}

static double moving_average(const double *samples, int n, int window) {
    CTRACK_NAME("moving_average");
    if (n <= 0 || window <= 0) return 0.0;
    double sum = 0.0;
    for (int i = 0; i < window && i < n; ++i) sum += samples[i];
    return sum / static_cast<double>(window < n ? window : n);
}

int main() {
    std::map<std::string, double> prices = {
        {"AAPL", 150.2}, {"MSFT", 310.5}, {"GOOG", 2750.0}, {"AMZN", 3300.1}};
    const double samples[] = {1.0, 2.0, 3.0, 4.0, 5.0, 6.0};

    double vol = price_volatility(prices);
    double ma = moving_average(samples, 6, 3);

    if (!(vol > 0.0) || !(ma > 0.0)) {
        std::cerr << "FAIL: business logic produced invalid results" << std::endl;
        return 1;
    }

    // Observable result: public API must report both tracked components.
    ctrack::ctrack_result_settings st;
    auto tables = ctrack::result_get_tables(st);

    int calls_vol = -1;
    int calls_ma = -1;
    for (const auto &row : tables.summary.rows) {
        if (row.function_name.find("price_volatility") != std::string::npos) {
            calls_vol = row.calls;
        } else if (row.function_name.find("moving_average") != std::string::npos) {
            calls_ma = row.calls;
        }
    }

    if (calls_vol != 1 || calls_ma != 1) {
        std::cerr << "FAIL: public API did not report expected tracked entries "
                  << "(volatility=" << calls_vol << ", moving_average=" << calls_ma << ")"
                  << std::endl;
        return 1;
    }

    // result_get_tables() already snapshots-and-clears the store; the
    // observable output comes from the same snapshot (no second fetch).
    std::cout << "ctrack consumer OK: volatility=" << vol << " ma=" << ma
              << ", tracked entries verified via public API" << std::endl;
    std::cout << "---- ctrack summary table (public API output) ----" << std::endl;
    for (const auto &row : tables.summary.rows) {
        std::cout << row.function_name << " | calls=" << row.calls
                  << " | line=" << row.line
                  << " | time_ae_all=" << row.time_ae_all.count() << "ns"
                  << std::endl;
    }
    return 0;
}