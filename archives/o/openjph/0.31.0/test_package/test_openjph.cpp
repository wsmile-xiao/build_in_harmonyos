/*
 * test_openjph.cpp — Consumer test for the openjph Conan package
 *
 * Modes:
 *   gen                     : generate test_input.ppm (P3, 64x64 RGB gradient)
 *   verify <a.ppm> <b.ppm>  : parse both PPMs (P3/P6, comment-tolerant) and
 *                             compare pixels byte-exactly (lossless check)
 *   api <file.j2c>          : library API smoke — version macros + decode a
 *                             small codestream (init + decode + release)
 */
#include <cctype>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>

#include "openjph/ojph_version.h"
#include "openjph/ojph_file.h"
#include "openjph/ojph_mem.h"
#include "openjph/ojph_params.h"
#include "openjph/ojph_codestream.h"

static const int IMG_W = 64;
static const int IMG_H = 64;

// ---------------- PPM helpers ----------------

struct PPM {
    int w = 0, h = 0, maxval = 0;
    std::vector<unsigned char> pixels; // RGB triplets
};

static void skip_ws_and_comments(FILE* f) {
    int c;
    while ((c = fgetc(f)) != EOF) {
        if (c == '#') {
            while ((c = fgetc(f)) != EOF && c != '\n') {
            }
        } else if (!isspace(c)) {
            ungetc(c, f);
            break;
        }
    }
}

static bool read_ppm(const char* path, PPM& ppm) {
    FILE* f = fopen(path, "rb");
    if (!f) {
        fprintf(stderr, "FAIL: cannot open %s\n", path);
        return false;
    }
    char magic[3] = {0};
    if (fscanf(f, "%2s", magic) != 1) {
        fclose(f);
        return false;
    }
    bool binary = (strcmp(magic, "P6") == 0);
    if (strcmp(magic, "P3") != 0 && !binary) {
        fprintf(stderr, "FAIL: unsupported PPM magic '%s'\n", magic);
        fclose(f);
        return false;
    }
    skip_ws_and_comments(f);
    if (fscanf(f, "%d", &ppm.w) != 1) {
        fclose(f);
        return false;
    }
    skip_ws_and_comments(f);
    if (fscanf(f, "%d", &ppm.h) != 1) {
        fclose(f);
        return false;
    }
    skip_ws_and_comments(f);
    if (fscanf(f, "%d", &ppm.maxval) != 1) {
        fclose(f);
        return false;
    }
    fgetc(f); // single whitespace after maxval
    size_t n = (size_t)ppm.w * ppm.h * 3;
    ppm.pixels.resize(n);
    if (binary) {
        if (fread(ppm.pixels.data(), 1, n, f) != n) {
            fclose(f);
            return false;
        }
    } else {
        for (size_t i = 0; i < n; ++i) {
            int v;
            if (fscanf(f, "%d", &v) != 1) {
                fclose(f);
                return false;
            }
            ppm.pixels[i] = (unsigned char)(v & 0xFF);
        }
    }
    fclose(f);
    return true;
}

// ---------------- mode: gen ----------------

static int gen_ppm(const char* path) {
    // 注意：上游 ppm_in::open 只接受 P5/P6 二进制格式（P3 文本不支持，报 0x03000003）
    FILE* f = fopen(path, "wb");
    if (!f) {
        fprintf(stderr, "FAIL: cannot write %s\n", path);
        return 1;
    }
    fprintf(f, "P6\n%d %d\n255\n", IMG_W, IMG_H);
    for (int y = 0; y < IMG_H; ++y) {
        for (int x = 0; x < IMG_W; ++x) {
            unsigned char px[3];
            px[0] = (unsigned char)((x * 255) / (IMG_W - 1));
            px[1] = (unsigned char)((y * 255) / (IMG_H - 1));
            px[2] = (unsigned char)(((x + y) * 255) / (IMG_W + IMG_H - 2));
            fwrite(px, 1, 3, f);
        }
    }
    fclose(f);
    printf("generated %s (%dx%d RGB P6 binary)\n", path, IMG_W, IMG_H);
    return 0;
}

// ---------------- mode: verify ----------------

static int verify_ppm(const char* a, const char* b) {
    PPM pa, pb;
    if (!read_ppm(a, pa) || !read_ppm(b, pb)) {
        return 1;
    }
    if (pa.w != pb.w || pa.h != pb.h) {
        fprintf(stderr, "FAIL: size mismatch %dx%d vs %dx%d\n", pa.w, pa.h, pb.w, pb.h);
        return 1;
    }
    if (pa.pixels.size() != pb.pixels.size()) {
        fprintf(stderr, "FAIL: pixel count mismatch\n");
        return 1;
    }
    size_t mismatches = 0;
    for (size_t i = 0; i < pa.pixels.size(); ++i) {
        if (pa.pixels[i] != pb.pixels[i]) {
            if (mismatches < 5) {
                fprintf(stderr, "  pixel[%zu]: %u vs %u\n", i, pa.pixels[i], pb.pixels[i]);
            }
            ++mismatches;
        }
    }
    if (mismatches > 0) {
        fprintf(stderr, "FAIL: %zu/%zu pixels differ\n", mismatches, pa.pixels.size());
        return 1;
    }
    printf("verify OK: %zu bytes identical (%dx%d, lossless round-trip)\n",
           pa.pixels.size(), pa.w, pa.h);
    return 0;
}

// ---------------- mode: api (library smoke) ----------------

// 按上游 ojph_expand 的主循环完整解码：create() 后必须 pull 所有行
static void pull_all_lines(ojph::codestream& codestream) {
    ojph::param_siz siz = codestream.access_siz();
    if (codestream.is_planar()) {
        for (ojph::ui32 c = 0; c < siz.get_num_components(); ++c) {
            ojph::ui32 height = siz.get_recon_height(c);
            for (ojph::ui32 i = height; i > 0; --i) {
                ojph::ui32 comp_num = 0;
                ojph::line_buf* line = codestream.pull(comp_num);
                if (line == nullptr) {
                    break;
                }
            }
        }
    } else {
        ojph::ui32 height = siz.get_recon_height(0);
        for (ojph::ui32 i = 0; i < height; ++i) {
            for (ojph::ui32 c = 0; c < siz.get_num_components(); ++c) {
                ojph::ui32 comp_num = 0;
                ojph::line_buf* line = codestream.pull(comp_num);
                if (line == nullptr) {
                    break;
                }
            }
        }
    }
}

static int api_smoke(const char* j2c_path) {
    if (OPENJPH_VERSION_MAJOR != 0 || OPENJPH_VERSION_MINOR != 31 ||
        OPENJPH_VERSION_PATCH != 0) {
        fprintf(stderr, "FAIL: unexpected version %d.%d.%d\n", OPENJPH_VERSION_MAJOR,
                OPENJPH_VERSION_MINOR, OPENJPH_VERSION_PATCH);
        return 1;
    }
    printf("OpenJPH version macro: %d.%d.%d\n", OPENJPH_VERSION_MAJOR,
           OPENJPH_VERSION_MINOR, OPENJPH_VERSION_PATCH);

    // init + decode a small codestream + release.
    // 注意：codestream::close() 内部会关闭 infile（infile->close()），
    // 与上游 ojph_expand 一致，不要在 codestream.close() 之后再显式
    // close j2c_infile（否则对已置 NULL 的 fh 二次 fclose 会崩溃）。
    ojph::j2c_infile infile;
    infile.open(j2c_path);
    fprintf(stderr, "[api] j2c_infile.open OK\n");
    ojph::codestream codestream;
    codestream.read_headers(&infile);
    fprintf(stderr, "[api] read_headers OK\n");
    codestream.restrict_input_resolution(0, 0);
    codestream.create();
    fprintf(stderr, "[api] create OK\n");
    pull_all_lines(codestream);
    fprintf(stderr, "[api] pull_all_lines OK\n");
    codestream.close();
    fprintf(stderr, "[api] close OK (input closed internally)\n");
    printf("API decode smoke OK: %s\n", j2c_path);
    return 0;
}

// ---------------- main ----------------

int main(int argc, char** argv) {
    if (argc >= 2 && strcmp(argv[1], "gen") == 0) {
        return gen_ppm("test_input.ppm");
    }
    if (argc >= 2 && strcmp(argv[1], "verify") == 0 && argc == 4) {
        return verify_ppm(argv[2], argv[3]);
    }
    if (argc >= 2 && strcmp(argv[1], "api") == 0 && argc == 3) {
        return api_smoke(argv[2]);
    }
    fprintf(stderr, "usage: %s gen | verify <a.ppm> <b.ppm> | api <file.j2c>\n", argv[0]);
    return 2;
}