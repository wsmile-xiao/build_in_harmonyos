// test_package/test.cpp — consumer test for threadweaver5 5.116.0 on HarmonyOS PC.
//
// R34: links KF5::ThreadWeaver and actually drives the public API
//      (Job subclassing, JobPointer, Sequence, Collection, Queue::stream()
//      and the global stream()/enqueue()/make_job() queueing helpers,
//      QObjectDecorator signals, ResourceRestrictionPolicy) after the
//      pattern of the upstream autotests (autotests/AppendCharacterJob.h).
// R53: asserts the HarmonyOS adaptation path:
//      1. the loaded libKF5ThreadWeaver.so carries the OHOS-required
//         unversioned DT_SONAME `libKF5ThreadWeaver.so`
//         (CMAKE_PLATFORM_NO_VERSIONED_SONAME) and a DT_RUNPATH (E537:
//         CMAKE_BUILD_WITH_INSTALL_RPATH=ON, so the installed ELF is not
//         rewritten after linking and stays loadable);
//      2. the packaged ELF carries a .codesign section (re-signed with
//         binary-sign-tool after install, OHOS loader requirement).
#include <elf.h>

#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

#include <QCoreApplication>
#include <QEventLoop>
#include <QMutex>
#include <QMutexLocker>
#include <QObject>
#include <QString>
#include <QTimer>

#include <ThreadWeaver/Collection>
#include <ThreadWeaver/DebuggingAids>
#include <ThreadWeaver/Job>
#include <ThreadWeaver/JobPointer>
#include <ThreadWeaver/QObjectDecorator>
#include <ThreadWeaver/Queue>
#include <ThreadWeaver/Queueing>
#include <ThreadWeaver/ResourceRestrictionPolicy>
#include <ThreadWeaver/Sequence>
#include <ThreadWeaver/Thread>
#include <ThreadWeaver/ThreadWeaver>

// Injected by CMake ($<TARGET_FILE:KF5::ThreadWeaver>): the packaged .so path.
#ifndef THREADWEAVER_SO_PATH
#define THREADWEAVER_SO_PATH ""
#endif

using namespace ThreadWeaver;

namespace {

int g_pass = 0;
int g_fail = 0;

void check(bool ok, const char *what)
{
    if (ok) {
        ++g_pass;
        std::printf("ok - %s\n", what);
    } else {
        ++g_fail;
        std::printf("FAIL - %s\n", what);
    }
}

QMutex s_GlobalMutex;

// The upstream autotest job pattern (autotests/AppendCharacterJob.h):
// a Job that appends a character to a shared QString under a mutex.
class AppendCharacterJob : public Job
{
public:
    explicit AppendCharacterJob(QChar c, QString *stringref)
        : Job()
        , m_c(c)
        , m_stringref(stringref)
    {
    }

    void run(JobPointer, Thread *) override
    {
        QMutexLocker locker(&s_GlobalMutex);
        m_stringref->append(m_c);
    }

private:
    QChar m_c;
    QString *m_stringref;
};

class FailingAppendCharacterJob : public AppendCharacterJob
{
public:
    explicit FailingAppendCharacterJob(QChar c, QString *stringref)
        : AppendCharacterJob(c, stringref)
    {
    }

    void run(JobPointer job, Thread *thread) override
    {
        AppendCharacterJob::run(job, thread);
        setStatus(Job::Status_Failed);
    }
};

// Locate the file backing the loaded libKF5ThreadWeaver.so via
// /proc/self/maps.
std::string loaded_library_path(const char *needle)
{
    FILE *maps = std::fopen("/proc/self/maps", "r");
    if (!maps) {
        return std::string();
    }
    char line[8192];
    std::string path;
    while (std::fgets(line, sizeof(line), maps)) {
        if (!std::strstr(line, needle)) {
            continue;
        }
        const char *slash = std::strrchr(line, '/');
        if (slash) {
            path = slash;
            while (!path.empty() && (path.back() == '\n' || path.back() == '\r' || path.back() == ' ')) {
                path.pop_back();
            }
            break;
        }
    }
    std::fclose(maps);
    return path;
}

struct ElfDynamic {
    bool ok = false;
    std::string soname;
    bool has_runpath = false;
    bool has_rpath = false;
};

ElfDynamic read_dynamic(const std::string &path)
{
    ElfDynamic info;
    FILE *f = std::fopen(path.c_str(), "rb");
    if (!f) {
        return info;
    }
    Elf64_Ehdr eh;
    if (std::fread(&eh, sizeof(eh), 1, f) != 1 || std::memcmp(eh.e_ident, ELFMAG, SELFMAG) != 0
        || eh.e_ident[EI_CLASS] != ELFCLASS64) {
        std::fclose(f);
        return info;
    }
    struct Load {
        Elf64_Addr vaddr;
        Elf64_Off offset;
        Elf64_Xword filesz;
    };
    std::vector<Load> loads;
    Elf64_Phdr dyn_ph;
    bool have_dyn = false;
    for (int i = 0; i < eh.e_phnum; ++i) {
        if (std::fseek(f, static_cast<long>(eh.e_phoff + static_cast<Elf64_Off>(i) * eh.e_phentsize), SEEK_SET) != 0) {
            std::fclose(f);
            return info;
        }
        Elf64_Phdr ph;
        if (std::fread(&ph, sizeof(ph), 1, f) != 1) {
            std::fclose(f);
            return info;
        }
        if (ph.p_type == PT_LOAD) {
            loads.push_back({ph.p_vaddr, ph.p_offset, ph.p_filesz});
        } else if (ph.p_type == PT_DYNAMIC) {
            dyn_ph = ph;
            have_dyn = true;
        }
    }
    if (!have_dyn) {
        std::fclose(f);
        return info;
    }
    auto vaddr_to_off = [&loads](Elf64_Addr v) -> Elf64_Off {
        for (const Load &s : loads) {
            if (v >= s.vaddr && v < s.vaddr + s.filesz) {
                return s.offset + (v - s.vaddr);
            }
        }
        return 0;
    };
    if (dyn_ph.p_filesz == 0 || dyn_ph.p_filesz % sizeof(Elf64_Dyn) != 0) {
        std::fclose(f);
        return info;
    }
    std::vector<Elf64_Dyn> dyn(dyn_ph.p_filesz / sizeof(Elf64_Dyn));
    if (std::fseek(f, static_cast<long>(dyn_ph.p_offset), SEEK_SET) != 0
        || std::fread(dyn.data(), sizeof(Elf64_Dyn), dyn.size(), f) != dyn.size()) {
        std::fclose(f);
        return info;
    }
    std::fclose(f);
    info.ok = true;
    for (const Elf64_Dyn &entry : dyn) {
        if (entry.d_tag == DT_NULL) {
            break;
        }
        if (entry.d_tag == DT_SONAME) {
            // The string table offset resolution needs the section headers;
            // approximate through the phdr-mapped string table by scanning
            // is overkill here — the SONAME is checked from the file's
            // dynstr via the section table below.
        } else if (entry.d_tag == DT_RUNPATH) {
            info.has_runpath = true;
        } else if (entry.d_tag == DT_RPATH) {
            info.has_rpath = true;
        }
    }
    return info;
}

// Resolve DT_SONAME through the dynamic string table (readelf-style).
std::string read_soname(const std::string &path)
{
    FILE *f = std::fopen(path.c_str(), "rb");
    if (!f) {
        return std::string();
    }
    Elf64_Ehdr eh;
    if (std::fread(&eh, sizeof(eh), 1, f) != 1 || std::memcmp(eh.e_ident, ELFMAG, SELFMAG) != 0) {
        std::fclose(f);
        return std::string();
    }
    struct Load {
        Elf64_Addr vaddr;
        Elf64_Off offset;
        Elf64_Xword filesz;
    };
    std::vector<Load> loads;
    Elf64_Phdr dyn_ph;
    bool have_dyn = false;
    for (int i = 0; i < eh.e_phnum; ++i) {
        if (std::fseek(f, static_cast<long>(eh.e_phoff + static_cast<Elf64_Off>(i) * eh.e_phentsize), SEEK_SET) != 0) {
            std::fclose(f);
            return std::string();
        }
        Elf64_Phdr ph;
        if (std::fread(&ph, sizeof(ph), 1, f) != 1) {
            std::fclose(f);
            return std::string();
        }
        if (ph.p_type == PT_LOAD) {
            loads.push_back({ph.p_vaddr, ph.p_offset, ph.p_filesz});
        } else if (ph.p_type == PT_DYNAMIC) {
            dyn_ph = ph;
            have_dyn = true;
        }
    }
    if (!have_dyn) {
        std::fclose(f);
        return std::string();
    }
    auto vaddr_to_off = [&loads](Elf64_Addr v) -> Elf64_Off {
        for (const Load &s : loads) {
            if (v >= s.vaddr && v < s.vaddr + s.filesz) {
                return s.offset + (v - s.vaddr);
            }
        }
        return 0;
    };
    std::vector<Elf64_Dyn> dyn(dyn_ph.p_filesz / sizeof(Elf64_Dyn));
    if (std::fseek(f, static_cast<long>(dyn_ph.p_offset), SEEK_SET) != 0
        || std::fread(dyn.data(), sizeof(Elf64_Dyn), dyn.size(), f) != dyn.size()) {
        std::fclose(f);
        return std::string();
    }
    std::string soname;
    for (const Elf64_Dyn &entry : dyn) {
        if (entry.d_tag == DT_NULL) {
            break;
        }
        if (entry.d_tag == DT_STRTAB) {
            Elf64_Off stroff = vaddr_to_off(entry.d_un.d_ptr);
            for (const Elf64_Dyn &strsz_entry : dyn) {
                if (strsz_entry.d_tag == DT_STRSZ) {
                    std::vector<char> strtab(strsz_entry.d_un.d_val);
                    if (stroff != 0
                        && (std::fseek(f, static_cast<long>(stroff), SEEK_SET) == 0)
                        && std::fread(strtab.data(), 1, strtab.size(), f) == strtab.size()) {
                        for (const Elf64_Dyn &soname_entry : dyn) {
                            if (soname_entry.d_tag == DT_SONAME
                                && soname_entry.d_un.d_val < strtab.size()) {
                                soname = std::string(strtab.data() + soname_entry.d_un.d_val);
                                break;
                            }
                        }
                    }
                    break;
                }
            }
            break;
        }
    }
    std::fclose(f);
    return soname;
}

// Check the packaged ELF carries a .codesign section (binary-sign-tool
// re-signing, OHOS loader requirement).
bool has_codesign_section(const std::string &path)
{
    FILE *f = std::fopen(path.c_str(), "rb");
    if (!f) {
        return false;
    }
    Elf64_Ehdr eh;
    if (std::fread(&eh, sizeof(eh), 1, f) != 1 || std::memcmp(eh.e_ident, ELFMAG, SELFMAG) != 0) {
        std::fclose(f);
        return false;
    }
    bool found = false;
    for (int i = 0; i < eh.e_shnum; ++i) {
        if (std::fseek(f, static_cast<long>(eh.e_shoff + static_cast<Elf64_Off>(i) * eh.e_shentsize), SEEK_SET) != 0) {
            break;
        }
        Elf64_Shdr sh;
        if (std::fread(&sh, sizeof(sh), 1, f) != 1) {
            break;
        }
        if (sh.sh_type == SHT_PROGBITS && sh.sh_name > 0) {
            // Read the section name string table first.
            std::vector<char> names;
            if (std::fseek(f, static_cast<long>(eh.e_shoff + static_cast<Elf64_Off>(eh.e_shstrndx) * eh.e_shentsize), SEEK_SET) == 0) {
                Elf64_Shdr names_sh;
                if (std::fread(&names_sh, sizeof(names_sh), 1, f) == 1 && names_sh.sh_type != SHT_NOBITS) {
                    names.resize(names_sh.sh_size);
                    if (std::fseek(f, static_cast<long>(names_sh.sh_offset), SEEK_SET) == 0
                        && std::fread(names.data(), 1, names.size(), f) == names.size()
                        && sh.sh_name < names.size()
                        && std::strcmp(names.data() + sh.sh_name, ".codesign") == 0) {
                        found = true;
                        break;
                    }
                }
            }
        }
    }
    std::fclose(f);
    return found;
}

} // namespace

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    std::setvbuf(stdout, nullptr, _IONBF, 0);
    setDebugLevel(true, 1);

    // ── 1. Global queue basics: stream() + Job + finish(). ──────────────
    {
        QString result;
        AppendCharacterJob j1('a', &result);
        AppendCharacterJob j2('b', &result);
        JobPointer j3(new AppendCharacterJob('c', &result));
        stream() << j1 << j2 << j3;
        Queue::instance()->finish();
        check(result == QString::fromLatin1("abc"), "global stream() queues and executes jobs in order");
        check(Queue::instance()->isEmpty(), "Queue::isEmpty() after finish()");
    }

    // ── 2. Own Queue + Sequence ordering (upstream SequencesTests
    //      RecursiveStopTest pattern). ───────────────────────────────────
    {
        Queue queue;
        QString result;
        Sequence innerSequence;
        innerSequence << new AppendCharacterJob('b', &result) //
                      << new FailingAppendCharacterJob('c', &result) //
                      << new AppendCharacterJob('d', &result);
        Sequence outerSequence;
        outerSequence << new AppendCharacterJob('a', &result) //
                      << innerSequence //
                      << new AppendCharacterJob('e', &result);
        queue.stream() << outerSequence;
        queue.finish();
        check(result == QString::fromLatin1("abc"), "Sequence stops at the failed job (abc, not abcde)");
    }

    // ── 3. Collection: jobs run, order unspecified (upstream
    //      JobTests/QueueTests pattern). ─────────────────────────────────
    {
        Queue queue;
        QString result;
        Collection collection;
        collection << new AppendCharacterJob('x', &result) //
                   << new AppendCharacterJob('y', &result) //
                   << new AppendCharacterJob('z', &result);
        queue.stream() << collection;
        queue.finish();
        check(result.size() == 3 && result.contains('x') && result.contains('y') && result.contains('z'),
              "Collection executes all jobs regardless of order");
    }

    // ── 4. make_job() lambda + enqueue() to the global queue. ───────────
    {
        QString result;
        QMutex mutex;
        const JobPointer job = make_job([&result, &mutex]() {
            QMutexLocker locker(&mutex);
            result += QString::fromLatin1("L");
        });
        enqueue(job);
        Queue::instance()->finish();
        check(result == QString::fromLatin1("L"), "make_job() lambda enqueued through the global queue runs");
    }

    // ── 5. QObjectDecorator signals (started/done/failed). ──────────────
    {
        Queue queue;
        QString result;
        AppendCharacterJob *raw = new AppendCharacterJob('q', &result);
        QObjectDecorator *decorator = new QObjectDecorator(raw, true);
        int startedCount = 0;
        int doneCount = 0;
        QObject::connect(decorator, &QObjectDecorator::started, [&startedCount](JobPointer) {
            ++startedCount;
        });
        QObject::connect(decorator, &QObjectDecorator::done, [&doneCount](JobPointer) {
            ++doneCount;
        });
        queue.stream() << JobPointer(decorator);
        queue.finish();
        // The started/done signals are emitted from the worker threads and
        // delivered to this thread as queued connections; flush them before
        // counting.
        QCoreApplication::processEvents();
        QCoreApplication::processEvents();
        check(startedCount == 1, "QObjectDecorator::started emitted once");
        check(doneCount == 1, "QObjectDecorator::done emitted once");
        check(result == QString::fromLatin1("q"), "decorated job executed");
    }

    // ── 6. ResourceRestrictionPolicy caps concurrency. ──────────────────
    {
        Queue queue;
        QString result;
        ResourceRestrictionPolicy restriction(1);
        AppendCharacterJob first('1', &result);
        AppendCharacterJob second('2', &result);
        first.assignQueuePolicy(&restriction);
        second.assignQueuePolicy(&restriction);
        queue.setMaximumNumberOfThreads(4);
        queue.stream() << first << second;
        queue.finish();
        check(result.size() == 2, "ResourceRestrictionPolicy(1) jobs both complete under the cap");
    }

    // ── 7. Job status transitions. ──────────────────────────────────────
    {
        Queue queue;
        QString result;
        AppendCharacterJob job('s', &result);
        check(job.status() == Job::Status_New, "fresh Job reports Status_New");
        queue.stream() << job;
        queue.finish();
        check(job.status() == Job::Status_Success, "completed Job reports Status_Success");
        FailingAppendCharacterJob failing('f', &result);
        queue.stream() << failing;
        queue.finish();
        check(failing.status() == Job::Status_Failed, "job calling setStatus(Status_Failed) reports Status_Failed");
    }

    // ── R53 (1): OHOS ELF adaptation of the packaged library. ────────────
    std::string libPath = THREADWEAVER_SO_PATH;
    if (libPath.empty() || std::fopen(libPath.c_str(), "rb") == nullptr) {
        libPath = loaded_library_path("libKF5ThreadWeaver.so");
    }
    check(!libPath.empty(), "HarmonyOS: libKF5ThreadWeaver.so is mapped into the process");
    const ElfDynamic dyn = read_dynamic(libPath);
    const std::string soname = read_soname(libPath);
    std::printf("info - libKF5ThreadWeaver.so = %s\n", libPath.c_str());
    std::printf("info - DT_SONAME = %s (RUNPATH=%d RPATH=%d)\n",
                soname.c_str(), int(dyn.has_runpath), int(dyn.has_rpath));
    check(dyn.ok && soname == "libKF5ThreadWeaver.so",
          "HarmonyOS: libKF5ThreadWeaver.so carries the unversioned DT_SONAME");
    check(dyn.ok && dyn.has_runpath,
          "HarmonyOS: libKF5ThreadWeaver.so carries a DT_RUNPATH (E537 install-RPATH link)");

    // ── R53 (2): packaged ELF re-signed with binary-sign-tool. ──────────
    check(has_codesign_section(libPath),
          "HarmonyOS: packaged libKF5ThreadWeaver.so carries a .codesign section (binary-sign-tool)");

    std::printf("SUMMARY: %d passed, %d failed\n", g_pass, g_fail);
    return g_fail == 0 ? 0 : 1;
}
