# perl-list-moreutils

Perl module providing additional list utilities beyond List::Util.

## Description

List::MoreUtils provides some trivial but commonly needed functionality on lists which is not going to go into List::Util.

The module offers two implementations:
- **PP (Pure Perl)**: Full functionality, slightly slower
- **XS (C extension)**: Faster performance, requires system installation on OpenHarmony

## Available Version

| Version | Status | Date | Notes |
|---------|--------|------|-------|
| 0.430-r1 | built | 2026-06-15 | Pure Perl mode fully functional |

## Installation

### User Installation (Pure Perl Mode)

```bash
# Download and extract
tar xzf perl-list-moreutils-0.430-r1-ohos-aarch64.tar.gz
cp -r lib/site_perl/5.42.0/List ~/usr/local/lib/site_perl/5.42.0/

# Verify
perl -I ~/usr/local/lib/site_perl/5.42.0 -MList::MoreUtils -e 'print $List::MoreUtils::VERSION'
# Output: 0.430
```

### XS Module Installation (Requires Admin)

XS module (`perl-list-moreutils-xs`) requires installation to system directory due to SELinux HMDFS restrictions.

## Provided Functions

### Junction Functions
- `any`, `all`, `none`, `notall`, `one`

### Counting Functions
- `true`, `false`

### Indexing Functions
- `firstidx`, `lastidx`, `onlyidx`, `insert_after`, `insert_after_string`

### Retrieval Functions
- `firstval`, `lastval`, `onlyval`, `firstres`, `lastres`, `onlyres`

### Array Operations
- `uniq`, `minmax`, `part`, `mesh`, `zip6`

### Search Functions
- `bsearch`, `bsearchidx`, `binsert`, `bremove`

### Pair Operations
- `pairwise`, `natatime`, `each_array`, `each_arrayref`

### Sorting
- `sort_by`, `nsort_by`

### Miscellaneous
- `apply`, `after`, `after_incl`, `before`, `before_incl`

## Dependencies

- **Required**: perl 5.42.0
- **Optional**: perl-list-moreutils-xs (for XS acceleration)

## License

GPL-1.0-or-later OR Artistic-1.0

## OpenHarmony Notes

1. **Pure Perl mode works**: All functions are available via PP.pm implementation
2. **XS module limitation**: Due to SELinux HMDFS restrictions, XS module cannot be loaded from user directories. Requires admin installation to `/data/service/hnp/`
3. **Performance**: Pure Perl mode is slightly slower than XS, but sufficient for most use cases