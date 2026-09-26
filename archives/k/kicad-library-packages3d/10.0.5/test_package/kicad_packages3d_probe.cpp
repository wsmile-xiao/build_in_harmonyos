// kicad_packages3d_probe — kicad-library-packages3d 消费者测试探针
//
// 真实消费 3D 模型数据：核对 .3dshapes 家族目录集合与文件计数，
// 全量校验 .step 文件 ISO-10303-21 头/尾结构，并对截断文件做故障
// 注入负向校验，验证包内模型真实可读、格式与 KiCad 3D 渲染器及
// MCAD 软件的读取口径一致。
//
// KiCad 10 起上游模型库仅含 STEP（VRML .wrl 已从库中移除）。

#include <dirent.h>
#include <sys/stat.h>
#include <unistd.h>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

// 与配方 build() 一致的实测清单（上游 10.0.5 tag，Ubuntu 再打包归档：
// 移除 1 个 .fcstd 源文件，辅助文件 48 / 总 7293）。
const long kExpectedDirCount = 105;    // .3dshapes 家族目录数
const long kExpectedStepCount = 7245;  // .step 文件数
const long kExpectedAuxCount = 48;     // 辅助文件数（CREDITS.md 等）
const long kExpectedTotal = 7293;      // 文件总数

// 代表性封装族目录（覆盖常见元件族，全集由配方 build() 摘要覆盖）
const char* kSpotDirs[] = {
    "Button_Switch_SMD.3dshapes", "Capacitor_SMD.3dshapes",
    "Connector_PinHeader_2.54mm.3dshapes", "Connector_USB.3dshapes",
    "Crystal.3dshapes", "Diode_SMD.3dshapes", "Inductor_SMD.3dshapes",
    "LED_SMD.3dshapes", "Package_BGA.3dshapes", "Package_DFN_QFN.3dshapes",
    "Package_QFP.3dshapes", "Package_SO.3dshapes",
    "Package_TO_SOT_SMD.3dshapes", "Resistor_SMD.3dshapes",
    "TerminalBlock_Phoenix.3dshapes",
};
const size_t kSpotDirCount = sizeof(kSpotDirs) / sizeof(kSpotDirs[0]);

bool ends_with(const std::string& value, const std::string& suffix) {
    return value.size() >= suffix.size() &&
           value.compare(value.size() - suffix.size(), suffix.size(), suffix) == 0;
}

bool is_regular_file(const std::string& path) {
    struct stat info {};
    return ::stat(path.c_str(), &info) == 0 && S_ISREG(info.st_mode);
}

bool is_dir(const std::string& path) {
    struct stat info {};
    return ::stat(path.c_str(), &info) == 0 && S_ISDIR(info.st_mode);
}

std::vector<std::string> list_dir(const std::string& root) {
    std::vector<std::string> names;
    DIR* dir = ::opendir(root.c_str());
    if (!dir) throw std::runtime_error("cannot open directory: " + root);
    while (dirent* entry = ::readdir(dir)) {
        const std::string name(entry->d_name);
        if (name == "." || name == "..") continue;
        names.push_back(name);
    }
    ::closedir(dir);
    return names;
}

// 读文件头/尾窗口（字节安全，短文件读全文）。
// 尾窗口用 seekg 定位读取末尾 window 字节，避免读整个文件
// （7245 个 .step 共约 3.4 GB，全量读取会显著拖慢探针）。
std::string read_window(const std::string& path, bool head, size_t window) {
    std::ifstream stream(path.c_str(), std::ios::binary);
    if (!stream) throw std::runtime_error("cannot read file: " + path);
    std::string out;
    if (head) {
        out.resize(window);
        stream.read(&out[0], static_cast<std::streamsize>(window));
        out.resize(static_cast<size_t>(stream.gcount()));
    } else {
        stream.seekg(0, std::ios::end);
        const std::streamoff size = stream.tellg();
        const size_t count =
            size > static_cast<std::streamoff>(window) ? window
                                                       : static_cast<size_t>(size);
        stream.seekg(size - static_cast<std::streamoff>(count), std::ios::beg);
        out.resize(count);
        stream.read(&out[0], static_cast<std::streamsize>(count));
        out.resize(static_cast<size_t>(stream.gcount()));
    }
    return out;
}

// STEP（ISO 10303-21）结构校验：文件头必须以前缀 "ISO-10303-21;" 开头
// （不能用子串查找——尾部 "END-ISO-10303-21;" 本身包含该子串，
// 缺头截断文件会被误收），且尾窗口含 "END-ISO-10303-21;"
void validate_step(const std::string& path) {
    const std::string head = read_window(path, true, 512);
    if (head.compare(0, 13, "ISO-10303-21;") != 0)
        throw std::runtime_error("missing ISO-10303-21 header in " + path);
    const std::string tail = read_window(path, false, 512);
    if (tail.find("END-ISO-10303-21;") == std::string::npos)
        throw std::runtime_error("missing END-ISO-10303-21 footer in " + path);
}

}  // namespace

int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr << "usage: kicad_packages3d_probe <kicad-3dmodels-root>\n";
        return 2;
    }
    const std::string models_root = argv[1];

    try {
        // 1) 资源根目录必须存在且为目录
        if (!is_dir(models_root))
            throw std::runtime_error("3dmodels resource root is not a directory: " +
                                     models_root);

        // 2) 目录集合与计数（与配方 build() 防漂移校验同口径）
        std::vector<std::string> dirs;
        long step = 0, aux = 0, total = 0;
        for (const std::string& name : list_dir(models_root)) {
            const std::string path = models_root + "/" + name;
            if (!is_dir(path) || !ends_with(name, ".3dshapes"))
                throw std::runtime_error("unexpected entry at models root: " + name);
            dirs.push_back(name);
            const std::vector<std::string> entries = list_dir(path);
            if (entries.empty())
                throw std::runtime_error("empty model directory: " + name);
            for (const std::string& entry : entries) {
                // 上游家族目录内全部为普通文件（无嵌套目录）
                if (!is_regular_file(path + "/" + entry))
                    throw std::runtime_error("unexpected entry type: " +
                                             path + "/" + entry);
                ++total;
                if (ends_with(entry, ".step")) ++step;
                else ++aux;
            }
        }
        if (static_cast<long>(dirs.size()) != kExpectedDirCount)
            throw std::runtime_error("dir count " +
                                     std::to_string(dirs.size()) + " != " +
                                     std::to_string(kExpectedDirCount));
        if (step != kExpectedStepCount)
            throw std::runtime_error(".step count " + std::to_string(step) +
                                     " != " + std::to_string(kExpectedStepCount));
        if (aux != kExpectedAuxCount)
            throw std::runtime_error("aux file count " + std::to_string(aux) +
                                     " != " + std::to_string(kExpectedAuxCount));
        if (total != kExpectedTotal)
            throw std::runtime_error("total file count " + std::to_string(total) +
                                     " != " + std::to_string(kExpectedTotal));

        // 3) 代表性封装族目录在位
        for (size_t i = 0; i < kSpotDirCount; ++i) {
            const std::string path = models_root + "/" + kSpotDirs[i];
            if (!is_dir(path))
                throw std::runtime_error(std::string("missing spot dir: ") + kSpotDirs[i]);
        }

        // 4) 全量消费：逐个校验 .step 的 ISO-10303-21 头/尾结构
        long checked = 0;
        for (const std::string& name : dirs) {
            const std::string path = models_root + "/" + name;
            for (const std::string& entry : list_dir(path)) {
                if (ends_with(entry, ".step")) {
                    validate_step(path + "/" + entry);
                    ++checked;
                }
            }
        }
        if (checked != kExpectedStepCount)
            throw std::runtime_error("validated " + std::to_string(checked) +
                                     " != " + std::to_string(kExpectedStepCount));

        // 5) 负向校验：截断文件必须被校验器拒绝
        const char* tmpdir = ::getenv("TMPDIR");
        std::string truncated = tmpdir && *tmpdir ? std::string(tmpdir) : std::string(".");
        if (!truncated.empty() && truncated.back() != '/') truncated += '/';
        // (a) 缺 END-ISO-10303-21 尾
        const std::string no_footer = truncated + "kicad_truncated_probe_no_footer.step";
        {
            std::ofstream out(no_footer.c_str(), std::ios::binary | std::ios::trunc);
            out << "ISO-10303-21;\nHEADER;\nENDSEC;\n";
        }
        bool rejected = false;
        try {
            validate_step(no_footer);
        } catch (const std::exception&) {
            rejected = true;
        }
        if (!rejected) throw std::runtime_error("step missing footer was not rejected");
        // (b) 缺 ISO-10303-21 头
        const std::string no_header = truncated + "kicad_truncated_probe_no_header.step";
        {
            std::ofstream out(no_header.c_str(), std::ios::binary | std::ios::trunc);
            out << "HEADER;\nDATA;\nENDSEC;\nEND-ISO-10303-21;\n";
        }
        rejected = false;
        try {
            validate_step(no_header);
        } catch (const std::exception&) {
            rejected = true;
        }
        if (!rejected) throw std::runtime_error("step missing header was not rejected");
        ::unlink(no_footer.c_str());
        ::unlink(no_header.c_str());

        std::cout << "kicad_packages3d_probe: " << dirs.size() << " model dirs, "
                  << step << " .step validated OK\n";
        return 0;
    } catch (const std::exception& err) {
        std::cerr << "kicad_packages3d_probe FAILED: " << err.what() << "\n";
        return 1;
    }
}
