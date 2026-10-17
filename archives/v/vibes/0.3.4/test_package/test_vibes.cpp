/**
 * test_vibes.cpp — consumer test for the packaged VIBES C++ client API.
 *
 * Links against the installed libvibes and exercises the real public API:
 *   1. Value/Params JSON serialization (pure, headless).
 *   2. File-mode drawing: beginDrawing(file) + drawing commands write JSON
 *      messages to the file (the VIBES viewer is a separate process that
 *      watches this file, so no GUI is required), then validates the file
 *      content is non-empty and carries the expected draw payloads.
 *
 * Every assertion prints one "CHECK-OK: <name>" line; the C++ test harness
 * (conanfile.py) counts them for the HMBS_TEST_PACKAGE_RESULT marker.
 */

#include "vibes.h"

#include <cstdio>
#include <cstring>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

static int s_checks = 0;
static int s_failures = 0;

#define CHECK(name, cond)                                                    \
  do {                                                                       \
    ++s_checks;                                                              \
    if (cond) {                                                              \
      std::cout << "CHECK-OK: " << name << "\n";                             \
    } else {                                                                 \
      ++s_failures;                                                          \
      std::cout << "CHECK-FAIL: " << name << " (line " << __LINE__ << ")\n"; \
    }                                                                        \
  } while (0)

static std::string read_all(const std::string &path) {
  std::ifstream in(path.c_str(), std::ios::in | std::ios::binary);
  std::ostringstream ss;
  ss << in.rdbuf();
  return ss.str();
}

int main(int argc, char **argv) {
  const std::string outfile =
      (argc > 1) ? argv[1] : std::string("vibes_test.json");

  // --- 1. Value JSON serialization (pure, headless, no viewer needed) ---
  CHECK("value_int", vibes::Value(42).toJSONString() == "42");
  CHECK("value_decimal", vibes::Value(3.5).toJSONString() == "3.5");
  CHECK("value_bool", vibes::Value(true).toJSONString() == "true");
  CHECK("value_string",
        vibes::Value(std::string("hi")).toJSONString() == "\"hi\"");
  {
    vibes::Params p;
    p["color"] = std::string("red");
    p["width"] = 2;
    std::string j = p.toJSON();
    CHECK("params_color",
          j.find("\"color\":\"red\"") != std::string::npos);
    CHECK("params_width", j.find("\"width\":2") != std::string::npos);
  }

  // --- 2. File-mode drawing: beginDrawing(file) + drawing commands ---
  vibes::beginDrawing(outfile);
  vibes::newFigure("fig1");
  vibes::clearFigure("fig1");
  vibes::drawBox(0.0, 1.0, 0.0, 1.0);
  vibes::drawBox(0.0, 1.0, 0.0, 1.0, "blue");
  vibes::axisLimits(0.0, 10.0, 0.0, 10.0, "fig1");
  {
    std::vector<double> x;
    x.push_back(0.0);
    x.push_back(1.0);
    std::vector<double> y;
    y.push_back(0.0);
    y.push_back(2.0);
    vibes::drawLine(x, y, "green");
  }

  // The viewer watches the file; every write is fflushed, so a separate
  // reader handle sees the flushed data immediately.
  std::string content = read_all(outfile);
  CHECK("draw_file_nonempty", !content.empty());
  CHECK("draw_new_figure",
        content.find("\"action\":\"new\"") != std::string::npos);
  CHECK("draw_clear_figure",
        content.find("\"action\":\"clear\"") != std::string::npos);
  CHECK("draw_box_type",
        content.find("\"action\":\"draw\"") != std::string::npos &&
            content.find("\"type\":\"box\"") != std::string::npos);
  CHECK("draw_line_type",
        content.find("\"type\":\"line\"") != std::string::npos);
  CHECK("draw_axis_view",
        content.find("\"viewbox\"") != std::string::npos);
  CHECK("draw_figure_name",
        content.find("\"figure\":\"fig1\"") != std::string::npos);

  std::cout << "SUMMARY: " << s_failures << " failures / " << s_checks
            << " checks\n";
  return s_failures == 0 ? 0 : 1;
}
