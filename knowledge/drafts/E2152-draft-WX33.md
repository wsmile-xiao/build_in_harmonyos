# E2152 - Bind source archives to the current GitHub Release asset digest

## Symptom

An official release archive downloads and extracts correctly, but its SHA-256
differs from a checksum copied from Homebrew or another third-party catalog.
The mismatch alone does not identify which value describes the current
upstream asset.

## Trigger

- Phase: source acquisition and integrity validation
- Source: an uploaded GitHub Release asset
- Conflict: current local bytes disagree with a third-party checksum snapshot

## Root Cause

Package-manager indexes and catalogs are snapshots. They can retain a checksum
from an earlier asset generation or another source artifact. A release URL by
itself does not bind the current uploaded object's identity.

GitHub's Releases API exposes the uploaded asset's `id`, exact `name`, byte
`size`, `updated_at`, `browser_download_url`, and `digest`. These fields allow
the current upstream object to be distinguished from stale catalog metadata.

## Fix

1. Read the exact tag from GitHub's Releases API.
2. Select the exact uploaded asset name, not the generated tag archive.
3. Record the asset ID, size, update time, URL, and official digest.
4. Hash the completed local file and require an exact digest match.
5. Keep any third-party mismatch as evidence, but do not use it as the recipe
   checksum after the current official asset is bound.

Do not trust a checksum only because it appears in a package-manager formula,
and do not accept a transport mirror unless its final bytes match the official
asset digest.

## Validation

For wxWidgets v3.3.3, the third-party snapshot value
`0d55c1b9dadb31536c922b846194072aaf608641cd7e314a3b983996d1a30ccd`
conflicted with the downloaded release file. The current GitHub Releases API
identified `wxWidgets-3.3.3.tar.bz2` as asset `471278068`, size `32358881`,
updated at `2026-07-09T11:16:20Z`, with digest
`81b09d6dd9f1ed9301f8c55a968a488d0491f264dc2bab19a7e407ac67009482`.
The local archive matched both the official size and digest and declared
wxWidgets version 3.3.3 after extraction.

## Safety Boundaries

- Asset integrity does not prove build or runtime correctness.
- Re-read the API if any bound asset identity field changes.
- Do not substitute GitHub's generated tag archive when the release archive
  contains submodules or bundled third-party source.
- Do not weaken a recipe hash to accommodate a mismatching mirror.

## Related

- E285: distinguishes source archives from unrelated release binary digests.
