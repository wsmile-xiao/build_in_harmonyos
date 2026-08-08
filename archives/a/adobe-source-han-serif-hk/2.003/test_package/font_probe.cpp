#include <dirent.h>
#include <sys/stat.h>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>
namespace {
uint16_t be16(const unsigned char* p) { return static_cast<uint16_t>((p[0] << 8) | p[1]); }
uint32_t be32(const unsigned char* p) { return (static_cast<uint32_t>(p[0]) << 24) | (static_cast<uint32_t>(p[1]) << 16) | (static_cast<uint32_t>(p[2]) << 8) | static_cast<uint32_t>(p[3]); }
bool ends_with(const std::string& v, const std::string& s) { return v.size() >= s.size() && v.compare(v.size() - s.size(), s.size(), s) == 0; }
void collect_fonts(const std::string& root, std::vector<std::string>& fonts) {
    DIR* dir = opendir(root.c_str()); if (!dir) throw std::runtime_error("cannot open directory: " + root);
    while (dirent* entry = readdir(dir)) {
        const std::string name(entry->d_name); if (name == "." || name == "..") continue;
        const std::string path = root + "/" + name; struct stat info {};
        if (stat(path.c_str(), &info) != 0) { closedir(dir); throw std::runtime_error("cannot stat: " + path); }
        if (S_ISDIR(info.st_mode)) collect_fonts(path, fonts);
        else if (S_ISREG(info.st_mode) && (ends_with(name, ".otf") || ends_with(name, ".ttf"))) fonts.push_back(path);
    }
    closedir(dir);
}
void validate_font(const std::string& path) {
    std::ifstream stream(path.c_str(), std::ios::binary | std::ios::ate); if (!stream) throw std::runtime_error("cannot read font: " + path);
    const std::streamoff end = stream.tellg(); if (end < 12) throw std::runtime_error("truncated SFNT header: " + path);
    const uint64_t size = static_cast<uint64_t>(end); stream.seekg(0); std::vector<unsigned char> bytes(static_cast<size_t>(size));
    stream.read(reinterpret_cast<char*>(bytes.data()), static_cast<std::streamsize>(size)); if (!stream) throw std::runtime_error("short read: " + path);
    const uint32_t signature = be32(bytes.data()); if (signature != 0x00010000u && signature != 0x4f54544fu) throw std::runtime_error("unsupported SFNT signature: " + path);
    const uint16_t count = be16(bytes.data() + 4); if (count == 0 || 12u + static_cast<uint64_t>(count) * 16u > size) throw std::runtime_error("invalid table directory: " + path);
    std::set<std::string> tags;
    for (uint16_t i = 0; i < count; ++i) {
        const unsigned char* record = bytes.data() + 12u + static_cast<size_t>(i) * 16u; const std::string tag(reinterpret_cast<const char*>(record), 4);
        const uint64_t offset = be32(record + 8), length = be32(record + 12); if (offset > size || length > size - offset) throw std::runtime_error("out-of-bounds table " + tag + ": " + path); tags.insert(tag);
    }
    const char* required[] = {"name", "cmap", "head", "maxp"}; for (const char* tag : required) if (tags.count(tag) == 0) throw std::runtime_error(std::string("missing ") + tag + " table: " + path);
    if (tags.count("glyf") == 0 && tags.count("CFF ") == 0 && tags.count("CFF2") == 0) throw std::runtime_error("missing glyph outline table: " + path);
}
}
int main(int argc, char** argv) {
    try {
        if (argc == 3 && std::string(argv[1]) == "--expect-invalid") { try { validate_font(argv[2]); } catch (const std::exception&) { std::cout << "PASS: corrupted font rejected\n"; return 0; } std::cerr << "FAIL: corrupted font was accepted\n"; return 1; }
        if (argc != 3) { std::cerr << "usage: font_probe <font-root> <expected-count>\n"; return 2; }
        std::vector<std::string> fonts; collect_fonts(argv[1], fonts); const long expected = std::strtol(argv[2], nullptr, 10);
        if (expected <= 0 || fonts.size() != static_cast<size_t>(expected)) throw std::runtime_error("font count mismatch: expected " + std::to_string(expected) + ", got " + std::to_string(fonts.size()));
        for (const std::string& font : fonts) validate_font(font); std::cout << "PASS: parsed " << fonts.size() << " packaged OpenType fonts\n"; return 0;
    } catch (const std::exception& error) { std::cerr << "FAIL: " << error.what() << '\n'; return 1; }
}
