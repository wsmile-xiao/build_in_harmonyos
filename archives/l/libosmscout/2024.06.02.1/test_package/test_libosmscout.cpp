/*
  Consumer acceptance test for the libosmscout OHOS package.

  The program exercises the *public* API of every library that the package
  ships and performs real work with real data:

    stage 1  core geometry / number codec            OSMScout::OSMScout
    stage 2  GPX XML parsing (libxml2)               OSMScout::GPX
    stage 3  OSM XML -> imported map database        OSMScout::Import
    stage 4  database open + client directory check  OSMScout::OSMScout/Client
    stage 5  packaged standard.oss style sheet       OSMScout::Map
    stage 6  tile lookup + SVG rendering             OSMScout::Map/MapSVG

  The map database used by stages 4-6 is produced by the test itself from an
  inline OSM XML document, so nothing but the package content is required.
*/
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <list>
#include <memory>
#include <sstream>
#include <string>

#include <osmscout/GeoCoord.h>
#include <osmscout/TypeConfig.h>
#include <osmscout/db/Database.h>
#include <osmscout/projection/MercatorProjection.h>
#include <osmscout/util/Bearing.h>
#include <osmscout/util/Distance.h>
#include <osmscout/util/GeoBox.h>
#include <osmscout/util/Magnification.h>
#include <osmscout/util/Number.h>

#include <osmscoutmap/MapData.h>
#include <osmscoutmap/MapParameter.h>
#include <osmscoutmap/MapService.h>
#include <osmscoutmap/StyleConfig.h>

#include <osmscoutmapsvg/MapPainterSVG.h>

#include <osmscoutimport/Import.h>
#include <osmscoutimport/ImportProgress.h>

#include <osmscoutgpx/GpxFile.h>
#include <osmscoutgpx/Import.h>
#include <osmscoutgpx/Track.h>

#include <osmscoutclient/MapDirectory.h>

namespace fs = std::filesystem;

namespace {

int g_checks = 0;
int g_failures = 0;

void Check(bool ok, const std::string& what)
{
  ++g_checks;
  if (ok) {
    std::cout << "  [ok]   " << what << std::endl;
  }
  else {
    ++g_failures;
    std::cout << "  [FAIL] " << what << std::endl;
  }
}

std::string StylesheetDir(const char* argv0)
{
  if (const char* env = std::getenv("OSMSCOUT_TEST_STYLESHEETS"); env != nullptr && *env != '\0') {
    return env;
  }
  (void)argv0;
  return OSMSCOUT_TEST_STYLESHEETS;
}

// ---------------------------------------------------------------------------
void TestCoreGeometry()
{
  std::cout << "[stage 1] core geometry and number codec" << std::endl;

  const osmscout::GeoCoord berlin(52.520008, 13.404954);
  const osmscout::GeoCoord potsdam(52.390569, 13.064473);

  Check(berlin.IsValid(), "GeoCoord(52.52, 13.40) is valid");
  Check(berlin == berlin, "GeoCoord equality");
  Check(berlin != potsdam, "GeoCoord inequality");

  const double meters = berlin.GetDistance(potsdam).AsMeter();
  std::cout << "         Berlin->Potsdam distance = " << meters << " m" << std::endl;
  Check(meters > 24000.0 && meters < 31000.0,
        "GetDistance Berlin->Potsdam within 24..31 km");

  const osmscout::Bearing east = osmscout::Bearing::Degrees(90.0);
  Check(std::fabs(east.AsDegrees() - 90.0) < 1.0e-6, "Bearing::Degrees(90) round trips");
  Check(std::fabs(east.AsRadians() - M_PI / 2.0) < 1.0e-9, "Bearing::AsRadians is pi/2");
  Check(std::fabs((osmscout::Bearing::Degrees(350.0) + osmscout::Bearing::Degrees(20.0)).AsDegrees() - 10.0) < 1.0e-6,
        "Bearing addition wraps around 360 degrees");

  const osmscout::GeoBox box(osmscout::GeoCoord(52.0, 13.0), osmscout::GeoCoord(53.0, 14.0));
  Check(box.IsValid(), "GeoBox(min,max) is valid");
  Check(!box.IsValid() == false, "GeoBox validity is stable");
  const osmscout::GeoCoord minCoord = box.GetMinCoord();
  const osmscout::GeoCoord maxCoord = box.GetMaxCoord();
  Check(minCoord.GetLat() <= berlin.GetLat() && berlin.GetLat() <= maxCoord.GetLat() &&
        minCoord.GetLon() <= berlin.GetLon() && berlin.GetLon() <= maxCoord.GetLon(),
        "GeoBox min/max bound Berlin");

  char buffer[32];
  unsigned int written = osmscout::EncodeNumber(static_cast<uint32_t>(1234567u), buffer);
  uint32_t decodedUnsigned = 0;
  const unsigned int readUnsigned = osmscout::DecodeNumber(buffer, decodedUnsigned);
  Check(written == readUnsigned && decodedUnsigned == 1234567u,
        "EncodeNumber/DecodeNumber uint32 round trip");

  written = osmscout::EncodeNumber(static_cast<int32_t>(-98765), buffer);
  int32_t decodedSigned = 0;
  osmscout::DecodeNumber(buffer, decodedSigned);
  Check(decodedSigned == -98765, "EncodeNumber/DecodeNumber int32 round trip (negative)");
}

// ---------------------------------------------------------------------------
void WriteGpx(const fs::path& path)
{
  std::ofstream out(path);
  out << "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
         "<gpx version=\"1.1\" creator=\"libosmscout-consumer-test\"\n"
         "     xmlns=\"http://www.topografix.com/GPX/1/1\">\n"
         "  <metadata><name>consumer track</name></metadata>\n"
         "  <trk>\n"
         "    <name>consumer</name>\n"
         "    <trkseg>\n"
         "      <trkpt lat=\"52.520000\" lon=\"13.404000\"><ele>34</ele>"
         "<time>2024-06-02T10:00:00Z</time></trkpt>\n"
         "      <trkpt lat=\"52.521000\" lon=\"13.405000\"><ele>36</ele>"
         "<time>2024-06-02T10:01:00Z</time></trkpt>\n"
         "      <trkpt lat=\"52.523000\" lon=\"13.409000\"><ele>40</ele>"
         "<time>2024-06-02T10:02:00Z</time></trkpt>\n"
         "    </trkseg>\n"
         "  </trk>\n"
         "</gpx>\n";
}

bool TestGpxImport(const fs::path& tmpDir)
{
  std::cout << "[stage 2] GPX parsing through libxml2 (OSMScout::GPX)" << std::endl;

  const fs::path gpxPath = tmpDir / "consumer-track.gpx";
  WriteGpx(gpxPath);

  osmscout::gpx::GpxFile gpx;
  const bool imported = osmscout::gpx::ImportGpx(gpxPath.string(), gpx);
  Check(imported, "gpx::ImportGpx parsed the file");
  Check(gpx.tracks.size() == 1, "exactly one track element");

  if (gpx.tracks.empty()) {
    return false;
  }

  const osmscout::gpx::Track& track = gpx.tracks.front();
  Check(track.GetPointCount() == 3, "three track points");

  const double length = track.GetLength().AsMeter();
  std::cout << "         track length = " << length << " m" << std::endl;
  Check(length > 300.0 && length < 800.0, "track length within 300..800 m");
  return imported;
}

// ---------------------------------------------------------------------------
void WriteOsmXml(const fs::path& path)
{
  std::ofstream out(path);
  out << "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
         "<osm version=\"0.6\" generator=\"libosmscout-consumer-test\">\n"
         "  <bounds minlat=\"52.5100\" minlon=\"13.3900\" maxlat=\"52.5350\" maxlon=\"13.4250\"/>\n"
         "  <node id=\"1\" lat=\"52.5225\" lon=\"13.4050\" version=\"1\">\n"
         "    <tag k=\"place\" v=\"city\"/><tag k=\"name\" v=\"Consumerville\"/>\n"
         "    <tag k=\"population\" v=\"120000\"/>\n"
         "  </node>\n"
         "  <node id=\"2\" lat=\"52.5200\" lon=\"13.4000\" version=\"1\">\n"
         "    <tag k=\"place\" v=\"suburb\"/><tag k=\"name\" v=\"Consumer Quarter\"/>\n"
         "  </node>\n"
         "  <node id=\"3\" lat=\"52.5240\" lon=\"13.4100\" version=\"1\">\n"
         "    <tag k=\"amenity\" v=\"library\"/><tag k=\"name\" v=\"Consumer Library\"/>\n"
         "  </node>\n"
         "  <node id=\"4\" lat=\"52.5190\" lon=\"13.3980\" version=\"1\"/>\n"
         "  <node id=\"5\" lat=\"52.5190\" lon=\"13.4120\" version=\"1\"/>\n"
         "  <node id=\"6\" lat=\"52.5260\" lon=\"13.4120\" version=\"1\"/>\n"
         "  <node id=\"7\" lat=\"52.5260\" lon=\"13.3980\" version=\"1\"/>\n"
         "  <node id=\"8\" lat=\"52.5175\" lon=\"13.4020\" version=\"1\"/>\n"
         "  <node id=\"9\" lat=\"52.5175\" lon=\"13.4100\" version=\"1\"/>\n"
         "  <way id=\"100\" version=\"1\">\n"
         "    <nd ref=\"4\"/><nd ref=\"5\"/><nd ref=\"6\"/><nd ref=\"7\"/><nd ref=\"4\"/>\n"
         "    <tag k=\"highway\" v=\"residential\"/><tag k=\"name\" v=\"Consumer Ring\"/>\n"
         "  </way>\n"
         "  <way id=\"101\" version=\"1\">\n"
         "    <nd ref=\"8\"/><nd ref=\"9\"/>\n"
         "    <tag k=\"highway\" v=\"primary\"/><tag k=\"name\" v=\"Consumer Avenue\"/>\n"
         "    <tag k=\"maxspeed\" v=\"50\"/><tag k=\"lanes\" v=\"2\"/>\n"
         "  </way>\n"
         "  <way id=\"102\" version=\"1\">\n"
         "    <nd ref=\"4\"/><nd ref=\"8\"/>\n"
         "    <tag k=\"highway\" v=\"footway\"/><tag k=\"name\" v=\"Consumer Footpath\"/>\n"
         "  </way>\n"
         "  <way id=\"103\" version=\"1\">\n"
         "    <nd ref=\"5\"/><nd ref=\"9\"/><nd ref=\"6\"/><nd ref=\"5\"/>\n"
         "    <tag k=\"building\" v=\"yes\"/><tag k=\"name\" v=\"Consumer Hall\"/>\n"
         "    <tag k=\"addr:street\" v=\"Consumer Avenue\"/><tag k=\"addr:housenumber\" v=\"7\"/>\n"
         "  </way>\n"
         "</osm>\n";
}

bool TestOsmImport(const fs::path& tmpDir, const fs::path& stylesheetDir, fs::path& dbDir)
{
  std::cout << "[stage 3] OSM XML import through libxml2 (OSMScout::Import)" << std::endl;

  const fs::path osmPath = tmpDir / "consumer.osm";
  WriteOsmXml(osmPath);

  dbDir = tmpDir / "db";
  fs::remove_all(dbDir);
  fs::create_directories(dbDir);

  const fs::path typeFile = stylesheetDir / "map.ost";
  Check(fs::exists(typeFile), "packaged type configuration map.ost exists");

  osmscout::ImportParameter parameter;
  std::list<std::string> mapFiles;
  mapFiles.push_back(osmPath.string());
  parameter.SetTypefile(typeFile.string());
  parameter.SetMapfiles(mapFiles);
  parameter.SetDestinationDirectory(dbDir.string());
  parameter.AddRouter(osmscout::ImportParameter::Router(
      osmscout::vehicleBicycle | osmscout::vehicleFoot | osmscout::vehicleCar, "router"));

  osmscout::ImportProgress progress;
  bool imported = false;
  try {
    osmscout::Importer importer(parameter);
    imported = importer.Import(progress);
  }
  catch (const std::exception& e) {
    std::cout << "         import raised: " << e.what() << std::endl;
    imported = false;
  }
  Check(imported, "Importer::Import produced a database");
  return imported;
}

// ---------------------------------------------------------------------------
bool TestDatabaseOpen(const fs::path& dbDir, osmscout::DatabaseRef& database,
                      osmscout::TypeConfigRef& typeConfig)
{
  std::cout << "[stage 4] database open and client directory validation" << std::endl;

  osmscout::DatabaseParameter parameter;
  database = std::make_shared<osmscout::Database>(parameter);

  const bool opened = database->Open(dbDir.string());
  Check(opened, "Database::Open on the imported directory");
  if (!opened) {
    return false;
  }

  typeConfig = database->GetTypeConfig();
  Check(typeConfig != nullptr, "Database::GetTypeConfig returns a configuration");
  if (typeConfig != nullptr) {
    std::cout << "         imported types = " << typeConfig->GetTypeCount() << std::endl;
    Check(typeConfig->GetTypeCount() > 100, "type configuration carries the OSM types");
    Check(typeConfig->GetTypeInfo("highway_primary") != nullptr,
          "highway_primary type present in the imported configuration");
    Check(typeConfig->GetTypeInfo("building") != nullptr,
          "building type present in the imported configuration");
  }

  // the client side database abstraction must accept the produced directory
  osmscout::MapDirectory directory(dbDir);
  Check(directory.IsValid(), "client MapDirectory accepts the imported database");
  Check(directory.ByteSize() > 0, "imported database occupies disk space");
  Check(!osmscout::MapDirectory::MandatoryFiles().empty(),
        "MapDirectory::MandatoryFiles is not empty");
  return true;
}

// ---------------------------------------------------------------------------
osmscout::StyleConfigRef TestStyleConfig(const fs::path& stylesheetDir,
                                         const osmscout::TypeConfigRef& typeConfig)
{
  std::cout << "[stage 5] packaged style sheet compilation (OSMScout::Map)" << std::endl;

  const fs::path styleFile = stylesheetDir / "standard.oss";
  Check(fs::exists(styleFile), "packaged style sheet standard.oss exists");

  osmscout::StyleConfigRef styleConfig = std::make_shared<osmscout::StyleConfig>(typeConfig);
  const bool loaded = styleConfig->Load(styleFile.string());
  Check(loaded, "StyleConfig::Load compiled standard.oss");
  Check(styleConfig->GetErrors().empty(), "style sheet has no errors");
  for (const auto& error : styleConfig->GetErrors()) {
    std::cout << "         style error: " << error.GetDescription() << std::endl;
  }
  for (const auto& warning : styleConfig->GetWarnings()) {
    std::cout << "         style warning: " << warning.GetDescription() << std::endl;
  }
  return styleConfig;
}

// ---------------------------------------------------------------------------
void TestMapRendering(const osmscout::DatabaseRef& database,
                      const osmscout::StyleConfigRef& styleConfig,
                      const fs::path& tmpDir)
{
  std::cout << "[stage 6] tile lookup and SVG rendering (OSMScout::Map/MapSVG)" << std::endl;

  osmscout::MapService mapService(database);

  const osmscout::Magnification magnification(osmscout::Magnification::magClose);
  osmscout::MercatorProjection projection;
  const bool projectionOk = projection.Set(osmscout::GeoCoord(52.5225, 13.4050),
                                           magnification,
                                           96.0,
                                           400,
                                           300);
  Check(projectionOk, "MercatorProjection::Set");

  std::list<osmscout::TileRef> tiles;
  mapService.LookupTiles(projection, tiles);
  std::cout << "         tiles looked up = " << tiles.size() << std::endl;
  Check(!tiles.empty(), "MapService::LookupTiles found tiles in the imported database");

  osmscout::AreaSearchParameter searchParameter;
  const bool loaded = mapService.LoadMissingTileData(searchParameter, *styleConfig, tiles);
  Check(loaded, "MapService::LoadMissingTileData");

  osmscout::MapData mapData;
  mapService.AddTileDataToMapData(tiles, mapData);
  mapService.GetGroundTiles(projection, mapData.groundTiles);
  std::cout << "         map data: nodes=" << mapData.nodes.size()
            << " ways=" << mapData.ways.size()
            << " areas=" << mapData.areas.size() << std::endl;
  Check(!mapData.ways.empty(), "MapData carries ways from the imported database");
  Check(!mapData.nodes.empty(), "MapData carries nodes from the imported database");

  osmscout::MapParameter drawParameter;
  drawParameter.SetFontName("sans-serif");
  drawParameter.SetFontSize(3.0);
  drawParameter.SetRenderUnknowns(true);

  osmscout::MapPainterSVG painter(styleConfig);
  std::ostringstream svg;
  const bool drawn = painter.DrawMap(projection, drawParameter, mapData, svg);
  Check(drawn, "MapPainterSVG::DrawMap");

  const std::string document = svg.str();
  const fs::path svgPath = tmpDir / "render.svg";
  {
    std::ofstream out(svgPath);
    out << document;
  }
  std::cout << "         svg bytes = " << document.size() << std::endl;
  Check(document.find("<svg") != std::string::npos, "SVG document contains an <svg> element");
  Check(document.size() > 500, "SVG document is not empty");
  Check(fs::exists(svgPath) && fs::file_size(svgPath) == document.size(),
        "SVG document written to disk");
}

} // namespace

int main(int argc, char* argv[])
{
  std::cout << "libosmscout consumer acceptance test" << std::endl;

  fs::path tmpDir = fs::current_path() / "consumer-tmp";
  fs::remove_all(tmpDir);
  fs::create_directories(tmpDir);

  const std::string stylesheetDir = StylesheetDir(argc > 1 ? argv[1] : nullptr);
  std::cout << "stylesheet directory: " << stylesheetDir << std::endl;
  Check(fs::is_directory(stylesheetDir), "stylesheet directory is available");

  TestCoreGeometry();
  TestGpxImport(tmpDir);

  fs::path dbDir;
  const bool imported = TestOsmImport(tmpDir, stylesheetDir, dbDir);

  if (imported) {
    osmscout::DatabaseRef database;
    osmscout::TypeConfigRef typeConfig;
    if (TestDatabaseOpen(dbDir, database, typeConfig) && typeConfig != nullptr) {
      osmscout::StyleConfigRef styleConfig = TestStyleConfig(stylesheetDir, typeConfig);
      TestMapRendering(database, styleConfig, tmpDir);
      database->Close();
    }
  }
  else {
    std::cout << "  [skip] stages 4-6 skipped, the import did not succeed" << std::endl;
  }

  std::cout << "checks: " << g_checks << "  failures: " << g_failures << std::endl;
  if (g_failures != 0) {
    std::cout << "RESULT: FAILED" << std::endl;
    return 1;
  }
  std::cout << "RESULT: PASSED (" << g_checks << "/" << g_checks << ")" << std::endl;
  return 0;
}
