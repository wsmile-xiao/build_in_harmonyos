/*
   ohos_test.cpp — HarmonyOS 专项测试 for qmmp 2.3.2

   只验证与 HarmonyOS (aarch64-linux-ohos) 平台适配直接相关的安装产物行为，
   区别于消费者 test.cpp（real API 冒烟）：

   1) OHOS soname 适配：CMake 没有 Platform/HarmonyOS 模块，配方的 generate()
      显式恢复 `CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG/C_FLAG`。断言 libqmmp /
      libqmmpui 这两个共享库带 DT_SONAME 且为纯文件名（消费者据此记录
      DT_NEEDED；缺失时链接器会写入构建目录路径，musl 按进程 CWD 解析含斜杠
      的 DT_NEEDED 会加载失败）。
   2) 插件为 MODULE（dlopen 加载，CMake 不设 SONAME）：断言每个插件都是合法
      ELF64，且其 DT_NEEDED 不含任何含 '/' 的路径。链接缺 DT_SONAME 的依赖库
      时链接器会写入打开时的绝对路径（libvorbisfile/libsoxr/libQt6Multimedia
      等已发布包即如此），配方的 package() 会把这些条目就地缩短为纯文件名，
      使插件可重定位。
   3) 插件目录布局：qmmp 按 <plugin path>/<Category>/<name>.so 扫描，断言 10 个
      类别目录齐备，并断言本适配启用的解码器集合与输出插件均已安装。
   4) 应用产物：断言安装包内 bin/qmmp 存在且可执行。
   5) OHOS Qt Widgets 运行链路：offscreen 平台下真实创建 QWidget 并处理一次
      事件循环，验证 Qt 事件/布局/插件加载链路在 OHOS 上可用。

   QMMP_PREFIX 由 test_package/conanfile.py 的 test() 注入（= 被测包安装前缀）。
*/
#include <QApplication>
#include <QDir>
#include <QFileInfo>
#include <QString>
#include <QStringList>
#include <QWidget>

#include <qmmp/qmmp.h>

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <string>
#include <vector>

namespace
{
constexpr std::uint32_t kDtNeeded = 1;
constexpr std::uint32_t kDtSoname = 14;

struct Elf64Ehdr {
    unsigned char e_ident[16];
    std::uint16_t e_type;
    std::uint16_t e_machine;
    std::uint32_t e_version;
    std::uint64_t e_entry;
    std::uint64_t e_phoff;
    std::uint64_t e_shoff;
    std::uint32_t e_flags;
    std::uint16_t e_ehsize;
    std::uint16_t e_phentsize;
    std::uint16_t e_phnum;
    std::uint16_t e_shentsize;
    std::uint16_t e_shnum;
    std::uint16_t e_shstrndx;
};

struct Elf64Shdr {
    std::uint32_t sh_name;
    std::uint32_t sh_type;
    std::uint64_t sh_flags;
    std::uint64_t sh_addr;
    std::uint64_t sh_offset;
    std::uint64_t sh_size;
    std::uint32_t sh_link;
    std::uint32_t sh_info;
    std::uint64_t sh_addralign;
    std::uint64_t sh_entsize;
};

struct Elf64Dyn {
    std::int64_t d_tag;
    std::uint64_t d_val;
};

struct ElfFacts {
    bool valid = false;
    std::string soname;
    std::vector<std::string> slashedNeeded;
};

int failures = 0;

void check(bool condition, const char *what)
{
    if (condition) {
        std::printf("PASS %s\n", what);
    } else {
        std::printf("FAIL %s\n", what);
        ++failures;
    }
}

bool readFile(const std::string &path, std::vector<char> &buffer)
{
    std::ifstream stream(path, std::ios::binary);
    if (!stream) {
        return false;
    }
    stream.seekg(0, std::ios::end);
    const std::streamoff size = stream.tellg();
    if (size <= 0) {
        return false;
    }
    buffer.resize(static_cast<std::size_t>(size));
    stream.seekg(0, std::ios::beg);
    stream.read(buffer.data(), size);
    return static_cast<bool>(stream);
}

ElfFacts elfFacts(const std::string &path)
{
    ElfFacts facts;
    std::vector<char> buffer;
    if (!readFile(path, buffer)) {
        return facts;
    }
    if (buffer.size() < sizeof(Elf64Ehdr) || std::memcmp(buffer.data(), "\177ELF", 4) != 0) {
        return facts;
    }
    Elf64Ehdr header;
    std::memcpy(&header, buffer.data(), sizeof(header));
    if (header.e_ident[4] != 2 /*ELFCLASS64*/ || header.e_shentsize != sizeof(Elf64Shdr)) {
        return facts;
    }
    const std::size_t sectionsEnd =
        static_cast<std::size_t>(header.e_shoff) + static_cast<std::size_t>(header.e_shnum) * sizeof(Elf64Shdr);
    if (sectionsEnd > buffer.size()) {
        return facts;
    }
    std::vector<Elf64Shdr> sections(header.e_shnum);
    std::memcpy(sections.data(), buffer.data() + header.e_shoff, sections.size() * sizeof(Elf64Shdr));

    std::vector<char> sectionNames;
    if (header.e_shstrndx < sections.size()) {
        const Elf64Shdr &strtab = sections[header.e_shstrndx];
        if (strtab.sh_offset + strtab.sh_size <= buffer.size()) {
            sectionNames.assign(buffer.data() + strtab.sh_offset, buffer.data() + strtab.sh_offset + strtab.sh_size);
        }
    }
    auto sectionName = [&sectionNames](const Elf64Shdr &section) {
        if (section.sh_name >= sectionNames.size()) {
            return std::string();
        }
        return std::string(sectionNames.data() + section.sh_name);
    };

    const Elf64Shdr *dynamic = nullptr;
    const Elf64Shdr *dynstr = nullptr;
    for (const Elf64Shdr &section : sections) {
        const std::string name = sectionName(section);
        if (name == ".dynamic") {
            dynamic = &section;
        } else if (name == ".dynstr") {
            dynstr = &section;
        }
    }
    if (!dynamic || !dynstr || dynamic->sh_offset + dynamic->sh_size > buffer.size()) {
        return facts;
    }
    const std::string strtab(buffer.data() + dynstr->sh_offset, static_cast<std::size_t>(dynstr->sh_size));
    auto stringAt = [&strtab](std::uint64_t offset) {
        if (offset >= strtab.size()) {
            return std::string();
        }
        return strtab.substr(offset, strtab.find('\0', offset) - offset);
    };

    const std::size_t entries = static_cast<std::size_t>(dynamic->sh_size / sizeof(Elf64Dyn));
    for (std::size_t i = 0; i < entries; ++i) {
        Elf64Dyn entry;
        std::memcpy(&entry, buffer.data() + dynamic->sh_offset + i * sizeof(Elf64Dyn), sizeof(entry));
        if (entry.d_tag == kDtSoname) {
            facts.soname = stringAt(entry.d_val);
        } else if (entry.d_tag == kDtNeeded) {
            const std::string name = stringAt(entry.d_val);
            if (name.find('/') != std::string::npos) {
                facts.slashedNeeded.push_back(name);
            }
        }
    }
    facts.valid = true;
    return facts;
}

std::vector<std::string> collectSharedObjects(const QString &root)
{
    std::vector<std::string> result;
    QDir dir(root);
    const QFileInfoList entries = dir.entryInfoList(QDir::Files | QDir::Dirs | QDir::NoDotAndDotDot, QDir::Name);
    for (const QFileInfo &entry : entries) {
        if (entry.isDir()) {
            const std::vector<std::string> nested = collectSharedObjects(entry.absoluteFilePath());
            result.insert(result.end(), nested.begin(), nested.end());
            continue;
        }
        if (entry.isSymLink()) {
            continue;
        }
        const QString name = entry.fileName();
        if (name.startsWith(QLatin1String("lib")) && name.contains(QLatin1String(".so"))) {
            result.push_back(entry.absoluteFilePath().toStdString());
        }
    }
    return result;
}

QStringList pluginsIn(const QString &pluginDir, const QString &category)
{
    return QDir(pluginDir + QLatin1Char('/') + category)
        .entryList(QStringList() << QLatin1String("*.so"), QDir::Files);
}
} // namespace

int main(int argc, char **argv)
{
    QApplication app(argc, argv);

    const char *prefixEnv = std::getenv("QMMP_PREFIX");
    if (!prefixEnv || *prefixEnv == '\0') {
        std::printf("FAIL QMMP_PREFIX is not set (test_package must export it)\n");
        return 1;
    }
    const QString prefix = QString::fromLocal8Bit(prefixEnv);
    const QString pluginDir = prefix + QLatin1String("/lib/qmmp-2.3");
    if (!QDir(pluginDir).exists()) {
        std::printf("FAIL installed plugin dir missing: %s\n", qPrintable(pluginDir));
        return 1;
    }

    // --- 1) 共享库 DT_SONAME：OHOS soname 旗标适配 -------------------------
    {
        const QStringList coreNames = {
            QStringLiteral("libqmmp.so"),
            QStringLiteral("libqmmpui.so"),
        };
        for (const QString &name : coreNames) {
            // 跟随 soname 符号链接找到真实文件
            const QString real = QFileInfo(prefix + QLatin1String("/lib/") + name).canonicalFilePath();
            if (real.isEmpty()) {
                std::printf("FAIL missing shared library: %s\n", qPrintable(name));
                ++failures;
                continue;
            }
            const ElfFacts facts = elfFacts(real.toStdString());
            if (facts.soname.empty() || facts.soname.find('/') != std::string::npos) {
                std::printf("FAIL DT_SONAME missing or path-like in %s\n", qPrintable(name));
                ++failures;
            } else {
                std::printf("PASS DT_SONAME %s = %s\n", qPrintable(name), facts.soname.c_str());
            }
        }
    }

    // --- 2) 插件的 ELF 契约（无含斜杠的 DT_NEEDED） ------------------------
    {
        const std::vector<std::string> plugins = collectSharedObjects(pluginDir);
        int ok = 0;
        for (const std::string &plugin : plugins) {
            const ElfFacts facts = elfFacts(plugin);
            if (!facts.valid) {
                std::printf("FAIL not a valid ELF64 object: %s\n", plugin.c_str());
                ++failures;
                continue;
            }
            if (!facts.slashedNeeded.empty()) {
                std::printf("FAIL slash-containing DT_NEEDED '%s' in %s\n", facts.slashedNeeded.front().c_str(), plugin.c_str());
                ++failures;
                continue;
            }
            ++ok;
        }
        std::printf("     plugin ELF contract: %d/%d plugins\n", ok, int(plugins.size()));
        check(ok == int(plugins.size()) && ok >= 40, "every installed plugin is a relocatable ELF64 module");
    }

    // --- 3) 插件目录布局 --------------------------------------------------
    {
        const QStringList categories = {
            QStringLiteral("CommandLineOptions"),
            QStringLiteral("Effect"),
            QStringLiteral("FileDialogs"),
            QStringLiteral("General"),
            QStringLiteral("Input"),
            QStringLiteral("Output"),
            QStringLiteral("PlayListFormats"),
            QStringLiteral("Transports"),
            QStringLiteral("Ui"),
            QStringLiteral("Visual"),
        };
        int missing = 0;
        for (const QString &category : categories) {
            if (pluginsIn(pluginDir, category).isEmpty()) {
                std::printf("FAIL plugin category empty or missing: %s\n", qPrintable(category));
                ++missing;
            }
        }
        check(missing == 0, "all 10 plugin category directories installed");

        const QStringList expectedDecoders = {
            QStringLiteral("libmpeg.so"),
            QStringLiteral("libflac.so"),
            QStringLiteral("libvorbis.so"),
            QStringLiteral("libopus.so"),
            QStringLiteral("libsndfile.so"),
            QStringLiteral("libwavpack.so"),
            QStringLiteral("libwildmidi.so"),
            QStringLiteral("libarchive.so"),
            QStringLiteral("libcue.so"),
        };
        const QStringList installed = pluginsIn(pluginDir, QStringLiteral("Input"));
        for (const QString &decoder : expectedDecoders) {
            if (!installed.contains(decoder)) {
                std::printf("FAIL enabled decoder plugin missing: %s\n", qPrintable(decoder));
                ++failures;
            }
        }
        std::printf("     Input plugins installed: %d\n", int(installed.size()));

        const QStringList outputs = pluginsIn(pluginDir, QStringLiteral("Output"));
        if (!outputs.contains(QLatin1String("libqtmultimedia.so"))) {
            std::printf("FAIL Qt Multimedia output plugin missing\n");
            ++failures;
        }
        std::printf("     Output plugins installed: %d\n", int(outputs.size()));
        check(!outputs.isEmpty() && !installed.isEmpty(), "decoder/output plugin set installed");
    }

    // --- 4) 应用产物 ------------------------------------------------------
    {
        const QFileInfo info(prefix + QLatin1String("/bin/qmmp"));
        check(info.exists() && info.isExecutable(), "installed application binary bin/qmmp");
    }

    // --- 5) OHOS Qt Widgets 运行链路 --------------------------------------
    {
        QWidget widget;
        widget.setWindowTitle(QStringLiteral("qmmp ohos test"));
        widget.resize(200, 100);
        widget.show();
        app.processEvents();
        std::printf("     platform = %s, libqmmp version = %s\n", qPrintable(app.platformName()), qPrintable(Qmmp::strVersion()));
        check(app.platformName() == QLatin1String("offscreen"), "OHOS headless Qt platform (offscreen)");
    }

    if (failures == 0) {
        std::printf("OHOS TEST ALL PASS\n");
        return 0;
    }
    std::printf("OHOS TEST %d FAILURE(S)\n", failures);
    return 1;
}
