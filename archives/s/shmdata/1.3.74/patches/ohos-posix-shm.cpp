/* HarmonyOS PC POSIX shared-memory backend; System V IPC is seccomp-blocked.
 * SPDX-License-Identifier: LGPL-2.1-or-later
 */
#include "./sysv-shm.hpp"
#include <cerrno>
#include <cstdio>
#include <cstring>
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>

namespace shmdata {

static void segment_name(char* out, size_t length, key_t key) {
  snprintf(out, length, "/shmdata-segment-%08x", static_cast<unsigned>(key));
}

bool force_shm_cleaning(key_t key, AbstractLogger* log) {
  char name[64];
  segment_name(name, sizeof(name), key);
  if (shm_unlink(name) == 0) return true;
  if (errno != ENOENT) log->warning("shm_unlink: %", strerror(errno));
  return false;
}

sysVShm::sysVShm(key_t key, size_t size, AbstractLogger* log, bool owner,
                 mode_t unix_permission)
    : log_(log), key_(key), size_(size), owner_(owner) {
  if (key_ == -1) {
    log_->warning("ftok: %", strerror(errno));
    return;
  }
  // SysV shmat rejects a creator without owner read/write permission.
  // A newly created POSIX fd could still be mapped by its creator, so
  // preserve the original permission contract explicitly.
  if (owner_ && (unix_permission & 0600) != 0600) {
    errno = EACCES;
    log_->warning("shared memory owner permission: %", strerror(errno));
    return;
  }
  segment_name(name_, sizeof(name_), key_);
  // A reader may receive an update while the writer is replacing a resized
  // named segment.  The SysV implementation tolerates this handoff; wait
  // briefly for the replacement to become visible instead of mapping -1.
  for (int attempt = 0; attempt < 50; ++attempt) {
    fd_ = shm_open(name_, owner_ ? O_RDWR | O_CREAT | O_EXCL : O_RDWR,
                   unix_permission);
    if (fd_ < 0) {
      if (!owner_ && errno == ENOENT && attempt < 49) {
        usleep(1000);
        continue;
      }
      break;
    }
    if (!owner_) {
      struct stat info;
      if (fstat(fd_, &info) != 0) {
        close(fd_);
        fd_ = -1;
        break;
      }
      if (info.st_size <= 0 || (size_ && info.st_size < static_cast<off_t>(size_))) {
        close(fd_);
        fd_ = -1;
        if (attempt < 49) {
          usleep(1000);
          continue;
        }
        errno = EAGAIN;
      } else {
        size_ = static_cast<size_t>(info.st_size);
      }
    }
    break;
  }
  if (fd_ < 0) {
    log_->warning("shm_open: %", strerror(errno));
    return;
  }
  if (owner_) {
    if (size_ == 0 || ftruncate(fd_, static_cast<off_t>(size_)) != 0) {
      log_->warning("ftruncate: %", strerror(errno));
      return;
    }
  }
  shm_ = mmap(nullptr, size_, PROT_READ | PROT_WRITE, MAP_SHARED, fd_, 0);
  if (shm_ == MAP_FAILED) {
    log_->warning("mmap shared memory: %", strerror(errno));
    return;
  }
  // A newly created POSIX segment is zero-filled by the kernel.  Readers
  // must never clear it when attaching to a writer's existing mapping.
}

sysVShm::~sysVShm() {
  if (shm_ != MAP_FAILED) munmap(shm_, size_);
  if (fd_ >= 0) close(fd_);
  if (owner_ && fd_ >= 0 && name_[0]) shm_unlink(name_);
}

bool sysVShm::is_valid() const {
  return key_ != -1 && fd_ >= 0 && size_ > 0 && shm_ != MAP_FAILED;
}

static unsigned long read_limit(const char* path, AbstractLogger* log) {
  FILE* stream = fopen(path, "r");
  if (!stream) {
    if (log) log->warning("cannot read shared-memory limit: %", strerror(errno));
    return 0;
  }
  unsigned long limit = 0;
  if (fscanf(stream, "%lu", &limit) != 1) limit = 0;
  fclose(stream);
  return limit;
}

unsigned long sysVShm::get_shmmax(AbstractLogger* log) {
  return read_limit("/proc/sys/kernel/shmmax", log);
}

unsigned long sysVShm::get_shmmni(AbstractLogger* log) {
  return read_limit("/proc/sys/kernel/shmmni", log);
}

}  // namespace shmdata
