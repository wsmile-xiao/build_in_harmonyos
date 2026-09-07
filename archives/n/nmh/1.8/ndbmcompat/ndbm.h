/*
 * ndbm.h - ndbm compatibility layer backed by gdbm
 *
 * HarmonyOS (bionic) does not ship an ndbm implementation.  nmh's
 * slocal(1) uses the classic dbm_open/dbm_fetch/... API to suppress
 * duplicate Message-IDs, so this header re-implements the small ndbm
 * surface on top of the real gdbm library pulled in by the recipe.
 * Implementations are static inline so no extra library is required;
 * nmh links -lgdbm (NDBM_LIBS) for the gdbm_* symbols.
 *
 * Semantics notes:
 *  - slocal performs its own fcntl locking around the database file
 *    (see "it is difficult to portably lock a ndbm file" in slocal.c),
 *    therefore GDBM_NOLOCK is used to avoid double locking.
 *  - The O_ACCMODE/O_CREAT flags of dbm_open are mapped to the
 *    GDBM_READER/GDBM_WRITER/GDBM_WRCREAT access modes.
 */

#ifndef NMH_OHOS_NDBM_H
#define NMH_OHOS_NDBM_H

#include <fcntl.h>
#include <gdbm.h>

typedef struct gdbm_file_info DBM;

#ifndef DBM_INSERT
#define DBM_INSERT 0
#endif
#ifndef DBM_REPLACE
#define DBM_REPLACE 1
#endif

static inline DBM *
dbm_open (const char *file, int flags, int mode)
{
  int access_mode;
  int gdbm_flags;

  switch (flags & O_ACCMODE)
    {
    case O_RDWR:
      access_mode = (flags & O_CREAT) ? GDBM_WRCREAT : GDBM_WRITER;
      break;
    case O_WRONLY:
      access_mode = (flags & O_CREAT) ? GDBM_WRCREAT : GDBM_WRITER;
      break;
    default:
      access_mode = GDBM_READER;
      break;
    }
  gdbm_flags = access_mode | GDBM_NOLOCK;
  return gdbm_open (file, 0, gdbm_flags, mode, (void *) 0);
}

static inline void
dbm_close (DBM *db)
{
  gdbm_close (db);
}

static inline datum
dbm_fetch (DBM *db, datum key)
{
  return gdbm_fetch (db, key);
}

static inline int
dbm_store (DBM *db, datum key, datum content, int flags)
{
  int store_flags;

  store_flags = (flags == DBM_REPLACE) ? GDBM_REPLACE : GDBM_INSERT;
  return gdbm_store (db, key, content, store_flags);
}

static inline int
dbm_delete (DBM *db, datum key)
{
  return gdbm_delete (db, key);
}

static inline datum
dbm_firstkey (DBM *db)
{
  return gdbm_firstkey (db);
}

static inline datum
dbm_nextkey (DBM *db, datum key)
{
  return gdbm_nextkey (db, key);
}

static inline int
dbm_error (DBM *db)
{
  return gdbm_errno;
}

static inline void
dbm_clearerr (DBM *db)
{
  gdbm_errno = 0;
}

#endif /* NMH_OHOS_NDBM_H */
