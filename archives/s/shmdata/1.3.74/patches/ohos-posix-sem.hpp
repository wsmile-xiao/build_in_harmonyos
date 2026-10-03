/* HarmonyOS PC replacement for upstream's System V semaphore backend.
 * The public class API remains unchanged; only its private storage differs.
 * SPDX-License-Identifier: LGPL-2.1-or-later
 */
#ifndef _SHMDATA_SYSV_SEM_H_
#define _SHMDATA_SYSV_SEM_H_

#include <pthread.h>
#include <sys/ipc.h>
#include <sys/types.h>
#include "./abstract-logger.hpp"
#include "./safe-bool-idiom.hpp"

namespace shmdata {

class WriteLock;
class ReadLock;
bool force_semaphore_cleaning(key_t key, AbstractLogger* log);

class sysVSem : public SafeBoolIdiom {
  friend WriteLock;
  friend ReadLock;

 public:
  sysVSem(key_t key, AbstractLogger* log, bool owner = false,
          mode_t unix_permission = 0600);
  ~sysVSem();
  sysVSem() = delete;
  sysVSem(const sysVSem&) = delete;
  sysVSem& operator=(const sysVSem&) = delete;
  sysVSem& operator=(sysVSem&&) = default;
  void cancel_commited_reader();

 private:
  struct State {
    pthread_mutex_t mutex;
    pthread_cond_t changed;
    unsigned pending_readers;
    bool writer_active;
    unsigned magic;
  };
  key_t key_;
  bool owner_;
  int fd_{-1};
  State* state_{nullptr};
  char name_[64]{};
  AbstractLogger* log_;
  bool is_valid() const final;
};

class ReadLock : public SafeBoolIdiom {
 public:
  ReadLock(sysVSem* sem);
  ~ReadLock();
  ReadLock() = delete;
  ReadLock(const ReadLock&) = delete;
  ReadLock& operator=(const ReadLock&) = delete;
  ReadLock& operator=(ReadLock&&) = delete;

 private:
  sysVSem* sem_;
  bool valid_{false};
  bool is_valid() const final { return valid_; }
};

class WriteLock : public SafeBoolIdiom {
 public:
  WriteLock(sysVSem* sem);
  ~WriteLock();
  WriteLock() = delete;
  WriteLock(const WriteLock&) = delete;
  WriteLock& operator=(const WriteLock&) = delete;
  WriteLock& operator=(WriteLock&&) = default;
  bool commit_readers(short num_readers);

 private:
  sysVSem* sem_;
  bool valid_{false};
  bool is_valid() const final { return valid_; }
};

}  // namespace shmdata
#endif
