#include <stdint.h>
#include <stddef.h>
#include <argp.h>

#include <cstdio>
#include <cstring>
#include <string>

// argp-standalone 1.5.0 —— 真实参数解析验证（非 dlopen 空壳）。
// OHOS 的 musl sysroot **没有 argp.h**（探针实测），elfutils 的命令行工具要用它，故补此包。
// 断言：定义一组选项，喂进构造好的 argv，核对解析结果：
//   ① 长选项 --verbose 被识别
//   ② 带值的短选项 -o FILE 取到值
//   ③ 长选项等号形式 --output=FILE 取到值
//   ④ 位置参数进 ARGP_KEY_ARG
//   ⑤ 未知选项返回非 0（ARGP_NO_EXIT 下不退进程）
//   ⑥ argp_program_version 可设置

const char *argp_program_version = "argp-probe 1.0";

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
    {"verbose", 'v', nullptr, 0, "详细输出", 0},
    {"output", 'o', "FILE", 0, "输出文件", 0},
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

static struct argp argp_conf = {options, parse_opt, "[ARG...]", "argp 探针", nullptr, nullptr, nullptr};

static int run(int argc, const char **argv, args *out) {
  *out = args{0, "", "", 0};
  return argp_parse(&argp_conf, argc, const_cast<char **>(argv),
                    ARGP_NO_EXIT | ARGP_SILENT, nullptr, out);
}

int main() {
  // ⑥
  CHECK(argp_program_version != nullptr
            && std::strcmp(argp_program_version, "argp-probe 1.0") == 0,
        "argp_program_version 可设置并读回");

  // ① ② ④
  {
    const char *argv[] = {"prog", "--verbose", "-o", "out.txt", "input.bin", nullptr};
    args a;
    const int rc = run(5, argv, &a);
    CHECK(rc == 0, "解析 --verbose -o out.txt input.bin 返回 0");
    CHECK(a.verbose == 1, "长选项 --verbose 被识别");
    CHECK(a.output == "out.txt", "短选项 -o 取到值 out.txt");
    if (a.output != "out.txt") std::fprintf(stderr, "       实得 \"%s\"\n", a.output.c_str());
    CHECK(a.n_args == 1 && a.positional == "input.bin", "位置参数进 ARGP_KEY_ARG");
  }

  // ③ 等号形式
  {
    const char *argv[] = {"prog", "--output=eq.txt", nullptr};
    args a;
    const int rc = run(2, argv, &a);
    CHECK(rc == 0 && a.output == "eq.txt", "长选项等号形式 --output=eq.txt 取到值");
    if (a.output != "eq.txt") std::fprintf(stderr, "       实得 \"%s\"\n", a.output.c_str());
  }

  // 多个位置参数
  {
    const char *argv[] = {"prog", "a", "b", "c", nullptr};
    args a;
    run(4, argv, &a);
    CHECK(a.n_args == 3, "三个位置参数都进回调");
  }

  // ⑤ 未知选项
  {
    const char *argv[] = {"prog", "--definitely-not-an-option", nullptr};
    args a;
    const int rc = run(2, argv, &a);
    CHECK(rc != 0, "未知选项返回非 0（且未退出进程）");
  }

  if (failures) {
    std::fprintf(stderr, "\nargp-standalone: %d 项断言失败\n", failures);
    return 1;
  }
  std::printf("\nargp-standalone 1.5.0: 全部断言通过\n");
  return 0;
}
