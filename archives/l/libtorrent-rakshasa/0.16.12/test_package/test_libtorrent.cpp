#include <torrent/object.h>
#include <torrent/object_stream.h>

#include <iostream>
#include <sstream>
#include <string>

namespace {

int fail(const char* message) {
  std::cerr << "libtorrent consumer test failed: " << message << '\n';
  return 1;
}

}  // namespace

int main() {
  torrent::Object original = torrent::Object::create_map();
  original.insert_key("name", torrent::Object("HarmonyOS"));
  original.insert_key("piece-length", torrent::Object(16384));

  torrent::Object files = torrent::Object::create_list();
  files.insert_back(torrent::Object("alpha"));
  files.insert_back(torrent::Object("beta"));
  original.insert_key("files", files);

  std::ostringstream output;
  torrent::object_write_bencode(&output, &original);
  const std::string encoded = output.str();
  const std::string expected =
      "d5:filesl5:alpha4:betae4:name9:HarmonyOS12:piece-lengthi16384ee";
  if (encoded != expected) {
    return fail("unexpected bencode output");
  }

  torrent::Object decoded;
  std::istringstream input(encoded);
  torrent::object_read_bencode(&input, &decoded);

  if (!decoded.is_map()) {
    return fail("decoded object is not a map");
  }
  if (decoded.get_key_string("name") != "HarmonyOS") {
    return fail("decoded string value mismatch");
  }
  if (decoded.get_key_value("piece-length") != 16384) {
    return fail("decoded integer value mismatch");
  }

  const torrent::Object::list_type& decoded_files =
      decoded.get_key_list("files");
  if (decoded_files.size() != 2) {
    return fail("decoded list size mismatch");
  }
  if (decoded_files[0].as_string() != "alpha") {
    return fail("decoded first list entry mismatch");
  }
  if (decoded_files[1].as_string() != "beta") {
    return fail("decoded second list entry mismatch");
  }

  if (torrent::object_sha1(&decoded).size() != 20) {
    return fail("SHA-1 digest length mismatch");
  }

  return 0;
}
