// marisa_tool — out-of-process marisa trie builder for libkkc-data 0.2.7.
//
// tools/sortlm.py needs exactly two marisa operations:
//   1. build a trie from an ordered key list and save it with Trie::save();
//   2. obtain the trie key id of every vocabulary token.
//
// Upstream obtains them through the `marisa` Python module. That cannot work
// on the OHOS build worker: the sandbox only allows a process to dlopen a
// shared object carrying the `hnp_file` security label, while everything a
// build writes lives in a user-owned path (hmdfs label), so importing a
// freshly compiled extension fails with
//     ImportError: Error loading shared library ... Permission denied
// (hmmac security labels; see knowledge entry E212).
//
// This helper performs the very same marisa 0.3.1 calls in a separate
// process, compiled in one command together with the marisa sources, so the
// model generation never depends on loading a shared object into the
// interpreter and the helper and the trie always share one ABI.
//
// usage:
//   marisa_tool build <keys-file> <trie-file> [--no-ids]
//       <keys-file>  UTF-8 keys, one per line, in trie insertion order
//       <trie-file>  written by marisa::Trie::save(), byte-identical to the
//                    upstream `trie.save()` call
//       stdout       "<id>\t<key>" for every key, unless --no-ids
//   marisa_tool selftest
//       builds a tiny trie and checks the key ids; used as a cheap
//       "the helper runs on this machine" probe before model generation

#include <cstdio>
#include <cstring>
#include <exception>
#include <fstream>
#include <iostream>
#include <string>

#include "marisa/trie.h"

namespace {

int usage(const char *argv0) {
  std::fprintf(stderr,
               "usage: %s build <keys-file> <trie-file> [--no-ids]\n"
               "       %s selftest\n",
               argv0, argv0);
  return 2;
}

// Build a trie from `keys` (in the given order) and save it to `out_path`.
// Prints "<id>\t<key>" for every key when `print_ids` is set.
int build(const char *keys_path, const char *out_path, bool print_ids) {
  std::ifstream in(keys_path, std::ios::binary);
  if (!in) {
    std::fprintf(stderr, "marisa_tool: cannot open %s\n", keys_path);
    return 1;
  }

  marisa::Keyset keyset;
  std::string line;
  while (std::getline(in, line)) {
    if (!line.empty() && line.back() == '\r') {
      line.pop_back();
    }
    keyset.push_back(line.data(), line.size(), 1.0f);
  }
  in.close();

  // Default config flags, exactly like upstream's `Trie().build(keyset)`.
  marisa::Trie trie;
  trie.build(keyset);
  trie.save(out_path);

  if (print_ids) {
    for (std::size_t i = 0; i < keyset.num_keys(); ++i) {
      const marisa::Key &key = keyset[i];
      std::printf("%zu\t", key.id());
      if (key.length() != 0) {
        std::fwrite(key.ptr(), 1, key.length(), stdout);
      }
      std::fputc('\n', stdout);
    }
  }
  if (std::fflush(stdout) != 0) {
    std::fprintf(stderr, "marisa_tool: failed to flush key ids\n");
    return 1;
  }
  std::fprintf(stderr, "marisa_tool: %zu keys -> %s\n", keyset.num_keys(),
               out_path);
  return 0;
}

int selftest() {
  const char *keys[] = {"\xe3\x81\x82/\xe4\xba\x9c", "\xe3\x81\x84", "<s>"};
  marisa::Keyset keyset;
  for (const char *key : keys) {
    keyset.push_back(key, std::strlen(key), 1.0f);
  }
  marisa::Trie trie;
  trie.build(keyset);
  if (trie.num_keys() != 3) {
    std::fprintf(stderr, "marisa_tool: selftest num_keys=%zu, expected 3\n",
                 trie.num_keys());
    return 1;
  }
  for (std::size_t i = 0; i < keyset.num_keys(); ++i) {
    marisa::Agent agent;
    agent.set_query(keyset[i].ptr(), keyset[i].length());
    if (!trie.lookup(agent) || agent.key().id() != keyset[i].id()) {
      std::fprintf(stderr, "marisa_tool: selftest lookup mismatch at %zu\n", i);
      return 1;
    }
  }
  std::printf("marisa_tool selftest OK (3 keys)\n");
  return 0;
}

}  // namespace

int main(int argc, char **argv) {
  try {
    if (argc >= 2 && std::strcmp(argv[1], "selftest") == 0) {
      return selftest();
    }
    if (argc >= 4 && std::strcmp(argv[1], "build") == 0) {
      bool print_ids = true;
      for (int i = 4; i < argc; ++i) {
        if (std::strcmp(argv[i], "--no-ids") == 0) {
          print_ids = false;
        } else {
          return usage(argv[0]);
        }
      }
      return build(argv[2], argv[3], print_ids);
    }
    return usage(argv[0]);
  } catch (const std::exception &e) {
    std::fprintf(stderr, "marisa_tool: %s\n", e.what());
    return 1;
  }
}
