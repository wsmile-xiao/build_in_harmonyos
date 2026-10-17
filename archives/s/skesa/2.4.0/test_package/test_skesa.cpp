// SKESA OHOS consumer test.
//
// SKESA is a De novo sequencing application without a public library API, so
// this test drives the packaged `skesa` executable end-to-end (R34: must
// actually invoke the tested package):
//   1. `skesa --help` must print the option usage (binary executes).
//   2. A small synthetic single-end read set derived from a known reference is
//      assembled; the run must exit 0 and produce a non-empty FASTA that
//      contains a contig whose sequence matches a distinctive motif of the
//      reference.
//   3. (assertion 3) the assembly output is a non-empty FASTA with a real
//      contig.
//   4. (assertion 4) a contig reproduces the engineered reference motif,
//      proving a genuine (non-trivial) assembly was produced.
//
// The reference is generated as a HIGH-COMPLEXITY (non-repetitive) sequence so
// the k-mer de Bruijn graph has a well-defined linear path and assembles
// robustly.  The earlier fixed reference was a near-tandem arrangement of a
// handful of 10-mers; on such low-complexity / highly-repetitive data the
// de Bruijn graph collapses into a short ambiguous repeat loop, which can
// abort the assembly cleanly (finite short output) or leave the graph without
// a resolvable path — that made the end-to-end consumer test fail on-device
// (only 1/4 assertions passed).  Real sequencing reads come from the reference
// as exact (error-free) overlapping substrings, so the assembly is expected to
// succeed and to recover the engineered unique motif.
#include <cerrno>
#include <cctype>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>
#include <vector>

// A deterministic pseudo-random generator (no external dependency).
static unsigned long g_seed = 0x5EEDu;
static unsigned int lcg(void) {
    g_seed = g_seed * 6364136223846793005ULL + 1442695040888963407ULL;
    return (unsigned int)((g_seed >> 32) & 0xFFFFFFFFu);
}

static char base_at(unsigned long i) {
    static const char bases[4] = {'A', 'C', 'G', 'T'};
    return bases[i & 3u];
}

// Build a HIGH-COMPLEXITY reference genome of the requested length: a
// deterministic pseudo-random (non-repetitive) sequence with a single
// engineered distinctive 28-mer motif spliced into the middle.  The unique
// motif guarantees a recognisable, non-transitive seed for assertion 4 without
// depending on the surrounding bases being any particular value.
static std::string make_reference(int length) {
    const char *motif = "CGGATCGTACGGATCGTACGGATCCTGA";  // 28 nt, unique
    int motif_len = (int)strlen(motif);
    std::string ref;
    ref.reserve(length);
    int motif_at = length / 2;
    for (int i = 0; i < length; ++i) {
        if (i >= motif_at && i < motif_at + motif_len) {
            ref.push_back(motif[i - motif_at]);
        } else {
            ref.push_back(base_at(lcg()));
        }
    }
    return ref;
}

// Chop the reference into overlapping single-end reads of length `read_len`.
// Each read is an exact (error-free) contiguous substring of the reference so
// the k-mer graph has an unambiguous path; reads are laid down with an
// approximate coverage of `n_reads * read_len / ref_len`.
static bool write_reads(const char *read_file, const std::string &ref,
                        int read_len, int n_reads) {
    FILE *f = fopen(read_file, "w");
    if (!f) {
        return false;
    }
    int ref_len = (int)ref.size();
    if (ref_len <= read_len) {
        fclose(f);
        return false;
    }
    for (int i = 0; i < n_reads; ++i) {
        int start = (int)(lcg() % (unsigned long)(ref_len - read_len));
        fprintf(f, ">read%d\n", i);
        for (int j = 0; j < read_len; ++j) {
            fputc((char)toupper((unsigned char)ref[start + j]), f);
        }
        fputc('\n', f);
    }
    fclose(f);
    return true;
}

// Run a command through the shell and return its exit status.
static int run_command(const std::string &cmd, std::string &output) {
    FILE *pipe = popen(cmd.c_str(), "r");
    if (!pipe) {
        return -1;
    }
    char buf[4096];
    output.clear();
    size_t n;
    while ((n = fread(buf, 1, sizeof(buf), pipe)) > 0) {
        output.append(buf, n);
    }
    int status = pclose(pipe);
    if (status == -1 || !WIFEXITED(status)) {
        return -1;
    }
    return WEXITSTATUS(status);
}

static bool contains(const std::string &haystack, const std::string &needle) {
    return haystack.find(needle) != std::string::npos;
}

// Print the trimmed tail of a file to stdout (diagnostics when the assembly
// fails); the file must exist.
static void dump_tail(const char *path, int max_lines) {
    FILE *f = fopen(path, "r");
    if (!f) {
        fprintf(stderr, "[skesa-test] cannot open %s for diagnostics: %s\n",
                path, strerror(errno));
        return;
    }
    std::vector<std::string> lines;
    char buf[4096];
    while (fgets(buf, sizeof(buf), f)) {
        lines.push_back(buf);
    }
    fclose(f);
    size_t start = lines.size() > (size_t)max_lines
                       ? lines.size() - (size_t)max_lines
                       : 0;
    fprintf(stderr, "[skesa-test] ---- tail of %s (%zu lines) ----\n",
            path, lines.size());
    for (size_t i = start; i < lines.size(); ++i) {
        fprintf(stderr, "[skesa-test] %s", lines[i].c_str());
    }
    fprintf(stderr, "[skesa-test] ---- end of %s ----\n", path);
}

// Collect all FASTA contig sequences from a skesa output file (already
// uppercased by the caller). Returns true if at least one non-empty contig
// exists and the longest contig contains the reference motif.
static bool validate_assembly(const char *out_file, std::string &longest) {
    FILE *f = fopen(out_file, "r");
    if (!f) {
        return false;
    }
    std::string current;
    longest.clear();
    char line[65536];
    bool any = false;
    while (fgets(line, sizeof(line), f)) {
        if (line[0] == '>') {
            if (!current.empty()) {
                any = true;
                if (current.size() > longest.size()) {
                    longest = current;
                }
                current.clear();
            }
            continue;
        }
        for (char *p = line; *p && *p != '\n'; ++p) {
            current.push_back((char)toupper((unsigned char)*p));
        }
    }
    if (!current.empty()) {
        any = true;
        if (current.size() > longest.size()) {
            longest = current;
        }
    }
    fclose(f);
    return any && !longest.empty();
}

int main(int argc, char **argv) {
    const char *skesa = argc > 1 ? argv[1] : "skesa";
    const char *tmp = getenv("TMPDIR");
    if (!tmp || !*tmp) {
        tmp = ".";
    }
    std::string dir = std::string(tmp) + "/skesa-ohos-test-XXXXXX";
    if (!mkdtemp(&dir[0])) {
        fprintf(stderr, "FAIL: cannot create %s: %s\n", tmp, strerror(errno));
        return 1;
    }

    std::string reads = dir + "/reads.fa";
    std::string out = dir + "/out.fa";
    std::string log = dir + "/skesa.log";
    std::string help_out, asm_out;
    int passed = 0, total = 4;
    int status;

    // Test 1: --help prints usage and exits 0.
    std::string help_cmd = std::string("\"") + skesa + "\" --help 2>&1";
    status = run_command(help_cmd, help_out);
    if (status == 0 && contains(help_out, "skesa")) {
        ++passed;
    }

    // Build the synthetic read set and assemble it.  A ~6 kbp high-complexity
    // reference with a unique engineered motif; error-free overlapping reads
    // (length 70) at ~36x coverage assemble robustly and should reconstruct
    // the full reference as contigs well above --min_contig.
    const int REF_LEN = 6000;
    const int READ_LEN = 70;
    const int N_READS = 3100;   // ~36x coverage
    const std::string genome = make_reference(REF_LEN);

    if (!write_reads(reads.c_str(), genome, READ_LEN, N_READS)) {
        fprintf(stderr, "FAIL: cannot write reads to %s\n", reads.c_str());
        return 1;
    }

    std::string assemble_cmd = std::string("\"") + skesa + "\" --reads \"" +
                               reads + "\" --cores 1 --memory 3 " +
                               "--min_contig 100 > \"" + out + "\" 2> \"" + log + "\"";
    status = run_command(assemble_cmd, asm_out);

    // Test 2: assembly run exits 0.
    if (status == 0) {
        ++passed;
    } else {
        // Dump the real skesa stderr so an on-device failure is diagnosable
        // in the raw preflight log instead of a bare "1/4 passed".
        fprintf(stderr,
                "[skesa-test] assembly exited with status %d (WIFEXITED)\n",
                status);
        dump_tail(log.c_str(), 25);
    }

    // Test 3: assembly output is a non-empty FASTA with a real contig.
    std::string longest;
    if (validate_assembly(out.c_str(), longest)) {
        ++passed;
    } else {
        fprintf(stderr, "[skesa-test] no valid FASTA contig found in %s\n",
                out.c_str());
        dump_tail(log.c_str(), 25);
    }

    // Test 4: the longest assembled contig reproduces the reference motif,
    // proving a genuine (non-trivial) assembly was produced.
    if (!longest.empty() && contains(longest, "CGGATCGTACGGATCGTACGGATCCTGA")) {
        ++passed;
    } else if (!longest.empty()) {
        fprintf(stderr,
                "[skesa-test] longest contig (%zu nt) lacks the reference motif\n",
                longest.size());
    }

    printf("skesa OHOS consumer assertions: %d/%d passed\n", passed, total);
    fflush(stdout);

    // Emit the HMBS test-package result marker from the real test command.
    // discovered/passedCount come directly from the assertions executed above.
    printf(
        "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":%s,"
        "\"command\":\"%s --reads reads.fa --cores 1 --memory 3 "
        "--min_contig 100\",\"discovered\":%d,\"passedCount\":%d}\n",
        passed == total ? "true" : "false",
        skesa,
        total,
        passed
    );
    fflush(stdout);

    // Clean up temporary files.
    remove(reads.c_str());
    remove(out.c_str());
    remove(log.c_str());
    rmdir(dir.c_str());
    return passed == total ? 0 : 1;
}
