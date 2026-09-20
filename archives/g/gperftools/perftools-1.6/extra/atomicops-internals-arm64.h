/* Copyright (c) 2006, Google Inc.
 * All rights reserved.
 * 
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are
 * met:
 * 
 *     * Redistributions of source code must retain the above copyright
 * notice, this list of conditions and the following disclaimer.
 *     * Redistributions in binary form must reproduce the above
 * copyright notice, this list of conditions and the following disclaimer
 * in the documentation and/or other materials provided with the
 * distribution.
 *     * Neither the name of Google Inc. nor the names of its
 * contributors may be used to endorse or promote products derived from
 * this software without specific prior written permission.
 * 
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 * "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 * LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
 * A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
 * OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
 * SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
 * LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
 * DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
 * THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 * OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 *
 * ---
 * Implementation of atomic operations for AArch64 (ARMv8 64-bit),
 * using GCC/Clang builtin intrinsics (__sync_* / __atomic_*).
 * This file should not be included directly.  Clients should instead
 * include "base/atomicops.h".
 */

#ifndef BASE_ATOMICOPS_INTERNALS_ARM64_H_
#define BASE_ATOMICOPS_INTERNALS_ARM64_H_

typedef int32_t Atomic32;
#define BASE_HAS_ATOMIC64 1  // Use only in tests and base/atomic*

#define ATOMICOPS_COMPILER_BARRIER() __asm__ __volatile__("" : : : "memory")

namespace base {
namespace subtle {

typedef int64_t Atomic64;

// 32-bit low-level operations.

inline Atomic32 NoBarrier_CompareAndSwap(volatile Atomic32* ptr,
                                         Atomic32 old_value,
                                         Atomic32 new_value) {
  return __sync_val_compare_and_swap(ptr, old_value, new_value);
}

inline Atomic32 NoBarrier_AtomicExchange(volatile Atomic32* ptr,
                                         Atomic32 new_value) {
  return __sync_lock_test_and_set(ptr, new_value);
}

inline Atomic32 NoBarrier_AtomicIncrement(volatile Atomic32* ptr,
                                          Atomic32 increment) {
  return __sync_add_and_fetch(ptr, increment);
}

inline Atomic32 Barrier_AtomicIncrement(volatile Atomic32* ptr,
                                        Atomic32 increment) {
  return __sync_add_and_fetch(ptr, increment);
}

inline Atomic32 Acquire_CompareAndSwap(volatile Atomic32* ptr,
                                       Atomic32 old_value,
                                       Atomic32 new_value) {
  return __sync_val_compare_and_swap(ptr, old_value, new_value);
}

inline Atomic32 Release_CompareAndSwap(volatile Atomic32* ptr,
                                       Atomic32 old_value,
                                       Atomic32 new_value) {
  return __sync_val_compare_and_swap(ptr, old_value, new_value);
}

inline void NoBarrier_Store(volatile Atomic32* ptr, Atomic32 value) {
  __atomic_store_n(ptr, value, __ATOMIC_RELAXED);
}

inline void MemoryBarrier() {
  __sync_synchronize();
}

inline void Acquire_Store(volatile Atomic32* ptr, Atomic32 value) {
  __atomic_store_n(ptr, value, __ATOMIC_RELAXED);
  MemoryBarrier();
}

inline void Release_Store(volatile Atomic32* ptr, Atomic32 value) {
  __atomic_store_n(ptr, value, __ATOMIC_RELEASE);
}

inline Atomic32 NoBarrier_Load(volatile const Atomic32* ptr) {
  return __atomic_load_n(ptr, __ATOMIC_RELAXED);
}

inline Atomic32 Acquire_Load(volatile const Atomic32* ptr) {
  return __atomic_load_n(ptr, __ATOMIC_ACQUIRE);
}

inline Atomic32 Release_Load(volatile const Atomic32* ptr) {
  MemoryBarrier();
  return __atomic_load_n(ptr, __ATOMIC_RELAXED);
}

// 64-bit low-level operations.

inline Atomic64 NoBarrier_CompareAndSwap(volatile Atomic64* ptr,
                                         Atomic64 old_value,
                                         Atomic64 new_value) {
  return __sync_val_compare_and_swap(ptr, old_value, new_value);
}

inline Atomic64 NoBarrier_AtomicExchange(volatile Atomic64* ptr,
                                         Atomic64 new_value) {
  return __sync_lock_test_and_set(ptr, new_value);
}

inline Atomic64 NoBarrier_AtomicIncrement(volatile Atomic64* ptr,
                                          Atomic64 increment) {
  return __sync_add_and_fetch(ptr, increment);
}

inline Atomic64 Barrier_AtomicIncrement(volatile Atomic64* ptr,
                                        Atomic64 increment) {
  return __sync_add_and_fetch(ptr, increment);
}

inline Atomic64 Acquire_CompareAndSwap(volatile Atomic64* ptr,
                                       Atomic64 old_value,
                                       Atomic64 new_value) {
  return __sync_val_compare_and_swap(ptr, old_value, new_value);
}

inline Atomic64 Release_CompareAndSwap(volatile Atomic64* ptr,
                                       Atomic64 old_value,
                                       Atomic64 new_value) {
  return __sync_val_compare_and_swap(ptr, old_value, new_value);
}

inline void NoBarrier_Store(volatile Atomic64* ptr, Atomic64 value) {
  __atomic_store_n(ptr, value, __ATOMIC_RELAXED);
}

inline void Acquire_Store(volatile Atomic64* ptr, Atomic64 value) {
  __atomic_store_n(ptr, value, __ATOMIC_RELAXED);
  MemoryBarrier();
}

inline void Release_Store(volatile Atomic64* ptr, Atomic64 value) {
  __atomic_store_n(ptr, value, __ATOMIC_RELEASE);
}

inline Atomic64 NoBarrier_Load(volatile const Atomic64* ptr) {
  return __atomic_load_n(ptr, __ATOMIC_RELAXED);
}

inline Atomic64 Acquire_Load(volatile const Atomic64* ptr) {
  return __atomic_load_n(ptr, __ATOMIC_ACQUIRE);
}

inline Atomic64 Release_Load(volatile const Atomic64* ptr) {
  MemoryBarrier();
  return __atomic_load_n(ptr, __ATOMIC_RELAXED);
}

}  // namespace base::subtle
}  // namespace base

#endif  // BASE_ATOMICOPS_INTERNALS_ARM64_H_