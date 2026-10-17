// test_libkml.cpp — L1 consumer test for libkml 1.3.0.
// Actually calls the installed libkml API: version string + real KML parse.

#include <string>

#include "kml/base/version.h"
#include "kml/engine/kml_file.h"
#include "kml/engine/kml_stream.h"
#include "kml/dom/kml_funcs.h"

int main() {
  // 1) Version API of chunk kmlbase.
  const std::string version = kmlbase::Version::GetString();
  if (version.empty()) {
    return 1;
  }

  // 2) Real parse of a small KML document (exercises expat + zlib + uriparser).
  const std::string kml =
      "<kml xmlns=\"http://www.opengis.net/kml/2.2\">"
      "<Placemark><name>test</name>"
      "<Point><coordinates>1,2,0</coordinates></Point>"
      "</Placemark></kml>";
  std::string errors;
  kmlengine::KmlFilePtr kml_file =
      kmlengine::KmlFile::CreateFromParse(kml, &errors);
  if (kml_file.get() == NULL) {
    return 2;
  }
  const kmldom::ElementPtr root = kml_file->get_root();
  if (root.get() == NULL) {
    return 3;
  }
  std::string xml_output;
  if (!kml_file->SerializeToString(&xml_output) || xml_output.empty()) {
    return 4;
  }
  return 0;
}