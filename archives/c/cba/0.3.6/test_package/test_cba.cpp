/*
 * test_cba.cpp — cba 0.3.6 (Continuous Beam Analysis CLI) test harness.
 *
 * Upstream ships NO test suite (three-layer evidence):
 *   1. source tree: no tests/ directory anywhere in the release tarball;
 *   2. build files: src/Makefile + src/gui/Makefile define no check /
 *      TESTS targets (only all / clean / install);
 *   3. configure: no configure.ac exists (plain Makefile project).
 *
 * This harness therefore provides the full coverage:
 *   11 cases / 55 assertions —
 *     c01..c06 structural-analysis analytic checks (41 assertions)
 *       c01 single span, uniform load:      M=wL^2/8, R=wL/2, V=+/-wL/2,
 *                                            d=5wL^4/384EI at midspan
 *       c02 single span, mid-span point P:  M=PL/4, d=PL^3/48EI
 *       c03 point load at quarter point:    R_A=Pb/L, R_B=Pa/L, M=Pab/L
 *       c04 two equal spans, uniform load:  hogging M=-wL^2/8,
 *                                            interior R=5wL/4, ends R=3wL/8
 *       c05 two equal spans + live load with design factors 1.35/1.5:
 *                                            M_d=(1.35G+1.5Q)L^2/8,
 *                                            interior R_d=5w_dL/4
 *       c06 upstream README worked example (5.8/4.2 m steel beam)
 *            M_B=-w(L1^3+L2^3)/(8(L1+L2)) regression
 *     c07..c10 CLI parameter / error paths (8 assertions)
 *     c11 -o output file == stdout, -p plot layout consistency (6 assertions)
 *
 * (assertion numbers include each case's exit-status check)
 *
 * Robustness notes (AI review): parse_row() may return an empty vector when a
 * result block is missing; every use is therefore guarded by a size() check
 * before indexing, and cases return immediately when cba did not run cleanly
 * (rc != 0), so a failing tool can never crash the harness.
 *
 * Input files are constructed programmatically in the current directory and
 * removed afterwards — zero binary data, CI-safe.
 */
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <sstream>
#include <string>
#include <sys/wait.h>
#include <vector>

static int g_asserts = 0;
static int g_fails = 0;

#define CHECK(cond, ...)                                                     \
    do {                                                                     \
        ++g_asserts;                                                         \
        if (!(cond)) {                                                       \
            ++g_fails;                                                       \
            std::printf("FAIL[%d] ", __LINE__);                              \
            std::printf(__VA_ARGS__);                                        \
            std::printf("\n");                                               \
        }                                                                    \
    } while (0)

static bool approx(double got, double expect, double tol) {
    return std::fabs(got - expect) <= tol;
}

static double safe_at(const std::vector<double>& v, size_t i) {
    return i < v.size() ? v[i] : 0.0;
}

static std::string read_file(const std::string& path) {
    std::ifstream f(path.c_str(), std::ios::binary);
    std::ostringstream ss;
    ss << f.rdbuf();
    return ss.str();
}

static void write_file(const std::string& path, const std::string& data) {
    std::ofstream f(path.c_str(), std::ios::binary | std::ios::trunc);
    f << data;
}

/* run a command, capturing combined stdout+stderr; returns exit code */
static int run_cmd(const std::string& cmd, std::string& out) {
    FILE* p = popen((cmd + " 2>&1").c_str(), "r");
    if (!p) return -1;
    char buf[4096];
    size_t n;
    while ((n = fread(buf, 1, sizeof(buf), p)) > 0) out.append(buf, n);
    int rc = pclose(p);  /* wait status, not plain exit code */
    if (rc == -1) return -1;
    if (WIFEXITED(rc)) return WEXITSTATUS(rc);
    return -1;
}

/*
 * parse results text: returns the nth (0-based) occurrence of the row whose
 * first tab/space separated token equals `label`; values = remaining tokens.
 * Returns an empty vector when the block is absent — callers guard size().
 */
static std::vector<double> parse_row(const std::string& text,
                                     const std::string& label, int occurrence) {
    std::vector<double> vals;
    int seen = 0;
    std::istringstream lines(text);
    std::string line;
    while (std::getline(lines, line)) {
        std::istringstream tok(line);
        std::string head;
        tok >> head;
        if (head != label) continue;
        if (seen++ != occurrence) continue;
        std::string v;
        while (tok >> v) vals.push_back(std::strtod(v.c_str(), nullptr));
        break;
    }
    return vals;
}

/* 1-span UDL: L=8, w=20 => R=80 each, Mmax=160, V=+/-80, d=5wL^4/384EI */
static int c01_udl_single(const std::string& dir) {
    write_file(dir + "/in01.txt",
               "SPANS 8.0\nINERTIA 3.69e-5\nELASTICITY 2.1e8\n"
               "LOAD 1 1 20 0 0 0\n");
    std::string out;
    int rc = run_cmd("cba -i " + dir + "/in01.txt -o " + dir + "/out01.txt", out);
    CHECK(rc == 0, "c01: cba exited %d", rc);
    if (rc != 0) return g_fails;
    std::string text = read_file(dir + "/out01.txt");
    std::vector<double> m = parse_row(text, "Mmax:", 0);
    std::vector<double> mn = parse_row(text, "Mmin:", 0);
    std::vector<double> vmax = parse_row(text, "Vmax:", 0);
    std::vector<double> vmin = parse_row(text, "Vmin:", 0);
    std::vector<double> d = parse_row(text, "dmax:", 0);
    std::vector<double> r = parse_row(text, "Rmax:", 0);
    CHECK(m.size() >= 1 && approx(m[0], 160.0, 0.02),
          "c01: Mmax got %.2f want 160.00", safe_at(m, 0));
    CHECK(mn.size() >= 1 && std::fabs(mn[0]) < 0.02,
          "c01: Mmin got %.2f want ~0", safe_at(mn, 0));
    CHECK(vmax.size() >= 1 && approx(vmax[0], 80.0, 0.02),
          "c01: Vmax got %.2f want 80.00", safe_at(vmax, 0));
    CHECK(vmin.size() >= 1 && approx(vmin[0], -80.0, 0.02),
          "c01: Vmin got %.2f want -80.00", safe_at(vmin, 0));
    CHECK(r.size() >= 2 && approx(r[0], 80.0, 0.02),
          "c01: R0 got %.2f want 80.00", safe_at(r, 0));
    CHECK(r.size() >= 2 && approx(r[1], 80.0, 0.02),
          "c01: R1 got %.2f want 80.00", safe_at(r, 1));
    CHECK(d.size() >= 1 &&
          approx(d[0], 5.0 * 20.0 * 4096.0 / (384.0 * 2.1e8 * 3.69e-5), 0.0015),
          "c01: dmax got %.4f", safe_at(d, 0));
    std::remove((dir + "/in01.txt").c_str());
    std::remove((dir + "/out01.txt").c_str());
    return g_fails;
}

/* 1-span point load at midspan: L=6 P=60 => M=90, R=30/30, d=PL^3/48EI */
static int c02_point_mid(const std::string& dir) {
    write_file(dir + "/in02.txt",
               "SPANS 6.0\nINERTIA 3.69e-5\nELASTICITY 2.1e8\n"
               "LOAD 1 2 60 0 3 0\n");
    std::string out;
    int rc = run_cmd("cba -i " + dir + "/in02.txt -o " + dir + "/out02.txt", out);
    CHECK(rc == 0, "c02: cba exited %d", rc);
    if (rc != 0) return g_fails;
    std::string text = read_file(dir + "/out02.txt");
    std::vector<double> m = parse_row(text, "Mmax:", 0);
    std::vector<double> vmax = parse_row(text, "Vmax:", 0);
    std::vector<double> vmin = parse_row(text, "Vmin:", 0);
    std::vector<double> d = parse_row(text, "dmax:", 0);
    std::vector<double> r = parse_row(text, "Rmax:", 0);
    CHECK(m.size() >= 1 && approx(m[0], 90.0, 0.02),
          "c02: Mmax got %.2f want 90.00", safe_at(m, 0));
    CHECK(vmax.size() >= 1 && approx(vmax[0], 30.0, 0.02),
          "c02: Vmax got %.2f want 30.00", safe_at(vmax, 0));
    CHECK(vmin.size() >= 1 && approx(vmin[0], -30.0, 0.02),
          "c02: Vmin got %.2f want -30.00", safe_at(vmin, 0));
    CHECK(r.size() >= 2 && approx(r[0], 30.0, 0.02),
          "c02: R0 got %.2f want 30.00", safe_at(r, 0));
    CHECK(r.size() >= 2 && approx(r[1], 30.0, 0.02),
          "c02: R1 got %.2f want 30.00", safe_at(r, 1));
    CHECK(d.size() >= 1 &&
          approx(d[0], 60.0 * 216.0 / (48.0 * 2.1e8 * 3.69e-5), 0.0015),
          "c02: dmax got %.4f want ~0.0348", safe_at(d, 0));
    std::remove((dir + "/in02.txt").c_str());
    std::remove((dir + "/out02.txt").c_str());
    return g_fails;
}

/* 1-span point load at quarter: L=8, P=80 at x=2 => R_A=60, R_B=20, M=120 */
static int c03_point_quarter(const std::string& dir) {
    write_file(dir + "/in03.txt",
               "SPANS 8.0\nINERTIA 3.69e-5\nELASTICITY 2.1e8\n"
               "LOAD 1 2 80 0 2 0\n");
    std::string out;
    int rc = run_cmd("cba -i " + dir + "/in03.txt -o " + dir + "/out03.txt", out);
    CHECK(rc == 0, "c03: cba exited %d", rc);
    if (rc != 0) return g_fails;
    std::string text = read_file(dir + "/out03.txt");
    std::vector<double> m = parse_row(text, "Mmax:", 0);
    std::vector<double> vmax = parse_row(text, "Vmax:", 0);
    std::vector<double> vmin = parse_row(text, "Vmin:", 0);
    std::vector<double> r = parse_row(text, "Rmax:", 0);
    CHECK(r.size() >= 2 && approx(r[0], 60.0, 0.02),
          "c03: R_A got %.2f want 60.00", safe_at(r, 0));
    CHECK(r.size() >= 2 && approx(r[1], 20.0, 0.02),
          "c03: R_B got %.2f want 20.00", safe_at(r, 1));
    CHECK(m.size() >= 1 && approx(m[0], 120.0, 0.02),
          "c03: Mmax got %.2f want 120.00", safe_at(m, 0));
    CHECK(vmax.size() >= 1 && approx(vmax[0], 60.0, 0.02),
          "c03: Vmax got %.2f want 60.00", safe_at(vmax, 0));
    CHECK(vmin.size() >= 1 && approx(vmin[0], -20.0, 0.02),
          "c03: Vmin got %.2f want -20.00", safe_at(vmin, 0));
    std::remove((dir + "/in03.txt").c_str());
    std::remove((dir + "/out03.txt").c_str());
    return g_fails;
}

/* 2 equal spans L=4,4 uniform w=10: hogging M=-wL^2/8=-20, R=[15,50,15] */
static int c04_cont2_udl(const std::string& dir) {
    write_file(dir + "/in04.txt",
               "SPANS 4 4\nINERTIA 3.69e-5 3.69e-5\nELASTICITY 2.1e8\n"
               "CONSTRAINTS -1 0 -1 0 -1 0\n"
               "LOAD 1 1 10 0 0 0\nLOAD 2 1 10 0 0 0\n");
    std::string out;
    int rc = run_cmd("cba -i " + dir + "/in04.txt -o " + dir + "/out04.txt", out);
    CHECK(rc == 0, "c04: cba exited %d", rc);
    if (rc != 0) return g_fails;
    std::string text = read_file(dir + "/out04.txt");
    std::vector<double> mn = parse_row(text, "Mmin:", 0);
    std::vector<double> r = parse_row(text, "Rmax:", 0);
    CHECK(mn.size() >= 2 && approx(mn[0], -20.0, 0.02),
          "c04: Mmin span1 got %.2f want -20.00", safe_at(mn, 0));
    CHECK(mn.size() >= 2 && approx(mn[1], -20.0, 0.02),
          "c04: Mmin span2 got %.2f want -20.00", safe_at(mn, 1));
    CHECK(r.size() >= 3 && approx(r[1], 50.0, 0.02),
          "c04: R_int got %.2f want 50.00", safe_at(r, 1));
    CHECK(r.size() >= 3 && approx(r[0], 15.0, 0.02),
          "c04: R0 got %.2f want 15.00", safe_at(r, 0));
    CHECK(r.size() >= 3 && approx(r[2], 15.0, 0.02),
          "c04: R2 got %.2f want 15.00", safe_at(r, 2));
    std::remove((dir + "/in04.txt").c_str());
    std::remove((dir + "/out04.txt").c_str());
    return g_fails;
}

/* 2 equal spans L=4,4, perm 10 + live 5, FACTORS 1.35 1.5:
 * characteristic hogging M=-15L^2/8=-30; design M=-(1.35*10+1.5*5)L^2/8=-42;
 * interior R char 5/4*15*4=75, design 5/4*21*4=105 */
static int c05_factor_cont2(const std::string& dir) {
    write_file(dir + "/in05.txt",
               "SPANS 4 4\nINERTIA 3.69e-5 3.69e-5\nELASTICITY 2.1e8\n"
               "CONSTRAINTS -1 0 -1 0 -1 0\n"
               "LOAD 1 1 10 5 0 0\nLOAD 2 1 10 5 0 0\n"
               "FACTORS 1.35 1.5\n");
    std::string out;
    int rc = run_cmd("cba -i " + dir + "/in05.txt -o " + dir + "/out05.txt", out);
    CHECK(rc == 0, "c05: cba exited %d", rc);
    if (rc != 0) return g_fails;
    std::string text = read_file(dir + "/out05.txt");
    std::vector<double> mnc = parse_row(text, "Mmin:", 0);
    std::vector<double> mnd = parse_row(text, "Mmin:", 1);
    std::vector<double> rc_max = parse_row(text, "Rmax:", 0);
    std::vector<double> rd_max = parse_row(text, "Rmax:", 1);
    CHECK(mnc.size() >= 2 && approx(mnc[0], -30.0, 0.02),
          "c05: char Mmin s1 got %.2f want -30.00", safe_at(mnc, 0));
    CHECK(mnc.size() >= 2 && approx(mnc[1], -30.0, 0.02),
          "c05: char Mmin s2 got %.2f want -30.00", safe_at(mnc, 1));
    CHECK(mnd.size() >= 2 && approx(mnd[0], -42.0, 0.02),
          "c05: des Mmin s1 got %.2f want -42.00", safe_at(mnd, 0));
    CHECK(mnd.size() >= 2 && approx(mnd[1], -42.0, 0.02),
          "c05: des Mmin s2 got %.2f want -42.00", safe_at(mnd, 1));
    CHECK(rc_max.size() >= 3 && approx(rc_max[1], 75.0, 0.02),
          "c05: char R_int got %.2f want 75.00", safe_at(rc_max, 1));
    CHECK(rd_max.size() >= 3 && approx(rd_max[1], 105.0, 0.02),
          "c05: des R_int got %.2f want 105.00", safe_at(rd_max, 1));
    std::remove((dir + "/in05.txt").c_str());
    std::remove((dir + "/out05.txt").c_str());
    return g_fails;
}

/* upstream README example: 2 spans 5.8/4.2, p=10, q=5, factors 1.35/1.5
 * M_B = -w(L1^3+L2^3)/(8(L1+L2)): char w=15 -> -50.475 (~ -50.47),
 * design w=21 -> -70.665 (~ -70.67); interior R full-load char/design:
 * R_B = w(L1+L2) - (wL1/2 + M_B/L1) - (wL2/2 + M_B/L2) = 95.72 / 134.01 */
static int c06_readme_example(const std::string& dir) {
    write_file(dir + "/in06.txt",
               "SPANS 5.8 4.2\nINERTIA 3.69e-5 3.69e-5\nELASTICITY 2.1e8\n"
               "CONSTRAINTS -1 0 -1 0 -1 0\n"
               "LOAD 1 1 10 5 0 0\nLOAD 2 1 10 5 0 0\n"
               "FACTORS 1.35 1.5\n");
    std::string out;
    int rc = run_cmd("cba -i " + dir + "/in06.txt -o " + dir + "/out06.txt", out);
    CHECK(rc == 0, "c06: cba exited %d", rc);
    if (rc != 0) return g_fails;
    std::string text = read_file(dir + "/out06.txt");
    const double mb_c = -15.0 * (195.112 + 74.088) / 80.0; /* -50.475 */
    const double mb_d = -21.0 * (195.112 + 74.088) / 80.0; /* -70.665 */
    std::vector<double> mnc = parse_row(text, "Mmin:", 0);
    std::vector<double> mnd = parse_row(text, "Mmin:", 1);
    std::vector<double> rc_max = parse_row(text, "Rmax:", 0);
    std::vector<double> rd_max = parse_row(text, "Rmax:", 1);
    CHECK(mnc.size() >= 2 && approx(mnc[0], mb_c, 0.02),
          "c06: char Mmin s1 got %.2f want %.2f", safe_at(mnc, 0), mb_c);
    CHECK(mnc.size() >= 2 && approx(mnc[1], mb_c, 0.02),
          "c06: char Mmin s2 got %.2f want %.2f", safe_at(mnc, 1), mb_c);
    CHECK(mnd.size() >= 2 && approx(mnd[0], mb_d, 0.02),
          "c06: des Mmin s1 got %.2f want %.2f", safe_at(mnd, 0), mb_d);
    CHECK(mnd.size() >= 2 && approx(mnd[1], mb_d, 0.02),
          "c06: des Mmin s2 got %.2f want %.2f", safe_at(mnd, 1), mb_d);
    CHECK(rc_max.size() >= 3 && approx(rc_max[1], 95.72, 0.03),
          "c06: char R_int got %.2f want 95.72", safe_at(rc_max, 1));
    CHECK(rd_max.size() >= 3 && approx(rd_max[1], 134.01, 0.03),
          "c06: des R_int got %.2f want 134.01", safe_at(rd_max, 1));
    std::remove((dir + "/in06.txt").c_str());
    std::remove((dir + "/out06.txt").c_str());
    return g_fails;
}

/* no arguments -> usage on stdout, exit code 1 */
static int c07_no_args(const std::string& dir) {
    std::string out;
    int rc = run_cmd("cba", out);
    CHECK(rc == 1, "c07: exit got %d want 1", rc);
    if (rc != 1) return g_fails;
    CHECK(out.find("usage: cba") != std::string::npos,
          "c07: usage text missing from output");
    return g_fails;
}

/* nonexistent input file -> error on stderr, exit code 1 */
static int c08_missing_input(const std::string& dir) {
    std::string out;
    int rc = run_cmd("cba -i " + dir + "/does-not-exist.txt", out);
    CHECK(rc == 1, "c08: exit got %d want 1", rc);
    if (rc != 1) return g_fails;
    CHECK(out.find("unable to open input-file") != std::string::npos,
          "c08: missing-input message missing: %s", out.c_str());
    return g_fails;
}

/* input without SPANS -> 'geometry not right', exit code 1 */
static int c09_bad_geometry(const std::string& dir) {
    write_file(dir + "/in09.txt", "LOAD 1 1 10 0 0 0\n");
    std::string out;
    int rc = run_cmd("cba -i " + dir + "/in09.txt", out);
    CHECK(rc == 1, "c09: exit got %d want 1", rc);
    if (rc != 1) {
        std::remove((dir + "/in09.txt").c_str());
        return g_fails;
    }
    CHECK(out.find("geometry not right") != std::string::npos,
          "c09: geometry message missing: %s", out.c_str());
    std::remove((dir + "/in09.txt").c_str());
    return g_fails;
}

/* input without LOAD -> 'no loads', exit code 1 */
static int c10_no_loads(const std::string& dir) {
    write_file(dir + "/in10.txt", "SPANS 4.0\n");
    std::string out;
    int rc = run_cmd("cba -i " + dir + "/in10.txt", out);
    CHECK(rc == 1, "c10: exit got %d want 1", rc);
    if (rc != 1) {
        std::remove((dir + "/in10.txt").c_str());
        return g_fails;
    }
    CHECK(out.find("no loads") != std::string::npos,
          "c10: no-loads message missing: %s", out.c_str());
    std::remove((dir + "/in10.txt").c_str());
    return g_fails;
}

/* -o file must equal console output; -p plot: header + 101 rows * nf + 1 */
static int c11_outfile_plot(const std::string& dir) {
    write_file(dir + "/in11.txt",
               "SPANS 8.0\nINERTIA 3.69e-5\nELASTICITY 2.1e8\n"
               "LOAD 1 1 20 0 0 0\n");
    std::string stdout_text;
    int rc = run_cmd("cba -i " + dir + "/in11.txt -o " + dir + "/out11.txt"
                     " -p " + dir + "/plot11.dat", stdout_text);
    CHECK(rc == 0, "c11: cba exited %d", rc);
    if (rc != 0) {
        std::remove((dir + "/in11.txt").c_str());
        return g_fails;
    }
    std::string file_text = read_file(dir + "/out11.txt");
    CHECK(!file_text.empty(), "c11: -o output file missing/empty");
    CHECK(file_text == stdout_text,
          "c11: -o file differs from stdout (len %zu vs %zu)",
          file_text.size(), stdout_text.size());
    std::string plot = read_file(dir + "/plot11.dat");
    CHECK(plot.find("#x") != std::string::npos, "c11: plot header missing");
    int lines = 0;
    for (char ch : plot)
        if (ch == '\n') ++lines;
    CHECK(lines == 103, "c11: plot lines got %d want 103 (1 header+1 blank+101 rows)", lines);
    std::istringstream ps(plot);
    std::string row;
    std::getline(ps, row); /* header */
    std::getline(ps, row); /* blank */
    std::getline(ps, row); /* first data row: x Mmax Mmin Vmax Vmin dmax dmin */
    int toks = 0;
    std::istringstream ts(row);
    std::string t;
    while (ts >> t) ++toks;
    CHECK(toks == 7, "c11: plot data row tokens got %d want 7", toks);
    std::remove((dir + "/in11.txt").c_str());
    std::remove((dir + "/out11.txt").c_str());
    std::remove((dir + "/plot11.dat").c_str());
    return g_fails;
}

int main(int argc, char** argv) {
    if (argc != 2) {
        std::fprintf(stderr,
                     "usage: test_cba <case|c01_udl_single|...|c11_outfile_plot>\n");
        return 2;
    }
    const std::string dir = ".";
    int fails = 0;
    const std::string c = argv[1];
    if (c == "c01_udl_single") fails = c01_udl_single(dir);
    else if (c == "c02_point_mid") fails = c02_point_mid(dir);
    else if (c == "c03_point_quarter") fails = c03_point_quarter(dir);
    else if (c == "c04_cont2_udl") fails = c04_cont2_udl(dir);
    else if (c == "c05_factor_cont2") fails = c05_factor_cont2(dir);
    else if (c == "c06_readme_example") fails = c06_readme_example(dir);
    else if (c == "c07_no_args") fails = c07_no_args(dir);
    else if (c == "c08_missing_input") fails = c08_missing_input(dir);
    else if (c == "c09_bad_geometry") fails = c09_bad_geometry(dir);
    else if (c == "c10_no_loads") fails = c10_no_loads(dir);
    else if (c == "c11_outfile_plot") fails = c11_outfile_plot(dir);
    else {
        std::fprintf(stderr, "test_cba: unknown case '%s'\n", c.c_str());
        return 2;
    }
    std::printf("[%s] %d assertions, %d failed\n", c.c_str(), g_asserts, fails);
    return fails == 0 ? 0 : 1;
}
