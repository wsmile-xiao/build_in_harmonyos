// barkeep 0.1.5 — 消费者测试（test_package / L1）
//
// 从**已安装包头** `#include <barkeep/barkeep.h>` 取用（不是源码树），在**无 TTY**
// （stdout 走管道——鸿蒙设备 HiShell 非交互执行与 CI worker 的真实形态）下走
// barkeep 的 `no_tty` 渲染路径，断言渲染输出内容与 API 行为。
// 显式计数、任一失败即进程非零退出；不依赖 assert/NDEBUG（-DNDEBUG 下同样生效）。
//
// 这是「鸿蒙特有测试」行的用例来源（不进上游用例分母），输出形态：
//   barkeep consumer checks: N run, M failed

#include <barkeep/barkeep.h>

#include <atomic>
#include <chrono>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

namespace bk = barkeep;

namespace {

int checks = 0;
int failed = 0;

void expect(bool cond, const char* what, int line) {
  ++checks;
  if (!cond) {
    ++failed;
    std::cerr << "[FAIL] line " << line << ": " << what << "\n";
  }
}

std::vector<std::string> split_lines(const std::string& s) {
  std::vector<std::string> out;
  std::string cur;
  for (char c : s) {
    if (c == '\n') {
      out.push_back(cur);
      cur.clear();
    } else {
      cur.push_back(c);
    }
  }
  if (!cur.empty()) { out.push_back(cur); }
  return out;
}

}  // namespace

#define EXPECT(cond) expect(static_cast<bool>(cond), #cond, __LINE__)

int main() {
  using namespace std::chrono_literals;

  // 1) 打包版本与配方版本一致
  EXPECT(std::string(BARKEEP_VERSION) == "0.1.5");

  // 2) Counter：no_tty 渲染路径（无 \r 的逐帧换行），最终计数正确
  {
    std::stringstream out;
    int amount = 0;
    auto ctr = bk::Counter(&amount, {
                                        .out = &out,
                                        .message = "hb-count",
                                        .interval = 0.001,
                                        .no_tty = true,
                                    });
    for (int i = 0; i < 40; i++) {
      amount++;
      std::this_thread::sleep_for(1ms);
    }
    ctr->done();

    const std::string text = out.str();
    EXPECT(!text.empty());
    EXPECT(text.back() == '\n');                 // no_tty 收帧以换行结束
    EXPECT(text.find("hb-count") != std::string::npos);
    EXPECT(text.find('4') != std::string::npos); // 终值 40 被渲染出来
    EXPECT(split_lines(text).size() >= 1);
  }

  // 3) Counter + std::atomic（上游 ProgressTypeList 覆盖的原子类型面）
  {
    std::stringstream out;
    std::atomic<size_t> toks{0};
    auto ctr = bk::Counter(&toks, {
                                      .out = &out,
                                      .message = "hb-atomic",
                                      .speed = 1,
                                      .speed_unit = "tok/s",
                                      .interval = 0.001,
                                      .no_tty = true,
                                      .show = false,
                                    });
    ctr->show();
    toks += 7;
    ctr->done();
    const std::string text = out.str();
    EXPECT(text.find("hb-atomic") != std::string::npos);
    EXPECT(text.find("tok/s") != std::string::npos);  // 自定义速度单位生效
    EXPECT(text.find("7") != std::string::npos);
  }

  // 4) ProgressBar：total 语义 + 完成帧
  {
    std::stringstream out;
    size_t progress = 0;
    auto bar = bk::ProgressBar(&progress, {
                                              .out = &out,
                                              .total = 20,
                                              .message = "hb-bar",
                                              .interval = 0.001,
                                              .no_tty = true,
                                          });
    for (int i = 0; i < 20; i++) {
      progress++;
      std::this_thread::sleep_for(1ms);
    }
    bar->done();

    const std::string text = out.str();
    EXPECT(!text.empty());
    EXPECT(text.find("hb-bar") != std::string::npos);
    EXPECT(text.find("100.00%") != std::string::npos);  // 终帧到达 total
    EXPECT(text.find("20/20") != std::string::npos);     // 计数终值
    EXPECT(text.find('|') != std::string::npos);         // 默认 Blocks 样式条形帧
  }

  // 5) 复合显示：ProgressBar | Counter（operator| 组合面）
  {
    std::stringstream out;
    std::atomic<size_t> sents{0}, toks{0};
    auto comp = bk::ProgressBar(&sents, {
                                            .out = &out,
                                            .total = 10,
                                            .message = "hb-sents",
                                            .interval = 0.001,
                                            .show = false,
                                        }) |
                bk::Counter(&toks, {
                                       .out = &out,
                                       .message = "hb-toks",
                                       .speed = 1,
                                       .speed_unit = "tok/s",
                                       .show = false,
                                   });
    comp->show();
    for (int i = 0; i < 10; i++) {
      sents++;
      toks++;
      std::this_thread::sleep_for(1ms);
    }
    comp->done();

    const std::string text = out.str();
    EXPECT(text.find("hb-sents") != std::string::npos);
    EXPECT(text.find("hb-toks") != std::string::npos);
  }

  // 6) Status：消息更新与读回
  {
    std::stringstream out;
    auto stat = bk::Status({
        .out = &out,
        .message = "hb-status-0",
        .interval = 0.001,
        .no_tty = true,
    });
    std::this_thread::sleep_for(5ms);
    stat->message("hb-status-1");
    stat->done();
    const std::string text = out.str();
    EXPECT(stat->message() == "hb-status-1");
    EXPECT(text.find("hb-status-1") != std::string::npos);
  }

  // 7) Animation：show=false 静默路径 + 正常结束
  {
    std::stringstream out;
    auto anim = bk::Animation({
        .out = &out,
        .message = "hb-anim",
        .interval = 0.001,
        .no_tty = true,
        .show = false,
    });
    anim->done();
    EXPECT(out.str().empty());  // show=false 不产生输出
  }

  // 8) IterableBar：区间 for 遍历完整性（50 元素全访问）+ 渲染
  {
    std::stringstream out;
    std::vector<int> things(50, 3);
    long sum = 0;
    for (auto& thing : bk::IterableBar(things, {
                                                   .out = &out,
                                                   .message = "hb-iter",
                                                   .interval = 0.001,
                                                   .no_tty = true,
                                               })) {
      sum += thing;
      std::this_thread::sleep_for(0.2ms);
    }
    EXPECT(sum == 150);
    EXPECT(out.str().find("hb-iter") != std::string::npos);
  }

  // 9) 非法组合必须抛异常（上游 [edges] 面：显示**运行中**才禁止自我组合）
  {
    std::stringstream out;
    size_t dummy = 0;
    auto disp = bk::Counter(&dummy, {.out = &out, .show = false});
    disp->show();
    bool threw = false;
    try {
      auto bad = disp | disp;
      (void)bad;
    } catch (const std::exception&) {
      threw = true;
    } catch (...) {
      threw = true;
    }
    disp->done();
    EXPECT(threw);
  }

  // 10) 无 TTY 形态下 stdout 不产生 \r 控制序列（管道执行安全）
  {
    std::stringstream out;
    size_t progress = 0;
    auto bar = bk::ProgressBar(&progress, {
                                              .out = &out,
                                              .total = 5,
                                              .message = "hb-notty",
                                              .interval = 0.001,
                                              .no_tty = true,
                                          });
    progress = 5;
    bar->done();
    EXPECT(out.str().find('\r') == std::string::npos);
  }

  std::cout << "barkeep consumer checks: " << checks << " run, " << failed
            << " failed\n";
  return failed == 0 ? 0 : 1;
}
