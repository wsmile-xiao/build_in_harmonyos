/*
   ohos_test.cpp — HarmonyOS 专项测试 for ktextaddons 2.0.2

   该测试只验证与 HarmonyOS (aarch64-linux-ohos) 平台适配直接相关的真实产物行为，
   区别于上游 ctest 与消费者 test.cpp（real API 冒烟）：

   1) OHOS soname 适配：CMake 没有 Platform/HarmonyOS 模块，`CMAKE_SHARED_LIBRARY_
      SONAME_*` 旗标必须由配方显式恢复（archives/k/ktextaddons/2.0.2/conanfile.py
      generate()）。否则安装出的 .so 不带 DT_SONAME，消费者会把构建目录相对路径
      写进 DT_NEEDED，musl 加载器解析含斜杠的 DT_NEEDED 时按进程 CWD 查找而失败。
      本测试解析每个已安装共享库的 ELF64 .dynamic 段，断言 DT_SONAME 存在且为纯
      文件名（不含 '/'）。

   2) KDE 插件安装布局：上游 TranslatorEngineLoader 按 libraryPaths()+"/kf6/translator/"
      扫描翻译引擎插件；断言安装前缀内确实存在 kf6/translator 目录及其插件。

   3) OHOS Qt Widgets 运行链路：offscreen 平台下构造真实 QWidget（SlideContainer），
      驱动 setContent/slideHeight，验证 OHOS 上的 Qt 事件/布局链路。

   KTEXTADDONS_PREFIX 由 test_package/conanfile.py 的 test() 注入（= 被测包安装前缀）。
*/
#include <QApplication>
#include <QDir>
#include <QString>
#include <QStringList>

#include <TextAddonsWidgets/SlideContainer>

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <string>
#include <vector>

namespace
{
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

// 提取 ELF64 共享库的 DT_SONAME（空字符串代表不存在或不可解析）。
std::string sonameOf(const std::string &path, bool *parsed)
{
    *parsed = false;
    std::vector<char> buffer;
    if (!readFile(path, buffer)) {
        return {};
    }
    if (buffer.size() < sizeof(Elf64Ehdr) || std::memcmp(buffer.data(), "\177ELF", 4) != 0) {
        return {};
    }
    Elf64Ehdr header;
    std::memcpy(&header, buffer.data(), sizeof(header));
    if (header.e_ident[4] != 2 /*ELFCLASS64*/ || header.e_shentsize != sizeof(Elf64Shdr)) {
        return {};
    }
    const std::size_t sectionsEnd = static_cast<std::size_t>(header.e_shoff) + static_cast<std::size_t>(header.e_shnum) * sizeof(Elf64Shdr);
    if (sectionsEnd > buffer.size()) {
        return {};
    }
    std::vector<Elf64Shdr> sections(header.e_shnum);
    std::memcpy(sections.data(), buffer.data() + header.e_shoff, sections.size() * sizeof(Elf64Shdr));

    // section 名字表
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
        return {};
    }
    std::vector<char> strtab(buffer.data() + dynstr->sh_offset, buffer.data() + dynstr->sh_offset + dynstr->sh_size);
    const std::size_t entries = static_cast<std::size_t>(dynamic->sh_size / sizeof(Elf64Dyn));
    for (std::size_t i = 0; i < entries; ++i) {
        Elf64Dyn entry;
        std::memcpy(&entry, buffer.data() + dynamic->sh_offset + i * sizeof(Elf64Dyn), sizeof(entry));
        if (entry.d_tag != kDtSoname) {
            continue;
        }
        if (entry.d_val >= strtab.size()) {
            return {};
        }
        *parsed = true;
        return std::string(strtab.data() + entry.d_val);
    }
    return {};
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
        // 跳过 soname/developer 符号链接，只检查真实文件
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

// 在安装前缀中查找 kf6/<component> 插件目录（ECM KDEInstallDirs 布局），
// 返回其中第一个目录路径，找不到返回空字符串。
QString findPluginDir(const QString &root, const QString &component)
{
    QDir dir(root);
    const QFileInfoList entries = dir.entryInfoList(QDir::Dirs | QDir::NoDotAndDotDot, QDir::Name);
    for (const QFileInfo &entry : entries) {
        if (entry.fileName() == QLatin1String("kf6")) {
            const QString candidate = entry.absoluteFilePath() + QLatin1Char('/') + component;
            if (QDir(candidate).exists()) {
                return candidate;
            }
        }
        const QString nested = findPluginDir(entry.absoluteFilePath(), component);
        if (!nested.isEmpty()) {
            return nested;
        }
    }
    return QString();
}

std::vector<std::string> expectedLibraries()
{
    return {
        "libKF6TextAddonsWidgets.so",
        "libKF6TextAutoCorrectionCore.so",
        "libKF6TextAutoCorrectionWidgets.so",
        "libKF6TextEmoticonsCore.so",
        "libKF6TextEmoticonsWidgets.so",
        "libKF6TextTranslator.so",
        "libKF6TextGrammarCheck.so",
        "libKF6TextUtils.so",
        "libKF6TextCustomEditor.so",
        "libKF6TextAutoGenerateText.so",
        "libKF6TextSpeechToText.so",
        "libKF6TextEditTextToSpeech.so",
    };
}
} // namespace

int main(int argc, char **argv)
{
    QApplication app(argc, argv);
    int failures = 0;

    const char *prefixEnv = std::getenv("KTEXTADDONS_PREFIX");
    if (!prefixEnv || *prefixEnv == '\0') {
        std::printf("FAIL KTEXTADDONS_PREFIX is not set (test_package must export it)\n");
        return 1;
    }
    const QString prefix = QString::fromLocal8Bit(prefixEnv);
    const QString libDir = prefix + QLatin1String("/lib");
    if (!QDir(libDir).exists()) {
        std::printf("FAIL installed lib dir missing: %s\n", qPrintable(libDir));
        return 1;
    }

    // --- 1) DT_SONAME：OHOS 平台 soname 旗标适配 ---------------------------
    {
        const std::vector<std::string> libraries = collectSharedObjects(libDir);
        int checked = 0;
        int sonameOk = 0;
        for (const std::string &library : libraries) {
            bool parsed = false;
            const std::string soname = sonameOf(library, &parsed);
            ++checked;
            if (!parsed || soname.empty()) {
                std::printf("FAIL no DT_SONAME in %s\n", library.c_str());
                ++failures;
                continue;
            }
            if (soname.find('/') != std::string::npos) {
                std::printf("FAIL DT_SONAME with path separator in %s: %s\n", library.c_str(), soname.c_str());
                ++failures;
                continue;
            }
            ++sonameOk;
        }
        std::printf("%s DT_SONAME check: %d/%d installed shared objects carry a plain DT_SONAME\n", sonameOk == checked ? "PASS" : "FAIL", sonameOk, checked);
    }

    // --- 1b) 产物完整性：12 个组件库均安装 -------------------------------
    {
        const QStringList files = QDir(libDir).entryList(QStringList() << QLatin1String("lib*.so*"), QDir::Files);
        for (const std::string &expected : expectedLibraries()) {
            bool found = false;
            for (const QString &file : files) {
                if (file.startsWith(QString::fromStdString(expected))) {
                    found = true;
                    break;
                }
            }
            if (!found) {
                std::printf("FAIL installed library missing: %s\n", expected.c_str());
                ++failures;
            }
        }
        std::printf("PASS installed library set (12 components)\n");
    }

    // --- 2) KDE 插件安装布局 ---------------------------------------------
    {
        const QString translatorDir = findPluginDir(prefix, QLatin1String("translator"));
        if (translatorDir.isEmpty()) {
            std::printf("FAIL kf6/translator plugin directory not installed under %s\n", qPrintable(prefix));
            ++failures;
        } else {
            const QStringList plugins = QDir(translatorDir).entryList(QStringList() << QLatin1String("*.so"), QDir::Files);
            if (plugins.isEmpty()) {
                std::printf("FAIL kf6/translator is empty: %s\n", qPrintable(translatorDir));
                ++failures;
            } else {
                std::printf("PASS kf6/translator plugin directory: %d plugin(s) in %s\n", int(plugins.size()), qPrintable(translatorDir));
            }
        }
    }

    // --- 3) OHOS Qt Widgets 运行链路 --------------------------------------
    {
        QWidget host;
        TextAddonsWidgets::SlideContainer container(&host);
        QWidget content(&container);
        container.setContent(&content);
        if (container.content() != &content) {
            std::printf("FAIL SlideContainer::content round-trip\n");
            ++failures;
        }
        container.setSlideHeight(container.slideHeight());
        app.processEvents();
        std::printf("PASS OHOS Qt Widgets runtime (SlideContainer, platform=%s)\n", qPrintable(app.platformName()));
    }

    if (failures == 0) {
        std::printf("OHOS TEST ALL PASS\n");
        return 0;
    }
    std::printf("OHOS TEST %d FAILURE(S)\n", failures);
    return 1;
}
