#define TINYGLTF_LOADER_IMPLEMENTATION
#define STB_IMAGE_IMPLEMENTATION
#include "tiny_gltf_loader.h"

#include <iostream>
#include <string>

static int check(bool condition, const char *description) {
  if (!condition) {
    std::cerr << "FAIL: " << description << std::endl;
    return 1;
  }
  return 0;
}

int main() {
  const char document[] =
      "{\"asset\":{\"version\":\"1.0\"},"
      "\"scene\":\"default\","
      "\"scenes\":{\"default\":{\"nodes\":[]}},"
      "\"nodes\":{},\"accessors\":{},\"buffers\":{},"
      "\"bufferViews\":{}}";

  tinygltf::TinyGLTFLoader loader;
  tinygltf::Scene scene;
  std::string error;
  int failures = 0;

  bool parsed = loader.LoadFromString(
      scene, error, document, sizeof(document) - 1, "");
  failures += check(parsed, "LoadFromString accepts a valid glTF 1.0 document");
  failures += check(scene.asset.version == "1.0", "asset version is retained");
  failures += check(scene.defaultScene == "default", "default scene is retained");
  failures += check(scene.scenes.size() == 1, "scene inventory is populated");

  tinygltf::Scene invalid_scene;
  error.clear();
  const char invalid_document[] = "{\"nodes\":{}}";
  bool invalid = loader.LoadFromString(
      invalid_scene, error, invalid_document, sizeof(invalid_document) - 1, "");
  failures += check(!invalid, "invalid glTF is rejected");
  failures += check(
      error.find("scene") != std::string::npos,
      "invalid glTF reports the missing scene field");

  if (failures != 0) {
    return 1;
  }
  std::cout << "tinygltfloader consumer test: 6 checks passed" << std::endl;
  return 0;
}
