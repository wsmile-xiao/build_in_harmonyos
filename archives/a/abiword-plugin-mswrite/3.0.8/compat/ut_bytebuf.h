/* compat/ut_bytebuf.h — OHOS minimal UT_ByteBuf shim
 * Growable byte buffer; subset used by the mswrite plugin
 * (append / getLength / getPointer / truncate / ins).
 */
#ifndef COMPAT_UT_BYTEBUF_H
#define COMPAT_UT_BYTEBUF_H

#include <stdlib.h>
#include <string.h>
#include "ut_types.h"

class UT_ByteBuf
{
public:
	UT_ByteBuf (UT_uint32 iChunk = 0)
		: m_buf (0), m_iSize (0), m_iSpace (0), m_iChunk (iChunk ? iChunk : 1024)
	{
	}
	~UT_ByteBuf ()
	{
		free (m_buf);
	}

	bool append (const UT_Byte * pValue, UT_uint32 length)
	{
		if (!length)
			return true;
		if (!_byteBuf (m_iSize + length))
			return false;
		memcpy (m_buf + m_iSize, pValue, length);
		m_iSize += length;
		return true;
	}

	bool ins (UT_uint32 position, const UT_Byte * pValue, UT_uint32 length)
	{
		if (position > m_iSize)
			return false;
		if (!_byteBuf (m_iSize + length))
			return false;
		memmove (m_buf + position + length, m_buf + position, m_iSize - position);
		memcpy (m_buf + position, pValue, length);
		m_iSize += length;
		return true;
	}

	bool del (UT_uint32 position, UT_uint32 amount)
	{
		if (position + amount > m_iSize)
			return false;
		memmove (m_buf + position, m_buf + position + amount, m_iSize - position - amount);
		m_iSize -= amount;
		return true;
	}

	void truncate (UT_uint32 position)
	{
		if (position < m_iSize)
			m_iSize = position;
	}

	UT_uint32 getLength (void) const { return m_iSize; }
	/* 上游 mswrite 用 *mData.getPointer(pos) 逐个取字节：必须返回
	 * 对应位置的指针（clarisworks 仅比较指针地址，位置无影响）。
	 * 越界防御：返回缓冲区起始（m_buf 恒有效，除非缓冲为空），
	 * 避免 m_buf + m_iSize 在空缓冲区上产生悬垂/NULL 指针。 */
	const UT_Byte * getPointer (UT_uint32 position) const
	{
		if (position >= m_iSize || !m_buf)
			return m_buf;   /* 越界/空缓冲：安全回退到缓冲区起始 */
		return m_buf + position;
	}

private:
	bool _byteBuf (UT_uint32 spaceNeeded)
	{
		if (spaceNeeded <= m_iSpace)
			return true;
		/* 容量倍增防回绕：>2GB 时 uint32 倍增会回绕为 0 导致死循环
		 * （审查 P3）。用 64 位中间量计算并拒绝超 uint32 上限。 */
		UT_uint64 newSpace = m_iSpace ? m_iSpace : m_iChunk;
		while (newSpace < spaceNeeded)
		{
			newSpace *= 2;
			if (newSpace > 0xFFFFFFFFULL)
				return false;   /* 超出 UT_uint32 容量，拒绝分配 */
		}
		UT_Byte * newBuf = static_cast<UT_Byte *> (realloc (m_buf, (size_t)newSpace));
		if (!newBuf)
			return false;
		m_buf = newBuf;
		m_iSpace = (UT_uint32)newSpace;
		return true;
	}

	UT_Byte * m_buf;
	UT_uint32 m_iSize;
	UT_uint32 m_iSpace;
	UT_uint32 m_iChunk;
};

#endif /* COMPAT_UT_BYTEBUF_H */
