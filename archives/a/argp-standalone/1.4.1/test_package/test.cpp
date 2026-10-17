#include <stdint.h>
#include <stddef.h>
#include <argp.h>

#include <cstdio>
#include <cstring>
#include <string>

// argp-standalone 1.4.1 —— 真实命令行解析往返验证（R34：实质调用 argp_parse）。
// OHOS musl 不提供 argp（glibc 专属 API），本测试验证 libargp.a 补齐后
// argp_parse 可正常解析长/短选项、取值、位置参数，并拒绝未知选项。
// 断言集：
//   ① 长选项 --verbose 被识别
//   ② 带值短选项 -o FILE 取到值
//   ③ 长选项等号形式 --output=FILE 取到值
//   ④ 位置参数进 ARGP_KEY_ARG
//   ⑤ 未知选项返回非 0（ARGP_NO_EXIT 下不退进程）
//   ⑥ argp_program_version 可设置并读回
//   ⑦ 多个位置参数逐个进回调

const char *argp_program_version = "argp-probe 1.4.1";

static int failures = 0;

#define CHECK(cond, msg)                                                     \
  do {                                                                       \
    if (!(cond)) {                                                           \
      std::fprintf(stderr, "[FAIL] %s  (%s:%d)\n", msg, __FILE__, __LINE__); \
      ++failures;                                                            \
    } else {                                                                 \
      std::printf("[ok] %s\n", msg);                                         \
    }                                                                        \
  } while (0)

struct args {
  int verbose;
  std::string output;
  std::string positional;
  int n_args;
};

static struct argp_option options[] = {
    {"verbose", 'v', nullptr, 0, "verbose output", 0},
    {"output", 'o', "FILE", 0, "output file", 0},
    {nullptr, 0, nullptr, 0, nullptr, 0},
};

static error_t parse_opt(int key, char *arg, struct argp_state *state) {
  args *a = static_cast<args *>(state->input);
  switch (key) {
    case 'v': a->verbose = 1; break;
    case 'o': a->output = arg ? arg : ""; break;
    case ARGP_KEY_ARG:
      ++a->n_args;
      if (a->positional.empty()) a->positional = arg ? arg : "";
      break;
    default: return ARGP_ERR_UNKNOWN;
  }
  return 0;
}

static struct argp argp_conf = {options, parse_opt, "[ARG...]", "argp probe 1.4.1", nullptr, nullptr, nullptr};

static int run(int argc, const char **argv, args *a) {
  memset(a, 0, sizeof(*a));
  // argv 为 const 数组，argp_parse 需要可写 char*，拷贝一份
  char *cargv[16];
  for (int i = 0; i < argc && i < 15; ++i) cargv[i] = strdup(argv[i]);
  cargv[argc] = nullptr;
  const int rc = argp_parse(&argp_conf, argc, cargv, ARGP_NO_EXIT, nullptr, a);
  for (int i = 0; i < argc && i < 15; ++i) free(cargv[i]);
  return rc;
}

int main() {
  // ⑥
  CHECK(argp_program_version != nullptr
            && std::strcmp(argp_program_version, "argp-probe 1.4.1") == 0,
        "argp_program_version can be set and read back");

  // ① ② ④
  {
    const char *argv[] = {"prog", "--verbose", "-o", "out.txt", "input.bin", nullptr};
    args a;
    const int rc = run(5, argv, &a);
    CHECK(rc == 0, "parse --verbose -o out.txt input.bin returns 0");
    CHECK(a.verbose == 1, "long option --verbose recognized");
    CHECK(a.output == "out.txt", "short option -o got value out.txt");
    if (a.output != "out.txt") std::fprintf(stderr, "       got \"%s\"\n", a.output.c_str());
    CHECK(a.n_args == 1 && a.positional == "input.bin", "positional arg reaches ARGP_KEY_ARG");
  }

  // ③ equals form
  {
    const char *argv[] = {"prog", "--output=eq.txt", nullptr};
    args a;
    const int rc = run(2, argv, &a);
    CHECK(rc == 0 && a.output == "eq.txt", "long option equals form --output=eq.txt gets value");
    if (a.output != "eq.txt") std::fprintf(stderr, "       got \"%s\"\n", a.output.c_str());
  }

  // ⑦ multiple positionals
  {
    const char *argv[] = {"prog", "a", "b", "c", nullptr};
    args a;
    run(4, argv, &a);
    CHECK(a.n_args == 3, "all three positional args reach callback");
  }

  // ⑤ unknown option
  {
    const char *argv[] = {"prog", "--definitely-not-an-option", nullptr};
    args a;
    const int rc = run(2, argv, &a);
    CHECK(rc != 0, "unknown option returns non-zero (without exiting process)");
  }

  if (failures) {
    std::fprintf(stderr, "\nargp-standalone: %d assertion(s) failed\n", failures);
    return 1;
  }
  std::printf("\nargp-standalone 1.4.1: all assertions passed\n");
  return 0;
}
