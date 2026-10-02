// Consumer-perspective smoke test for iguana 1.2.0 on HarmonyOS PC.
//
// It plays the role of a third-party application that installs the Conan
// package and uses the public headers only: reflection macros, JSON/XML/YAML
// writers and readers, error handling on malformed input. Nothing from the
// upstream build tree is included directly.
#include <cstdint>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>

#include <iguana/field_reflection.hpp>  // pulls the vendored frozen headers
#include <iguana/json_reader.hpp>
#include <iguana/json_writer.hpp>
#include <iguana/prettify.hpp>
#include <iguana/xml_reader.hpp>
#include <iguana/xml_writer.hpp>
#include <iguana/yaml_reader.hpp>
#include <iguana/yaml_writer.hpp>

struct sensor_reading_t {
  std::string sensor_id;
  double celsius;
  bool healthy;
};
YLT_REFL(sensor_reading_t, sensor_id, celsius, healthy);

struct device_report_t {
  std::string device_name;
  uint32_t battery_percent;
  std::vector<std::string> tags;
  std::map<std::string, int32_t> counters;
  sensor_reading_t primary_sensor;
};
YLT_REFL(device_report_t, device_name, battery_percent, tags, counters, primary_sensor);

struct boot_record_t {
  std::string device_name;
  uint32_t battery_percent;
  std::vector<std::string> tags;
  sensor_reading_t primary_sensor;
};
YLT_REFL(boot_record_t, device_name, battery_percent, tags, primary_sensor);

static int g_checks = 0;
static int g_failures = 0;

static void check(bool ok, const char *what) {
  ++g_checks;
  if (!ok) {
    ++g_failures;
    std::cerr << "CHECK FAILED: " << what << "\n";
  }
}

static device_report_t make_report() {
  device_report_t report;
  report.device_name = "HarmonyOS PC";
  report.battery_percent = 87;
  report.tags = {"ohos", "arm64", "iguana"};
  report.counters = {{"frames", 1234}, {"dropped", 0}};
  report.primary_sensor = {"cpu-temp", 36.5, true};
  return report;
}

int main() {
  const device_report_t report = make_report();

  // ── 1. JSON writer: reflected struct -> text ──
  std::string json;
  iguana::to_json(report, json);
  check(json.find("\"device_name\":\"HarmonyOS PC\"") != std::string::npos,
        "json keeps the string field");
  check(json.find("\"battery_percent\":87") != std::string::npos,
        "json keeps the integer field");
  check(json.find("cpu-temp") != std::string::npos,
        "json reaches the nested struct");
  check(json.find("ohos") != std::string::npos, "json keeps array elements");

  // ── 2. JSON reader: text -> reflected struct ──
  device_report_t parsed;
  iguana::from_json(parsed, json);
  check(parsed.device_name == report.device_name, "json round-trip: string");
  check(parsed.battery_percent == 87u, "json round-trip: unsigned integer");
  check(parsed.tags.size() == 3 && parsed.tags[1] == "arm64", "json round-trip: vector");
  check(parsed.counters["frames"] == 1234 && parsed.counters.count("dropped") == 1,
        "json round-trip: map");
  check(parsed.primary_sensor.celsius == 36.5 && parsed.primary_sensor.healthy,
        "json round-trip: nested struct fields");

  // ── 3. prettify keeps the document valid and multi-line ──
  const std::string pretty = iguana::prettify(json);
  check(pretty.find('\n') != std::string::npos, "prettify produces multi-line output");
  device_report_t reparsed;
  iguana::from_json(reparsed, pretty);
  check(reparsed.counters["frames"] == 1234, "prettified json stays parseable");

  // ── 4. YAML round-trip on the same struct ──
  std::string yaml;
  iguana::to_yaml(report, yaml);
  check(yaml.find("battery_percent") != std::string::npos, "yaml keeps field names");
  device_report_t from_yaml;
  iguana::from_yaml(from_yaml, yaml);
  check(from_yaml.tags.size() == 3 && from_yaml.counters["frames"] == 1234,
        "yaml round-trip: vector + map");

  // ── 5. XML round-trip (consumer-visible struct graph) ──
  boot_record_t boot;
  boot.device_name = report.device_name;
  boot.battery_percent = report.battery_percent;
  boot.tags = report.tags;
  boot.primary_sensor = report.primary_sensor;
  std::string xml;
  iguana::to_xml(boot, xml);
  boot_record_t from_xml;
  iguana::from_xml(from_xml, xml);
  check(from_xml.device_name == boot.device_name, "xml round-trip: string");
  check(from_xml.battery_percent == 87u, "xml round-trip: integer");
  check(from_xml.tags.size() == 3 && from_xml.primary_sensor.sensor_id == "cpu-temp",
        "xml round-trip: vector + nested struct");

  // ── 6. Error handling: malformed input must raise, not silently pass ──
  bool raised = false;
  try {
    device_report_t broken;
    std::string bad = R"({"battery_percent": 1.0})";
    iguana::from_json(broken, bad);
  } catch (const std::exception &) {
    raised = true;
  }
  check(raised, "malformed numeric field raises an exception");

  std::cout << "IGUANA_CONSUMER_CHECKS=" << g_checks
            << " FAILURES=" << g_failures << "\n";
  if (g_failures != 0) {
    std::cerr << "IGUANA_CONSUMER_FAILED\n";
    return 1;
  }
  std::cout << "IGUANA_CONSUMER_OK" << std::endl;
  return 0;
}
