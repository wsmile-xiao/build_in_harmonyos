# hunspell-ca 3.0.91 adaptation notes

The competition task version `3.0.91` is the normalized form of Debian's
immutable `3.0.9+repack1` source. The dictionary content itself identifies as
upstream version `3.0.9`; this recipe does not relabel it as a nonexistent
upstream 3.0.91 release.

The source archive contains data only and has no test target. Packaging follows
the established Hunspell locale names:

- `catalan.*` becomes `ca.*` and `ca_ES.*`;
- `catalan-valencia.*` becomes `ca_ES-valencia.*`.

The added consumer validates UTF-8 declarations, declared dictionary counts,
aliases, representative Catalan and Valencian words, a negative lookup, and a
missing-directory fault path.
