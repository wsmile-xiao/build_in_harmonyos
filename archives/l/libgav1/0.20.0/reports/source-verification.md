# libgav1 0.20.0 source verification

This report records why the source declaration changed, which artifact is now
used, and how its identity was verified without access to the upstream Git host.

## 1. Observed failure

Every PR CI attempt on this branch failed inside `source()` with the same cause:

| CI run | Date | Worker | Failure |
|---|---|---|---|
| #50298 | 2026-09-18 | CI-032 | `git clone https://chromium.googlesource.com/codecs/libgav1.git` → `Failed to connect to chromium.googlesource.com port 443` |
| #52175 | 2026-09-20 | CI-032 | worker resource failure (`fork failed: out of memory`, infrastructure) |
| #52414 | 2026-09-20 | CI-026 | same `git clone` connect failure |
| #53532 | 2026-09-20 | CI-029 | same `git clone` connect failure |
| #59757 | 2026-09-24 | CI-006 | same `git clone` connect failure |

Independent reachability probe from the build network:

```text
curl https://chromium.googlesource.com/codecs/libgav1.git/info/refs?service=git-upload-pack
  → curl: (28) Connection timed out after 20002 milliseconds
curl https://deb.debian.org/debian/pool/main/libg/libgav1/                                  → HTTP 200
curl https://mirrors.tuna.tsinghua.edu.cn/debian/pool/main/libg/libgav1/                     → HTTP 200
curl https://mirrors.aliyun.com/debian/pool/main/libg/libgav1/                               → HTTP 200
```

Upstream publishes no byte-stable archive (Gitiles `.tar.gz` output is not
reproducible), so a Gitiles SHA-256 cannot be pinned as an alternative. The
previous `sha256: null` therefore could not be resolved while keeping the
official Git host as the fetched source.

## 2. Adopted source

Debian's upstream orig tarball for libgav1 0.20.0:

| Item | Value |
|---|---|
| URL | `https://deb.debian.org/debian/pool/main/libg/libgav1/libgav1_0.20.0.orig.tar.xz` |
| Size | 758912 bytes |
| SHA-256 | `953f98a5147f556f358ef986601fda7804cfaaa634302aa9b842fea889aa7e6c` |
| Checksum authority | `libgav1_0.20.0-2.dsc`, PGP-signed by the Debian Multimedia Maintainers |
| Upstream metadata | Debian `Homepage:` and `debian/watch` both point at `https://chromium.googlesource.com/codecs/libgav1` |

`conandata.yml` lists two additional mirrors of the same Debian archive
(`mirrors.tuna.tsinghua.edu.cn`, `mirrors.aliyun.com`); all three hosts were
downloaded and returned the identical 758912-byte file with the identical
SHA-256. `mirrors.ustc.edu.cn` was probed and rejected: it serves a 19255-byte
error page for this path, not the archive.

## 3. Verification chain

1. **Checksum**: the downloaded tarball SHA-256 equals the value published in
   the signed `libgav1_0.20.0-2.dsc`, and equals the value served by both CN
   mirrors.
2. **Upstream revision**: `debian/watch` declares upstream
   `https://chromium.googlesource.com/codecs/libgav1` with tag pattern
   `v([\d\.]+)`, so the orig tarball is generated from upstream tag `v0.20.0`.
   All Debian changes live in `debian/patches/` (`Unbundle-abseil`,
   `Use-system-googletest`, `Use-C-17`, `Temporarily-disable-CPU-test`) and are
   not part of the orig tarball — the tarball is the unmodified upstream tree.
3. **Pinned commit**: upstream `v0.20.0` is an annotated, PGP-signed tag whose
   target is commit `c05bf9be660cf170d7c26bd06bb42b3322180e58` — the exact
   revision this recipe previously pinned.
4. **Tree equality**: a file-by-file comparison of the Debian orig tarball
   against the upstream `v0.20.0` tree gives 387 files on both sides, 0 path
   differences and 0 content differences.

The comparison reference in step 4 was an independent public mirror of upstream
tag `v0.20.0` (`moneytoo/libgav1`, self-described as a mirror of
`chromium.googlesource.com/codecs/libgav1`). It was used **only** as a
comparison reference; it is not referenced by the recipe and is never fetched
during a build. The build source stays the Debian archive, whose checksum is
published in a PGP-signed Debian `.dsc`.

## 4. Reproduction

```sh
# checksum published by Debian (inside the PGP-signed .dsc)
curl -sS https://deb.debian.org/debian/pool/main/libg/libgav1/libgav1_0.20.0-2.dsc \
  | grep -A3 Checksums-Sha256

# fetched artifact must match that checksum
curl -sSL -o libgav1_0.20.0.orig.tar.xz \
  https://deb.debian.org/debian/pool/main/libg/libgav1/libgav1_0.20.0.orig.tar.xz
sha256sum libgav1_0.20.0.orig.tar.xz
# 953f98a5147f556f358ef986601fda7804cfaaa634302aa9b842fea889aa7e6c
```

`conan create archives/l/libgav1/0.20.0` on a free OHOS runner exercises the
same path: Conan downloads the tarball, verifies `sha256`, strips the
`libgav1-0.20.0/` root and builds it.
