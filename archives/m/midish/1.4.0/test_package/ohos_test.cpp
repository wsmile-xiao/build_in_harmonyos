/*
   ohos_test.cpp — HarmonyOS 专项测试 for midish 1.4.0

   只验证与 HarmonyOS (aarch64-linux-ohos) 平台适配直接相关的安装产物行为：

   1) 平台适配核心（补丁 0001）：本平台的管道在到达 end-of-file 时 poll() 只
      报告 POLLHUP（不报告 POLLIN，实测 revents=0x10）。上游非 tty stdin 分支
      只认 POLLIN，解释器因此永远看不到 EOF，会一直空转不退（上游回归套件与
      所有批处理脚本都会挂住）。本测试 fork+exec 已安装的 midish，把一个脚本
      通过管道喂进去后关闭写端，断言进程在超时内以退出码 0 结束。

   2) 安装产物：bin/midish 为合法 ELF64 且 DT_NEEDED 不含任何含 '/' 的路径
      （可重定位）；bin/smfplay、bin/smfrec 为可执行脚本且 shebang 为 /bin/sh。

   3) 安装布局：示例歌曲/rc 文件、文档与 man page 就位（供使用者按上游说明
      直接运行）。

   MIDISH_PREFIX 由 test_package/conanfile.py 的 test() 注入（= 被测包安装前缀）。
*/
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <string>
#include <vector>

#include <fcntl.h>
#include <signal.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

namespace
{
constexpr std::uint32_t kDtNeeded = 1;

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

bool isRegular(const std::string &path)
{
    struct stat info;
    return stat(path.c_str(), &info) == 0 && S_ISREG(info.st_mode);
}

std::string readHead(const std::string &path, std::size_t count)
{
    std::ifstream stream(path, std::ios::binary);
    if (!stream) {
        return std::string();
    }
    std::string data(count, '\0');
    stream.read(&data[0], static_cast<std::streamsize>(count));
    data.resize(static_cast<std::size_t>(stream.gcount()));
    return data;
}

bool elfNeededIsRelocatable(const std::string &path, std::string *offender)
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
    std::vector<char> buffer(static_cast<std::size_t>(size));
    stream.seekg(0, std::ios::beg);
    stream.read(buffer.data(), size);
    if (buffer.size() < sizeof(Elf64Ehdr) || std::memcmp(buffer.data(), "\177ELF", 4) != 0) {
        return false;
    }
    Elf64Ehdr header;
    std::memcpy(&header, buffer.data(), sizeof(header));
    if (header.e_ident[4] != 2 || header.e_shentsize != sizeof(Elf64Shdr)) {
        return false;
    }
    std::vector<Elf64Shdr> sections(header.e_shnum);
    if (static_cast<std::size_t>(header.e_shoff) + sections.size() * sizeof(Elf64Shdr) > buffer.size()) {
        return false;
    }
    std::memcpy(sections.data(), buffer.data() + header.e_shoff, sections.size() * sizeof(Elf64Shdr));
    std::vector<char> names;
    if (header.e_shstrndx < sections.size()) {
        const Elf64Shdr &strtab = sections[header.e_shstrndx];
        names.assign(buffer.data() + strtab.sh_offset, buffer.data() + strtab.sh_offset + strtab.sh_size);
    }
    auto sectionName = [&names](const Elf64Shdr &section) {
        if (section.sh_name >= names.size()) {
            return std::string();
        }
        return std::string(names.data() + section.sh_name);
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
    if (!dynamic || !dynstr) {
        return true; // statically linked: nothing to relocate
    }
    const std::string strings(buffer.data() + dynstr->sh_offset, static_cast<std::size_t>(dynstr->sh_size));
    for (std::size_t i = 0; i < static_cast<std::size_t>(dynamic->sh_size / sizeof(Elf64Dyn)); ++i) {
        Elf64Dyn entry;
        std::memcpy(&entry, buffer.data() + dynamic->sh_offset + i * sizeof(Elf64Dyn), sizeof(entry));
        if (entry.d_tag != kDtNeeded || entry.d_val >= strings.size()) {
            continue;
        }
        const std::string name = strings.substr(entry.d_val, strings.find('\0', entry.d_val) - entry.d_val);
        if (name.find('/') != std::string::npos) {
            *offender = name;
            return false;
        }
    }
    return true;
}

/* 1) 管道 EOF（仅 POLLHUP）必须让 midish 退出。 */
bool midishExitsOnPipeEof(const std::string &midish, int timeoutTenths, int *exitCode)
{
    int fds[2];
    if (pipe(fds) != 0) {
        return false;
    }
    const pid_t pid = fork();
    if (pid < 0) {
        close(fds[0]);
        close(fds[1]);
        return false;
    }
    if (pid == 0) {
        if (dup2(fds[0], STDIN_FILENO) < 0) {
            _exit(126);
        }
        close(fds[0]);
        close(fds[1]);
        const int dev = open("/dev/null", O_WRONLY);
        if (dev >= 0) {
            dup2(dev, STDOUT_FILENO);
            dup2(dev, STDERR_FILENO);
            close(dev);
        }
        execl(midish.c_str(), "midish", "-b", static_cast<char *>(NULL));
        _exit(127);
    }
    close(fds[0]);
    const char script[] = "version\n";
    const ssize_t written = write(fds[1], script, sizeof(script) - 1);
    if (written != static_cast<ssize_t>(sizeof(script) - 1)) {
        close(fds[1]);
        kill(pid, SIGKILL);
        waitpid(pid, nullptr, 0);
        return false;
    }
    close(fds[1]); /* end-of-file for the child */

    for (int i = 0; i < timeoutTenths; ++i) {
        int status = 0;
        const pid_t result = waitpid(pid, &status, WNOHANG);
        if (result == pid) {
            if (WIFEXITED(status)) {
                *exitCode = WEXITSTATUS(status);
                return *exitCode == 0;
            }
            *exitCode = -1;
            return false;
        }
        struct timespec delay = {0, 100000000L};
        nanosleep(&delay, nullptr);
    }
    kill(pid, SIGKILL);
    waitpid(pid, nullptr, 0);
    *exitCode = -2; /* never terminated */
    return false;
}
} // namespace

int main()
{
    const char *prefixEnv = std::getenv("MIDISH_PREFIX");
    if (prefixEnv == nullptr || *prefixEnv == '\0') {
        std::printf("FAIL MIDISH_PREFIX is not set (test_package must export it)\n");
        return 1;
    }
    const std::string prefix(prefixEnv);
    const std::string midish = prefix + "/bin/midish";

    // --- 1) 平台适配核心：管道 EOF 退出 -----------------------------------
    {
        int exitCode = -3;
        const bool ok = midishExitsOnPipeEof(midish, 150, &exitCode);
        if (!ok) {
            std::printf("FAIL midish did not terminate on pipe end-of-file (exit=%d)\n", exitCode);
            ++failures;
        } else {
            std::printf("PASS midish exits with code 0 on pipe end-of-file (POLLHUP-only EOF handled)\n");
        }
    }

    // --- 2) 安装产物：可重定位的 ELF64 与 shell 前端 -----------------------
    {
        check(isRegular(midish), "installed binary bin/midish");
        std::string offender;
        check(elfNeededIsRelocatable(midish, &offender),
              "bin/midish DT_NEEDED has no path separator");
        if (!offender.empty()) {
            std::printf("     offending NEEDED entry: %s\n", offender.c_str());
        }
        for (const char *frontend : {"smfplay", "smfrec"}) {
            const std::string path = prefix + "/bin/" + frontend;
            const bool regular = isRegular(path);
            bool executable = false;
            struct stat info;
            if (regular && stat(path.c_str(), &info) == 0) {
                executable = (info.st_mode & S_IXUSR) != 0;
            }
            const std::string head = readHead(path, 9);
            check(regular && executable, (std::string("installed shell front-end bin/") + frontend).c_str());
            check(head == "#!/bin/sh", (std::string("bin/") + frontend + " is a /bin/sh script").c_str());
        }
    }

    // --- 3) 安装布局：示例、文档与 man page -------------------------------
    {
        const char *files[] = {
            "/share/examples/midish/sample.msh",
            "/share/examples/midish/midishrc",
            "/share/doc/midish/manual.html",
            "/share/doc/midish/README",
            "/share/man/man1/midish.1",
            "/share/man/man1/smfplay.1",
            "/share/man/man1/smfrec.1",
        };
        for (const char *relative : files) {
            const std::string path = prefix + relative;
            if (!isRegular(path)) {
                std::printf("FAIL missing installed file %s\n", relative);
                ++failures;
            }
        }
        std::printf("PASS installed examples, documentation and man pages\n");
    }

    if (failures == 0) {
        std::printf("OHOS TEST ALL PASS\n");
        return 0;
    }
    std::printf("OHOS TEST %d FAILURE(S)\n", failures);
    return 1;
}
