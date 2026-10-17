/* HarmonyOS PC replacement for upstream's System V shared-memory backend.
 * The public class API remains unchanged; only its private storage differs.
 * SPDX-License-Identifier: LGPL-2.1-or-later
 */
#ifndef _SHMDATA_SYSV_SHM_H_
#define _SHMDATA_SYSV_SHM_H_

#include <sys/ipc.h>
#include <sys/types.h>
#include <cstddef>
#include "./abstract-logger.hpp"
#include "./safe-bool-idiom.hpp"

namespace shmdata {

bool force_shm_cleaning(key_t key, AbstractLogger* log);

class sysVShm : public SafeBoolIdiom {
 public:
  sysVShm(key_t key, size_t size, AbstractLogger* log, bool owner = false,
          mode_t unix_permission = 0600);
  ~sysVShm();
  sysVShm() = delete;
  sysVShm(const sysVShm&) = delete;
  sysVShm& operator=(const sysVShm&) = delete;
  sysVShm& operator=(sysVShm&&) = default;

  void* get_mem() { return shm_; }
  std::size_t get_size() const { return size_; }
  static unsigned long get_shmmax(AbstractLogger* log);
  static unsigned long get_shmmni(AbstractLogger* log);

 private:
  AbstractLogger* log_;
  key_t key_;
  size_t size_;
  int fd_{-1};
  bool owner_;
  void* shm_{(void*)-1};
  char name_[64]{};
  bool is_valid() const final;
};

}  // namespace shmdata
#endif
