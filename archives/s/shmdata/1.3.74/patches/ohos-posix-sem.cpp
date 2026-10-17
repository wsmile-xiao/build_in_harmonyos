/* HarmonyOS PC process-shared mutex/condition backend for SysV semaphores.
 * SPDX-License-Identifier: LGPL-2.1-or-later
 */
#include "./sysv-sem.hpp"
#include <cerrno>
#include <cstdio>
#include <cstring>
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>

namespace shmdata {

static constexpr unsigned kMagic = 0x53484d53;

static void semaphore_name(char* out, size_t length, key_t key) {
  snprintf(out, length, "/shmdata-lock-%08x", static_cast<unsigned>(key));
}

bool force_semaphore_cleaning(key_t key, AbstractLogger* log) {
  char name[64];
  semaphore_name(name, sizeof(name), key);
  if (shm_unlink(name) == 0) return true;
  if (errno != ENOENT) log->warning("semaphore shm_unlink: %", strerror(errno));
  return false;
}

sysVSem::sysVSem(key_t key, AbstractLogger* log, bool owner,
                 mode_t unix_permission)
    : key_(key), owner_(owner), log_(log) {
  if (key_ == -1) {
    log_->warning("ftok: %", strerror(errno));
    return;
  }
  semaphore_name(name_, sizeof(name_), key_);
  fd_ = shm_open(name_, owner_ ? O_RDWR | O_CREAT | O_EXCL : O_RDWR,
                 unix_permission);
  if (fd_ < 0) {
    log_->warning("semaphore shm_open: %", strerror(errno));
    return;
  }
  if (owner_ && ftruncate(fd_, sizeof(State)) != 0) {
    log_->warning("semaphore ftruncate: %", strerror(errno));
    return;
  }
  state_ = static_cast<State*>(mmap(nullptr, sizeof(State), PROT_READ | PROT_WRITE,
                                    MAP_SHARED, fd_, 0));
  if (state_ == MAP_FAILED) {
    state_ = nullptr;
    log_->warning("semaphore mmap: %", strerror(errno));
    return;
  }
  if (owner_) {
    pthread_mutexattr_t mutex_attr;
    pthread_condattr_t cond_attr;
    if (pthread_mutexattr_init(&mutex_attr) != 0 ||
        pthread_condattr_init(&cond_attr) != 0) return;
    int result = pthread_mutexattr_setpshared(&mutex_attr, PTHREAD_PROCESS_SHARED);
    if (result == 0)
      result = pthread_condattr_setpshared(&cond_attr, PTHREAD_PROCESS_SHARED);
    if (result == 0) result = pthread_mutex_init(&state_->mutex, &mutex_attr);
    if (result == 0) result = pthread_cond_init(&state_->changed, &cond_attr);
    pthread_mutexattr_destroy(&mutex_attr);
    pthread_condattr_destroy(&cond_attr);
    if (result != 0) {
      log_->warning("process-shared synchronization: %", strerror(result));
      return;
    }
    state_->pending_readers = 0;
    state_->writer_active = false;
    state_->magic = kMagic;
  }
  if (state_->magic != kMagic)
    log_->warning("semaphore state not initialized");
}

sysVSem::~sysVSem() {
  // Other processes may still map the state; unlink only removes its name.
  if (state_) munmap(state_, sizeof(State));
  if (fd_ >= 0) close(fd_);
  if (owner_ && fd_ >= 0 && name_[0]) shm_unlink(name_);
}

bool sysVSem::is_valid() const {
  return key_ != -1 && fd_ >= 0 && state_ && state_->magic == kMagic;
}

void sysVSem::cancel_commited_reader() {
  if (!is_valid()) return;
  pthread_mutex_lock(&state_->mutex);
  if (state_->pending_readers) --state_->pending_readers;
  pthread_cond_broadcast(&state_->changed);
  pthread_mutex_unlock(&state_->mutex);
}

ReadLock::ReadLock(sysVSem* sem) : sem_(sem) {
  if (!sem_ || !sem_->is_valid()) return;
  auto* state = sem_->state_;
  if (pthread_mutex_lock(&state->mutex) != 0) return;
  int result = 0;
  while (state->writer_active && result == 0)
    result = pthread_cond_wait(&state->changed, &state->mutex);
  valid_ = result == 0;
  pthread_mutex_unlock(&state->mutex);
}

ReadLock::~ReadLock() {
  if (!valid_) return;
  auto* state = sem_->state_;
  pthread_mutex_lock(&state->mutex);
  if (state->pending_readers) --state->pending_readers;
  pthread_cond_broadcast(&state->changed);
  pthread_mutex_unlock(&state->mutex);
}

WriteLock::WriteLock(sysVSem* sem) : sem_(sem) {
  if (!sem_ || !sem_->is_valid()) return;
  auto* state = sem_->state_;
  if (pthread_mutex_lock(&state->mutex) != 0) return;
  int result = 0;
  while (state->pending_readers && result == 0)
    result = pthread_cond_wait(&state->changed, &state->mutex);
  if (result == 0) {
    state->writer_active = true;
    ++state->pending_readers;
    valid_ = true;
  }
  pthread_mutex_unlock(&state->mutex);
}

bool WriteLock::commit_readers(short num_readers) {
  if (!valid_ || num_readers < 0) return false;
  auto* state = sem_->state_;
  if (pthread_mutex_lock(&state->mutex) != 0) return false;
  state->pending_readers += static_cast<unsigned>(num_readers);
  pthread_mutex_unlock(&state->mutex);
  return true;
}

WriteLock::~WriteLock() {
  if (!valid_) return;
  auto* state = sem_->state_;
  pthread_mutex_lock(&state->mutex);
  state->writer_active = false;
  if (state->pending_readers) --state->pending_readers;
  pthread_cond_broadcast(&state->changed);
  pthread_mutex_unlock(&state->mutex);
}

}  // namespace shmdata
