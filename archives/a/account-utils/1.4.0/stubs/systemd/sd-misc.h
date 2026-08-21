/* Minimal stub of systemd/sd-journal.h + sd-varlink-idl.h for OHOS. */
#ifndef SD_MISC_STUB_H
#define SD_MISC_STUB_H

#include <stdint.h>
#include <stddef.h>

typedef struct sd_journal sd_journal;

int sd_journal_open(sd_journal **ret, int flags);
int sd_journal_open_files(sd_journal **ret, const char **paths, int flags);
void sd_journal_close(sd_journal *j);
int sd_journal_next(sd_journal *j);
int sd_journal_previous(sd_journal *j);
int sd_journal_get_data(sd_journal *j, const char *field, const void **data,
                        size_t *length);
int sd_journal_get_realtime_usec(sd_journal *j, uint64_t *usec);
int sd_journal_seek_head(sd_journal *j);
int sd_journal_seek_tail(sd_journal *j);
int sd_journal_add_match(sd_journal *j, const void *data, size_t size);
int sd_journal_add_disjunction(sd_journal *j);
int sd_journal_add_conjunction(sd_journal *j);

#endif /* SD_MISC_STUB_H */
