// Consumer contract for the installed KiCad template resources.

#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

namespace fs = std::filesystem;

namespace {

void require(bool condition, const std::string& message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

std::string read_prefix(const fs::path& path) {
    std::ifstream input(path, std::ios::binary);
    require(static_cast<bool>(input), "cannot read resource: " + path.string());
    std::string data(128, '\0');
    input.read(&data[0], static_cast<std::streamsize>(data.size()));
    data.resize(static_cast<size_t>(input.gcount()));
    require(!data.empty(), "empty resource: " + path.string());
    return data;
}

void check_signature(const fs::path& path, const std::string& signature) {
    const std::string data = read_prefix(path);
    const size_t first = data.find_first_not_of(" \t\r\n");
    require(first != std::string::npos && data.compare(first, signature.size(), signature) == 0,
            "unexpected KiCad signature in: " + path.string());
}

}  // namespace

int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr << "usage: kicad_templates_probe <template-resource-root>\n";
        return 2;
    }

    try {
        const fs::path root(argv[1]);
        const fs::path projects = root / "Projects";
        require(fs::is_directory(root), "template resource root is not a directory");
        require(fs::is_directory(projects), "Projects directory is missing");

        const std::set<std::string> expected_projects = {
            "API_Series-500", "Arduino_Mega", "Arduino_Micro", "Arduino_Nano",
            "Arduino_Pro_Mini", "Arduino_Uno", "BeagleBone-Black-Cape",
            "Edgeberry_Cartridge", "EuroCard160mmX100mm", "Hammond_1593K_Enclosure",
            "KiCad_MR_diagrams_large_parts", "KiCad_MR_diagrams_small_parts",
            "RaspberryPi-HAT", "RaspberryPi-uHAT", "STM32_Nucleo-64_Morpho",
            "STM32H7_DevEBox", "TI-LaunchPad-BoosterPack-20pin",
            "TI-LaunchPad-BoosterPack-40pin", "stm32f100-discovery-shield",
        };
        std::set<std::string> actual_projects;
        for (const fs::directory_entry& entry : fs::directory_iterator(projects)) {
            if (entry.is_directory()) {
                actual_projects.insert(entry.path().filename().string());
            }
        }
        require(actual_projects == expected_projects,
                "Projects root directory inventory does not match KiCad 10.0.5");

        std::map<std::string, size_t> extensions;
        size_t resource_files = 0;
        std::map<std::string, fs::path> samples;
        for (const fs::directory_entry& entry : fs::recursive_directory_iterator(root)) {
            if (!entry.is_regular_file()) {
                continue;
            }
            ++resource_files;
            const std::string extension = entry.path().extension().string();
            ++extensions[extension];
            if (samples.find(extension) == samples.end()) {
                samples[extension] = entry.path();
            }
        }
        require(resource_files == 177, "resource file count drifted from 177");
        require(extensions[".kicad_pcb"] == 19, "expected 19 .kicad_pcb files");
        require(extensions[".kicad_pro"] == 19, "expected 19 .kicad_pro files");
        require(extensions[".kicad_sch"] == 19, "expected 19 .kicad_sch files");
        require(extensions[".kicad_wks"] == 36, "expected 36 .kicad_wks files");

        check_signature(samples[".kicad_pcb"], "(kicad_pcb");
        check_signature(samples[".kicad_pro"], "{");
        check_signature(samples[".kicad_sch"], "(kicad_sch");
        check_signature(samples[".kicad_wks"], "(page_layout");

        const fs::path direct_worksheet = root / "A2_ISO5457-1999_ISO7200-2004_EN.kicad_wks";
        require(fs::is_regular_file(direct_worksheet),
                "worksheet was not installed at the template root");
        check_signature(direct_worksheet, "(page_layout");

        std::cout << "kicad-library-templates consumer probe passed: "
                  << actual_projects.size() << " projects, " << extensions[".kicad_wks"]
                  << " worksheets, " << resource_files << " resource files\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "kicad-library-templates consumer probe FAILED: " << error.what() << "\n";
        return 1;
    }
}
