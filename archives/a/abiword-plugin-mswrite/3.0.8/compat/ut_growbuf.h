/* compat/ut_growbuf.h — OHOS minimal AbiWord UT_GrowBuf shim */
#ifndef UT_GROWBUF_H
#define UT_GROWBUF_H

#include <vector>
#include "ut_types.h"

class UT_GrowBuf
{
public:
	UT_GrowBuf (UT_uint32 iChunk = 0);
	~UT_GrowBuf ();

	bool ins (UT_uint32 position, const UT_GrowBufElement * pValue, UT_uint32 length);
	void truncate (UT_uint32 position);
	UT_uint32 getLength (void) const;
	UT_GrowBufElement * getPointer (UT_uint32 position) const;

private:
	std::vector<UT_GrowBufElement> m_buf;
};

#endif /* UT_GROWBUF_H */
