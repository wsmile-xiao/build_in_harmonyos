#include <iostream>
#include <string>
#include <thread>
#include <tuple>
#include <vector>

#include <CsLibGuarded/cs_cow_guarded.h>
#include <CsLibGuarded/cs_lr_guarded.h>
#include <CsLibGuarded/cs_plain_guarded.h>
#include <CsLibGuarded/cs_rcu_guarded.h>
#include <CsLibGuarded/cs_rcu_list.h>
#include <CsLibGuarded/cs_shared_guarded.h>

// Exercise the second upstream include root as well; upstream installs
// headers to include/CsLibGuarded/ and exposes both include directories.
#include <cs_lock_guards.h>

namespace {

int g_failures = 0;

void check(bool condition, const char *message)
{
   if (!condition) {
      std::cerr << "FAIL: " << message << std::endl;
      ++g_failures;
   }
}

}  // namespace

int main()
{
   using libguarded::cow_guarded;
   using libguarded::lr_guarded;
   using libguarded::plain_guarded;
   using libguarded::rcu_guarded;
   using libguarded::rcu_list;
   using libguarded::shared_guarded;

   // 1) plain_guarded: exclusive write, then const read through handles.
   plain_guarded<int> plain(41);
   {
      auto h = plain.lock();
      check(h != nullptr, "plain_guarded::lock returns a valid handle");
      *h += 1;
   }
   {
      auto ch = plain.lock();
      check(ch != nullptr && *ch == 42, "plain_guarded value survives handle scope");
   }

   // 2) plain_guarded::try_lock contention.
   {
      auto h = plain.lock();
      check(h != nullptr, "plain_guarded held for contention check");
      auto t = plain.try_lock();
      check(t == nullptr, "try_lock fails while the object is locked");
   }

   // 3) shared_guarded: exclusive write, then shared read.
   shared_guarded<int> shared(0);
   {
      auto h = shared.lock();
      *h = 7;
   }
   {
      auto sh = shared.lock_shared();
      check(sh != nullptr && *sh == 7, "shared_guarded shared read sees exclusive write");
   }

   // 4) lr_guarded: modify() then non-blocking snapshot read.
   lr_guarded<std::string> lr("alpha");
   lr.modify([](std::string &s) { s += "-beta"; });
   {
      auto snap = lr.lock_shared();
      check(snap != nullptr && *snap == "alpha-beta", "lr_guarded snapshot sees modify()");
   }

   // 5) rcu_guarded over rcu_list: lock_write / lock_read handles.
   rcu_guarded<rcu_list<int>> rcu;
   {
      auto wh = rcu.lock_write();
      wh->push_back(1);
      wh->push_back(2);
      wh->push_back(3);
   }
   {
      auto rh = rcu.lock_read();
      int count = 0;
      for (const int &item : *rh) {
         (void)item;
         ++count;
      }
      check(count == 3, "rcu read handle sees all rcu_list writes");
   }

   // 6) cow_guarded: write handle commits on release, shared_ptr read.
   cow_guarded<int> cow(10);
   {
      auto h = cow.lock();
      check(h != nullptr, "cow_guarded::lock returns a valid handle");
      *h = 12;
   }
   {
      auto sh = cow.lock_shared();
      check(sh && *sh == 12, "cow_guarded commit is visible to shared readers");
   }

   // 7) cow_guarded::cancel discards the modified copy.
   {
      auto h = cow.lock();
      *h = 999;
      h.cancel();
   }
   {
      auto sh = cow.lock_shared();
      check(sh && *sh == 12, "cow_guarded cancel() discards the modified copy");
   }

   // 8) lock_guards: ordered try-lock of two guards at once.
   plain_guarded<int> ga(1);
   plain_guarded<int> gb(2);
   {
      auto locks = libguarded::lock_guards(ga, gb);
      check(std::get<0>(locks) != nullptr && std::get<1>(locks) != nullptr,
            "lock_guards acquires both handles");
      *std::get<0>(locks) = 11;
      *std::get<1>(locks) = 22;
   }
   {
      auto ha = ga.lock();
      auto hb = gb.lock();
      check(*ha == 11 && *hb == 22, "lock_guards writes are visible after release");
   }

   // 9) Concurrency stress: 4 threads x 500 increments through
   // plain_guarded handles; the guard must serialize them.
   plain_guarded<long> counter(0);
   std::vector<std::thread> workers;
   for (int t = 0; t < 4; ++t) {
      workers.emplace_back([&counter]() {
         for (int i = 0; i < 500; ++i) {
            auto h = counter.lock();
            *h += 1;
         }
      });
   }
   for (auto &w : workers) {
      w.join();
   }
   {
      auto h = counter.lock();
      check(*h == 2000, "plain_guarded serializes concurrent increments");
   }

   // 10) Concurrency stress through shared_guarded writers.
   shared_guarded<long> scounter(0);
   std::vector<std::thread> swriters;
   for (int t = 0; t < 2; ++t) {
      swriters.emplace_back([&scounter]() {
         for (int i = 0; i < 250; ++i) {
            auto h = scounter.lock();
            *h += 2;
         }
      });
   }
   for (auto &w : swriters) {
      w.join();
   }
   {
      auto sh = scounter.lock_shared();
      check(*sh == 1000, "shared_guarded serializes concurrent writers");
   }

   if (g_failures != 0) {
      std::cerr << g_failures << " consumer checks failed" << std::endl;
      return 1;
   }

   std::cout << "CsLibGuarded consumer checks passed: 10" << std::endl;
   return 0;
}
