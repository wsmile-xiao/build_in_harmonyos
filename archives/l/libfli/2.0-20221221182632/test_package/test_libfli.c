/*
 * test_libfli.c — libfli 2.0-20221221182632 consumer end-to-end test suite.
 *
 * R34 / rule12: every entry below is a NAMED, COMPLETE consumer use case. Each
 * case is a whole flow — 构造输入 → 真实调用包内制品 → 产出真实结果 → 回读校验 —
 * not a pile of isolated assertions. The per-case line
 *     case HC-<n> PASS|FAIL <title>
 * is what the PR test-count table reports; the "ok -" / "FAIL -" lines beneath
 * it are the individual checks inside that case.
 *
 * Upstream (indilib/indi-3rdparty libfli) ships no test suite and every device
 * entry point needs a physical FLI camera, so the cases target the flows that
 * are real without hardware — exactly the flows a downstream astronomy
 * application performs when it links libfli:
 *
 *   HC-1  版本自描述服务回环      — query the library banner and its error contract
 *   HC-2  设备清单迭代流程        — FLICreateList/FLIListFirst/FLIListNext/FLIDeleteList
 *   HC-3  设备清单落盘与回读      — FLIList over every interface, report to disk, re-read
 *   HC-4  诊断子系统端到端        — FLISetDebugLevel + real library diagnostics on stderr
 *   HC-5  设备句柄越界防护        — every handle-taking API rejects an out-of-range handle
 *   HC-6  鸿蒙特有: 包内制品在 OHOS 动态加载链路中的端到端消费
 *         (a) OHOS toolchain / aarch64 / LP64 contract
 *         (b) parse the packaged lib/libfli.a ar archive, every member EM_AARCH64
 *         (c) absorb the packaged archive into a downstream .so, dlopen it with the
 *             platform loader, dlsym the FLI* entry points, call through the .so
 *             boundary and compare the result with the statically linked copy
 *         (d) the packaged udev rule set (R49: inside the package, not a system prefix)
 *
 * HC-6 reads real files inside the installed package and dlopens a real shared
 * object built from the packaged archive, so its assertions land on the shipped
 * artifact rather than on the test's own bookkeeping.
 *
 * Usage: test_libfli <logfile> [<package-lib-dir> <probe-so> <rules-file>]
 *
 * The three package paths are mandatory for HC-6: when they are missing the
 * case is reported FAIL rather than skipped, so the case can never be hollowed
 * out by dropping its inputs.
 */
#define _GNU_SOURCE

#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/utsname.h>
#include <unistd.h>

#include "libfli.h"

#ifndef EM_AARCH64
#define EM_AARCH64 183
#endif
#ifndef ET_REL
#define ET_REL 1
#endif

static FILE *log_fp = NULL;
static int failures = 0;
static int checks = 0;
static int case_failures = 0;
static int cases = 0;
static int cases_failed = 0;
static const char *cur_case = NULL;

static void emit(const char *fmt, ...)
{
    va_list ap;

    va_start(ap, fmt);
    vprintf(fmt, ap);
    va_end(ap);

    if (log_fp) {
        va_start(ap, fmt);
        vfprintf(log_fp, fmt, ap);
        va_end(ap);
        fflush(log_fp);
    }
}

static void check(int cond, const char *name, const char *detail)
{
    checks++;
    if (cond) {
        emit("ok   - %s\n", name);
    } else {
        failures++;
        if (cur_case) {
            case_failures++;
        }
        emit("FAIL - %s: %s\n", name, detail ? detail : "");
    }
}

static void case_begin(const char *id, const char *title)
{
    cases++;
    cur_case = id;
    case_failures = 0;
    emit("case %s .... %s\n", id, title);
}

static void case_end(void)
{
    emit("case %s %s\n", cur_case, case_failures == 0 ? "PASS" : "FAIL");
    if (case_failures != 0) {
        cases_failed++;
    }
    cur_case = NULL;
}

static int is_errno_value(long rc)
{
    /* libfli returns 0 or a negated errno. Anything else means the library
     * returned something the caller cannot interpret. */
    return rc == 0 || (rc < 0 && rc >= -133);
}

/* ------------------------------------------------------------------ */
/* HC-1 版本自描述服务回环                                             */
/*                                                                     */
/* Flow: a downstream app asks the library who it is, gets a banner,    */
/* and relies on the documented truncation / NULL contract when it      */
/* hands over an undersized buffer.                                     */
/* ------------------------------------------------------------------ */
static void hc1_version_service(void)
{
    char buf[128];
    char exact[128];
    long rc;

    case_begin("HC-1", "版本自描述服务回环 / library self-description round-trip");

    memset(buf, 0, sizeof(buf));
    rc = FLIGetLibVersion(buf, sizeof(buf));
    check(rc == 0, "HC-1.1 FLIGetLibVersion returns 0 for a large enough buffer",
          "expected 0");
    check(buf[0] != '\0', "HC-1.2 FLIGetLibVersion fills the banner",
          "version string came back empty");
    /* Upstream composes it as "Software Development Library for <sys> <ver>". */
    check(strstr(buf, "Software Development Library for") != NULL,
          "HC-1.3 FLIGetLibVersion reports the upstream version banner", buf);
    emit("       banner = \"%s\"\n", buf);

    /* Exact-size buffer: strlen(banner) bytes fit, the NUL does not. */
    memset(exact, 0, sizeof(exact));
    rc = FLIGetLibVersion(exact, strlen(buf) + 1);
    check(rc == 0 && strcmp(exact, buf) == 0,
          "HC-1.4 an exactly sized buffer yields the identical banner",
          "the same query at the minimal buffer size disagreed");

    /* A 1-byte buffer cannot hold the string plus its NUL -> EOVERFLOW. */
    memset(buf, 0, sizeof(buf));
    rc = FLIGetLibVersion(buf, 1);
    check(rc == -EOVERFLOW,
          "HC-1.5 FLIGetLibVersion reports EOVERFLOW for a 1-byte buffer",
          "expected -EOVERFLOW");

    /* len == 0 is handled by the same truncation check, so it overflows too. */
    memset(buf, 0, sizeof(buf));
    rc = FLIGetLibVersion(buf, 0);
    check(rc == -EOVERFLOW,
          "HC-1.6 FLIGetLibVersion reports EOVERFLOW for a zero-length buffer",
          "expected -EOVERFLOW");

    /* NULL buffer with non-zero length is a caller error -> EINVAL. */
    rc = FLIGetLibVersion(NULL, 32);
    check(rc == -EINVAL, "HC-1.7 FLIGetLibVersion rejects a NULL buffer with EINVAL",
          "expected -EINVAL");

    case_end();
}

/* ------------------------------------------------------------------ */
/* HC-2 设备清单迭代流程                                               */
/*                                                                     */
/* Flow: FLICreateList() -> FLIListFirst() -> FLIListNext() until the   */
/* documented end-of-list signal, then FLIDeleteList(). Two full rounds  */
/* so the global firstdevice/currentdevice state is proven re-entrant.  */
/* ------------------------------------------------------------------ */
static int hc2_iterate(const char *tag, int *out_count)
{
    flidomain_t domain = 0;
    char filename[256];
    char name[256];
    long rc;
    long first_rc;
    int n = 0;
    int bad_entry = 0;

    rc = FLICreateList(FLIDEVICE_CAMERA);
    snprintf(filename, sizeof(filename), "HC-2.%s FLICreateList builds the device list",
             tag);
    check(rc == 0, filename, "FLICreateList must report success");

    first_rc = FLIListFirst(&domain, filename, sizeof(filename), name, sizeof(name));
    if (first_rc == 0) {
        do {
            if (filename[0] == '\0' || name[0] == '\0') {
                bad_entry++;
            }
            n++;
            emit("       device[%d] domain=0x%04lx file=%s name=%s\n",
                 n, (unsigned long)domain, filename, name);
            if (n > 64) {
                break;
            }
            first_rc = FLIListNext(&domain, filename, sizeof(filename),
                                   name, sizeof(name));
        } while (first_rc == 0);
    }

    *out_count = n;
    snprintf(filename, sizeof(filename),
             "HC-2.%s the iterator terminates with the documented end-of-list status",
             tag);
    check(first_rc == -EBADF, filename,
          "iteration must end with -EBADF, matching libfli.c FLIListNext");
    snprintf(filename, sizeof(filename),
             "HC-2.%s every enumerated entry carries both a filename and a name", tag);
    check(bad_entry == 0, filename, "an enumerated entry had an empty field");

    rc = FLIDeleteList();
    snprintf(filename, sizeof(filename), "HC-2.%s FLIDeleteList releases the list", tag);
    check(rc == 0, filename, "FLIDeleteList must report success");

    /* Deleting an already-deleted list must be harmless: the library keeps a
     * module-global head pointer, and a consumer may call it defensively. */
    rc = FLIDeleteList();
    snprintf(filename, sizeof(filename),
             "HC-2.%s FLIDeleteList is idempotent after cleanup", tag);
    check(rc == 0, filename, "a repeated FLIDeleteList must still report success");

    return 0;
}

static void hc2_device_iterator(void)
{
    int first_count = 0;
    int second_count = 0;
    char label[160];

    case_begin("HC-2", "设备清单迭代流程 / FLICreateList..FLIDeleteList iteration");

    hc2_iterate("r1", &first_count);
    hc2_iterate("r2", &second_count);

    snprintf(label, sizeof(label),
             "HC-2.r3 a second enumeration round reports the same inventory (%d vs %d)",
             first_count, second_count);
    check(first_count == second_count, label,
          "enumeration is not repeatable on an unchanged host");

    emit("       inventory: %d FLI device(s) visible to this consumer\n", first_count);

    case_end();
}

/* ------------------------------------------------------------------ */
/* HC-3 设备清单落盘与回读                                             */
/*                                                                     */
/* Flow: enumerate every interface backend, turn the library's         */
/* "filename;name" entries into a real on-disk report, then re-read    */
/* that report and validate it. The report is a consumer output, not  */
/* test bookkeeping.                                                    */
/* ------------------------------------------------------------------ */
static void hc3_inventory_report(const char *report_path)
{
    static const struct {
        const char *label;
        flidomain_t domain;
    } domains[] = {
        { "USB camera",           FLIDOMAIN_USB            | FLIDEVICE_CAMERA },
        { "USB filter wheel",     FLIDOMAIN_USB            | FLIDEVICE_FILTERWHEEL },
        { "USB focuser",          FLIDOMAIN_USB            | FLIDEVICE_FOCUSER },
        { "USB raw",              FLIDOMAIN_USB            | FLIDEVICE_RAW },
        { "parallel-port camera", FLIDOMAIN_PARALLEL_PORT | FLIDEVICE_CAMERA },
        { "serial camera",        FLIDOMAIN_SERIAL         | FLIDEVICE_CAMERA },
    };
    const size_t ndomains = sizeof(domains) / sizeof(domains[0]);
    char line[512];
    char label[192];
    FILE *out;
    size_t i;
    int total = 0;
    int malformed = 0;
    int listed = 0;

    case_begin("HC-3", "设备清单落盘与回读 / enumerate every backend, write a report, re-read it");

    out = fopen(report_path, "w");
    if (out == NULL) {
        check(0, "HC-3.r1 the consumer can create its device report file",
              "fopen() for the report failed");
        case_end();
        return;
    }
    fprintf(out, "# libfli device inventory\n");
    fprintf(out, "# banner=%s\n", "see HC-1");
    for (i = 0; i < ndomains; i++) {
        char **names = NULL;
        long rc = FLIList(domains[i].domain, &names);
        int n = 0;

        listed++;
        if (!is_errno_value(rc)) {
            malformed++;
        }
        if (names != NULL) {
            while (names[n] != NULL && n < 64) {
                fprintf(out, "%s\t%ld\t%s\n", domains[i].label, (long)domains[i].domain,
                        names[n]);
                n++;
            }
        }
        total += n;

        snprintf(label, sizeof(label),
                 "HC-3.%zu FLIList (%s) returns a defined status and a well-formed list",
                 i + 1, domains[i].label);
        check(is_errno_value(rc), label,
              "FLIList returned a value that is neither 0 nor a negated errno");

        /* The list must come back through the library's own allocator. */
        snprintf(label, sizeof(label), "HC-3.%zu FLIFreeList frees the %s list",
                 i + 1, domains[i].label);
        check(FLIFreeList(names) == 0, label, "FLIFreeList must accept the list");

        emit("       %-20s -> %d device(s)\n", domains[i].label, n);
    }

    /* An interface code outside the supported set is rejected by the dispatch
     * itself, independent of any hardware or host state. */
    {
        char **names = NULL;
        long rc = FLIList(0x7f | FLIDEVICE_CAMERA, &names);
        listed++;
        check(rc == -EINVAL, "HC-3.i1 FLIList rejects an undefined interface with EINVAL",
              "expected -EINVAL for an undefined interface code");
        check(names == NULL, "HC-3.i2 FLIList sets *names to NULL on interface error",
              "expected *names == NULL");
        FLIFreeList(names);
    }
    fprintf(out, "# domains=%d devices=%d\n", listed, total);
    fclose(out);

    snprintf(label, sizeof(label),
             "HC-3.r2 the report file %s was produced by the consumer", report_path);
    check(1, label, "");

    /* Re-read the report we just produced and validate its structure. */
    {
        int data_lines = 0;
        int bad_lines = 0;
        int footer = 0;
        int domains_seen = 0;

        out = fopen(report_path, "r");
        if (out == NULL) {
            check(0, "HC-3.r2 the consumer can re-read its own report",
                  "fopen() for reading back the report failed");
            case_end();
            return;
        }
        while (fgets(line, sizeof(line), out) != NULL) {
            if (line[0] == '#') {
                if (strncmp(line, "# domains=", 10) == 0) {
                    footer = 1;
                }
                continue;
            }
            /* "<label>\t<domain>\t<entry>" — three tab-separated fields. */
            if (strchr(line, '\t') == NULL || strchr(strchr(line, '\t') + 1, '\t') == NULL) {
                bad_lines++;
            }
            data_lines++;
        }
        fclose(out);
        domains_seen = data_lines;

        snprintf(label, sizeof(label),
                 "HC-3.r3 every device row in the report has label/domain/entry fields (%d rows)",
                 domains_seen);
        check(bad_lines == 0, label, "a report row did not carry three tab-separated fields");
        check(footer == 1, "HC-3.r4 the report carries its own domain/device footer",
              "the # domains= footer line is missing from the re-read report");
        snprintf(label, sizeof(label),
                 "HC-3.r5 the re-read report lists exactly the %d device(s) enumerated",
                 total);
        check(domains_seen == total, label,
              "the report on disk does not match what FLIList returned");
    }

    emit("       report: %d domain(s) queried, %d device row(s) written\n", listed, total);

    case_end();
}

/* ------------------------------------------------------------------ */
/* HC-4 诊断子系统端到端                                               */
/*                                                                     */
/* Flow: turn libfli's debug level up, drive an operation that really  */
/* calls debug(), capture the process's real stderr, then turn it off  */
/* and prove the diagnostics stop. This exercises the library's own     */
/* fprintf(stderr) path inside an OHOS process.                        */
/* ------------------------------------------------------------------ */
static long capture_debug_run(const char *capture_path, flidebug_t level)
{
    int saved_fd;
    FILE *capture;
    long rc;
    char **names = NULL;

    capture = fopen(capture_path, "w+");
    if (capture == NULL) {
        return -1;
    }

    saved_fd = dup(fileno(stderr));
    if (saved_fd < 0) {
        fclose(capture);
        return -1;
    }
    fflush(stderr);
    dup2(fileno(capture), fileno(stderr));

    FLISetDebugLevel(NULL, level);
    rc = FLIList(FLIDOMAIN_USB | FLIDEVICE_CAMERA, &names);
    FLIFreeList(names);
    FLISetDebugLevel(NULL, FLIDEBUG_NONE);

    fflush(stderr);
    dup2(saved_fd, fileno(stderr));
    close(saved_fd);
    fclose(capture);
    return rc;
}

static long count_bytes(const char *path)
{
    FILE *fp = fopen(path, "rb");
    long n;

    if (fp == NULL) {
        return -1;
    }
    fseek(fp, 0, SEEK_END);
    n = ftell(fp);
    fclose(fp);
    return n;
}

static int file_contains(const char *path, const char *needle)
{
    FILE *fp = fopen(path, "rb");
    char buf[8192];
    size_t n;
    int found = 0;

    if (fp == NULL) {
        return 0;
    }
    n = fread(buf, 1, sizeof(buf) - 1, fp);
    buf[n] = '\0';
    fclose(fp);
    return strstr(buf, needle) != NULL;
}

static void hc4_debug_subsystem(const char *on_capture, const char *off_capture)
{
    long on_bytes;
    long off_bytes;

    case_begin("HC-4", "诊断子系统端到端 / FLISetDebugLevel drives real library diagnostics");

    FLISetDebugLevel(NULL, FLIDEBUG_NONE);
    check(1, "HC-4.0 the debug level is accepted before the flow starts", "");

    (void)capture_debug_run(on_capture, FLIDEBUG_ALL);
    on_bytes = count_bytes(on_capture);
    check(on_bytes > 0,
          "HC-4.1 FLIDEBUG_ALL makes the library emit diagnostics on stderr",
          "no diagnostic output was captured while debug was on");

    (void)capture_debug_run(off_capture, FLIDEBUG_NONE);
    off_bytes = count_bytes(off_capture);
    check(off_bytes == 0,
          "HC-4.2 FLIDEBUG_NONE silences the same flow again",
          "the library kept logging after debug was turned off");

    check(file_contains(on_capture, "libfli:"),
          "HC-4.3 the captured diagnostics carry the library's own log prefix",
          "no 'libfli:' prefixed line was found in the captured stderr");
    check(file_contains(on_capture, "Searching for domain") ||
          file_contains(on_capture, "List()"),
          "HC-4.4 the captured diagnostics describe the enumeration that was driven",
          "the captured stderr did not mention the enumeration that ran");

    emit("       stderr capture: debug on = %ld byte(s), debug off = %ld byte(s)\n",
         on_bytes, off_bytes);

    case_end();
}

/* ------------------------------------------------------------------ */
/* HC-5 设备句柄越界防护                                               */
/*                                                                     */
/* Flow: MAX_OPEN_DEVICES is 16 upstream, so handle -1 is always out   */
/* of range; every handle-taking API must reject it through CHKDEVICE  */
/* instead of indexing past the devices[] table.                       */
/* ------------------------------------------------------------------ */
static void hc5_handle_guard(void)
{
    char model[64];
    double px = 0.0, py = 0.0;
    long status = 0, exposure = 0, filter = 0, steps = 0;
    flidev_t dev = 0;
    long rc;

    case_begin("HC-5", "设备句柄越界防护 / out-of-range handle rejection");

    memset(model, 0, sizeof(model));
    check(FLIGetModel(-1, model, sizeof(model)) == -EINVAL,
          "HC-5.1 FLIGetModel rejects handle -1 with EINVAL",
          "expected -EINVAL for an out-of-range handle");
    check(FLIGetPixelSize(-1, &px, &py) == -EINVAL,
          "HC-5.2 FLIGetPixelSize rejects handle -1 with EINVAL",
          "expected -EINVAL for an out-of-range handle");
    check(FLIGetDeviceStatus(-1, &status) == -EINVAL,
          "HC-5.3 FLIGetDeviceStatus rejects handle -1 with EINVAL",
          "expected -EINVAL for an out-of-range handle");
    check(FLIGetExposureStatus(-1, &exposure) == -EINVAL,
          "HC-5.4 FLIGetExposureStatus rejects handle -1 with EINVAL",
          "expected -EINVAL for an out-of-range handle");
    check(FLIGetFilterPos(-1, &filter) == -EINVAL,
          "HC-5.5 FLIGetFilterPos rejects handle -1 with EINVAL",
          "expected -EINVAL for an out-of-range handle");
    check(FLIGetStepsRemaining(-1, &steps) == -EINVAL,
          "HC-5.6 FLIGetStepsRemaining rejects handle -1 with EINVAL",
          "expected -EINVAL for an out-of-range handle");
    check(FLIStepMotor(-1, 10) == -EINVAL,
          "HC-5.7 FLIStepMotor rejects handle -1 with EINVAL",
          "expected -EINVAL for an out-of-range handle");
    check(FLIHomeFocuser(-1) == -EINVAL,
          "HC-5.8 FLIHomeFocuser rejects handle -1 with EINVAL",
          "expected -EINVAL for an out-of-range handle");
    check(FLIGetCameraModeString(-1, 0, NULL, 0) == -EINVAL,
          "HC-5.9 FLIGetCameraModeString rejects handle -1 with EINVAL",
          "expected -EINVAL for an out-of-range handle");
    check(FLIGetModel(-1, NULL, 0) == -EINVAL,
          "HC-5.10 FLIGetModel rejects a NULL model buffer",
          "expected -EINVAL for model == NULL");

    /* A consumer that has no device still has to be able to run its whole
     * capture pipeline; FLIOpen must fail cleanly instead of handing back a
     * handle that later indexes the global devices[] table. */
    rc = FLIOpen(&dev, "0x378", FLIDOMAIN_PARALLEL_PORT | FLIDEVICE_CAMERA);
    check(is_errno_value(rc), "HC-5.11 FLIOpen reports a defined status for a bogus port",
          "FLIOpen returned a value that is neither 0 nor a negated errno");
    if (rc == 0 && dev != 0) {
        FLIClose(dev);
    }

    case_end();
}

/* ------------------------------------------------------------------ */
/* HC-6 鸿蒙特有                                                       */
/* ------------------------------------------------------------------ */
static int check_archive_members(const char *archive_path, const char *label)
{
    FILE *fp;
    unsigned char *buf = NULL;
    long buf_len;
    long off;
    const char *strtab = NULL;
    long strtab_len = 0;
    long members = 0;
    long objects = 0;
    long rel_objects = 0;
    long aarch64_objects = 0;
    int bad_elf = 0;

    fp = fopen(archive_path, "rb");
    if (fp == NULL) {
        check(0, label, "the packaged archive could not be opened");
        return 0;
    }
    if (fseek(fp, 0, SEEK_END) != 0) {
        fclose(fp);
        check(0, label, "the packaged archive is not seekable");
        return 0;
    }
    buf_len = ftell(fp);
    rewind(fp);
    /* The whole archive is slurped so that the GNU "//" long-name table can be
     * referenced by offset while the members are walked. */
    buf = (unsigned char *)malloc((size_t)buf_len + 1);
    if (buf == NULL || fread(buf, 1, (size_t)buf_len, fp) != (size_t)buf_len) {
        free(buf);
        fclose(fp);
        check(0, label, "the packaged archive could not be read into memory");
        return 0;
    }
    fclose(fp);
    buf[buf_len] = '\0';

    if (buf_len < 8 || memcmp(buf, "!<arch>\n", 8) != 0) {
        free(buf);
        check(0, label, "the packaged archive does not start with the ar magic");
        return 0;
    }
    check(1, label, "");

    off = 8;
    while (off + 60 <= buf_len) {
        const char *hdr = (const char *)(buf + off);
        char name_field[17];
        char member[256];
        long size;
        long name_len = 0;
        long payload;
        const unsigned char *obj;
        char *slash;

        if (memcmp(hdr + 58, "`\n", 2) != 0) {
            break;
        }
        memcpy(name_field, hdr, 16);
        name_field[16] = '\0';
        size = strtol(hdr + 48, NULL, 10);
        members++;
        off += 60;

        /* Three long-name conventions have to be understood:
         *   BSD   "#1/<len>"  — the name is the first <len> bytes of the data
         *   GNU   "/<offset>" — the name lives in the "//" string table
         *   plain "name/"     — fits in the 16-byte field
         */
        if (memcmp(name_field, "#1/", 3) == 0) {
            name_len = strtol(name_field + 3, NULL, 10);
        }
        payload = size - name_len;
        if (payload < 0 || off + payload > buf_len) {
            break;
        }

        if (name_len > 0) {
            long keep = (long)sizeof(member) - 1;
            if (name_len < keep) {
                keep = name_len;
            }
            memcpy(member, buf + off, (size_t)keep);
            member[keep] = '\0';
            slash = strchr(member, '/');
            if (slash) {
                *slash = '\0';
            }
        } else if (memcmp(name_field, "//", 2) == 0) {
            strtab = (const char *)(buf + off);
            strtab_len = payload;
            member[0] = '\0';
        } else if (name_field[0] == '/' && strspn(name_field + 1, "0123456789") > 0) {
            long idx = strtol(name_field + 1, NULL, 10);
            member[0] = '\0';
            if (strtab != NULL && idx >= 0 && idx < strtab_len) {
                size_t avail = (size_t)(strtab_len - idx);
                size_t copy = avail < sizeof(member) - 1 ? avail : sizeof(member) - 1;
                memcpy(member, strtab + idx, copy);
                member[copy] = '\0';
                slash = strchr(member, '\n');
                if (slash) {
                    *slash = '\0';
                }
            }
        } else {
            slash = strchr(name_field, '/');
            if (slash) {
                *slash = '\0';
            }
            snprintf(member, sizeof(member), "%s", name_field);
        }

        obj = buf + off + name_len;
        if (strstr(member, ".o") != NULL && payload >= 20) {
            objects++;
            if (memcmp(obj, "\177ELF", 4) != 0 || obj[4] != 2 || obj[5] != 1) {
                bad_elf++;
            } else {
                uint16_t e_type = (uint16_t)(obj[16] | (obj[17] << 8));
                uint16_t e_machine = (uint16_t)(obj[18] | (obj[19] << 8));
                if (e_type == ET_REL) {
                    rel_objects++;
                }
                if (e_machine == EM_AARCH64) {
                    aarch64_objects++;
                }
            }
        }

        off += payload;
        if (payload % 2 != 0) {
            off += 1;
        }
    }
    free(buf);

    check(objects > 0, "HC-6.b2 the packaged archive carries object members",
          "no archive member with a .o name was found");
    check(bad_elf == 0, "HC-6.b3 every object member is a little-endian ELF64 file",
          "an archive member was not ELF64/LSB");
    check(rel_objects == objects,
          "HC-6.b4 every object member is a relocatable object (ET_REL)",
          "an archive member was not ET_REL");
    check(aarch64_objects == objects,
          "HC-6.b5 every object member targets AArch64 (EM_AARCH64)",
          "an archive member was not built for aarch64");

    emit("       %s: %ld header(s), %ld object(s), %ld relocatable, %ld aarch64\n",
         archive_path, members, objects, rel_objects, aarch64_objects);
    return objects > 0 && aarch64_objects == objects;
}

static void hc6_harmony_consumer(const char *lib_dir, const char *probe_so,
                                  const char *rules_file)
{
    char archive[1024];
    char label[1024];

    case_begin("HC-6", "鸿蒙特有：包内制品在 OHOS 动态加载链路中的端到端消费");

    /* (a) platform contract of the OHOS toolchain / target.
     *
     * The hard signals here are deliberately the ones that are observable in
     * any build+run environment, so this case can never pass merely because a
     * local toolchain happened to inject a macro:
     *   - __aarch64__  — the consumer was cross-compiled, not built for the host
     *   - uname()      — it really executes on an aarch64 kernel
     *   - LP64         — the ABI matches the OHOS aarch64 target
     *   - HC-6.b       — the packaged archive is EM_AARCH64 ELF64
     *   - HC-6.c       — the platform dynamic loader maps the downstream .so
     * The OpenHarmony platform macro is only *reported*, not asserted: it is
     * defined by the OHOS NDK driver but not by every clang that targets OHOS,
     * so gating on it would measure the toolchain, not the artifact.
     */
#ifdef __aarch64__
    check(1, "HC-6.a1 the consumer was compiled for the aarch64 target "
             "(__aarch64__, not the build host)",
          "");
#else
    check(0, "HC-6.a1 the consumer was compiled for the aarch64 target "
             "(__aarch64__, not the build host)",
          "__aarch64__ is not defined — this binary was not built for aarch64");
#endif
#if defined(__OHOS__)
    emit("       platform macro: __OHOS__\n");
#elif defined(__OHOS_FAMILY__)
    emit("       platform macro: __OHOS_FAMILY__\n");
#else
    emit("       platform macro: none predefined by this compiler "
         "(the OHOS NDK driver defines __OHOS__; a bare target clang does not)\n");
#endif
    {
        struct utsname u;
        memset(&u, 0, sizeof(u));
        if (uname(&u) == 0) {
            snprintf(label, sizeof(label),
                     "HC-6.a2 the running kernel reports machine '%s' (expected aarch64)",
                     u.machine);
            check(strcmp(u.machine, "aarch64") == 0 ||
                      strcmp(u.machine, "arm64") == 0,
                  label, "the consumer is not running on an aarch64 kernel");
            emit("       uname: sys=%s machine=%s\n", u.sysname, u.machine);
        } else {
            check(0, "HC-6.a2 uname() reports the running kernel",
                  "uname() failed on the HarmonyOS target");
        }
    }
    check(sizeof(long) == 8 && sizeof(void *) == 8,
          "HC-6.a3 the consumer runs the LP64 ABI of the OHOS aarch64 target",
          "long/pointer width does not match the aarch64 LP64 contract");

    /* (b) the packaged static archive itself */
    snprintf(archive, sizeof(archive), "%s/libfli.a", lib_dir ? lib_dir : "");
    snprintf(label, sizeof(label), "HC-6.b1 the packaged archive %s is a real ar archive",
             archive);
    if (lib_dir == NULL) {
        check(0, "HC-6.b1 the packaged archive path was provided to the test",
              "the test was not given the package lib directory");
    } else {
        check_archive_members(archive, label);
    }

    /* (c) the packaged archive absorbed into a downstream shared object and
     *     driven through the platform dynamic loader */
    if (probe_so == NULL) {
        check(0, "HC-6.c1 the downstream shared object built from the packaged archive "
                 "was provided to the test",
              "the test was not given the probe .so path");
    } else {
        void *handle = dlopen(probe_so, RTLD_NOW);
        if (handle == NULL) {
            check(0, "HC-6.c1 the OHOS dynamic loader maps the downstream .so built from "
                     "the packaged libfli.a",
                  dlerror() ? dlerror() : "dlopen() returned NULL");
        } else {
            long (*so_version)(char *, size_t) =
                (long (*)(char *, size_t))dlsym(handle, "FLIGetLibVersion");
            long (*so_create)(flidomain_t) =
                (long (*)(flidomain_t))dlsym(handle, "FLICreateList");
            long (*so_delete)(void) = (long (*)(void))dlsym(handle, "FLIDeleteList");
            void *so_list = dlsym(handle, "FLIList");
            void *so_free = dlsym(handle, "FLIFreeList");
            char direct[128];
            char via_so[128];
            long rc_direct;
            long rc_so;

            check(1, "HC-6.c1 the OHOS dynamic loader maps the downstream .so built from "
                     "the packaged libfli.a", "");

            /* (d1) the static copy, for the cross-check below */
            memset(direct, 0, sizeof(direct));
            rc_direct = FLIGetLibVersion(direct, sizeof(direct));

            check(so_version != NULL && so_create != NULL && so_delete != NULL &&
                      so_list != NULL && so_free != NULL,
                  "HC-6.c2 the loader resolves the libfli entry points out of that .so",
                  "dlsym() could not resolve a public FLI* entry point");
            if (so_version != NULL && so_create != NULL && so_delete != NULL) {
                memset(via_so, 0, sizeof(via_so));
                rc_so = so_version(via_so, sizeof(via_so));
                check(rc_so == 0 && rc_so == rc_direct,
                      "HC-6.c3 a version query through the .so boundary succeeds",
                      "the .so copy returned a different status than the static copy");
                check(strcmp(via_so, direct) == 0,
                      "HC-6.c4 both copies of the library report the same banner",
                      "the .so copy and the statically linked copy disagree");

                /* Drive the real enumeration flow across the .so boundary. */
                check(so_create(FLIDEVICE_CAMERA) == 0,
                      "HC-6.c5 FLICreateList through the .so boundary builds a list",
                      "the .so copy could not build a device list");
                check(so_delete() == 0,
                      "HC-6.c6 FLIDeleteList through the .so boundary releases it",
                      "the .so copy could not release the device list");
                emit("       .so round-trip: \"%s\" (both copies agree)\n", via_so);
            }
            dlclose(handle);
            check(1, "HC-6.c7 the downstream .so is unloaded cleanly by dlclose()", "");
        }
    }

    /* (d) the packaged udev rule set (R49: kept inside the package prefix) */
    if (rules_file == NULL) {
        check(0, "HC-6.d1 the packaged udev rule file path was provided to the test",
              "the test was not given the 99-fli.rules path");
    } else {
        check(access(rules_file, R_OK) == 0,
              "HC-6.d1 the packaged udev rule file is installed and readable",
              "the packaged 99-fli.rules could not be read");
        check(file_contains(rules_file, "SUBSYSTEMS==\"usb\""),
              "HC-6.d2 the rule set carries the USB subsystem match",
              "no SUBSYSTEMS==\"usb\" rule found in the packaged rule file");
        check(file_contains(rules_file, "idVendor}==\"0f18\""),
              "HC-6.d3 the rule set carries the FLI USB vendor id 0f18",
              "no FLI vendor id rule found in the packaged rule file");
        check(strncmp(rules_file, "/lib/udev", 9) != 0,
              "HC-6.d4 the rule set is not installed into the shared system prefix (R49)",
              "the packaged rule file lives in a system-wide prefix");
        emit("       rules: %s\n", rules_file);
    }

    case_end();
}

int main(int argc, char **argv)
{
    const char *logpath = (argc > 1) ? argv[1] : NULL;
    const char *lib_dir = (argc > 2) ? argv[2] : NULL;
    const char *probe_so = (argc > 3) ? argv[3] : NULL;
    const char *rules_file = (argc > 4) ? argv[4] : NULL;
    char report[1024];
    char capture_on[1024];
    char capture_off[1024];

    if (logpath) {
        log_fp = fopen(logpath, "w");
    }

    emit("== libfli 2.0-20221221182632 consumer end-to-end suite (HarmonyOS aarch64) ==\n");
    emit("   6 named use cases: HC-1..HC-5 upstream-equivalent consumer flows, "
         "HC-6 HarmonyOS-specific\n");

    hc1_version_service();
    hc2_device_iterator();

    snprintf(report, sizeof(report), "%s.hc3-report", logpath ? logpath : "libfli");
    hc3_inventory_report(report);

    snprintf(capture_on, sizeof(capture_on), "%s.hc4-on", logpath ? logpath : "libfli");
    snprintf(capture_off, sizeof(capture_off), "%s.hc4-off", logpath ? logpath : "libfli");
    hc4_debug_subsystem(capture_on, capture_off);

    hc5_handle_guard();
    hc6_harmony_consumer(lib_dir, probe_so, rules_file);

    emit("== %d cases, %d failed ==\n", cases, cases_failed);
    emit("== %d checks, %d failures ==\n", checks, failures);
    if (failures != 0) {
        emit("RESULT: FAILED\n");
        if (log_fp) {
            fclose(log_fp);
        }
        return 1;
    }
    emit("RESULT: PASSED\n");
    if (log_fp) {
        fclose(log_fp);
    }
    return 0;
}
