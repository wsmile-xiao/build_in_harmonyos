/* compat/ut_vector.h — OHOS minimal AbiWord ut_vector.h shim
 *
 * UT_GenericVector maps to std::vector in the shim.  Only the member
 * surface used by the paint plugin / shim itself is provided.
 */
#ifndef UT_VECTOR_H
#define UT_VECTOR_H

#include <vector>
#include "ut_types.h"

template <class T>
class UT_GenericVector
{
public:
	UT_GenericVector () {}
	~UT_GenericVector () {}

	bool addItem (T item) { m_items.push_back (item); return true; }
	bool insertItemAt (T item, UT_uint32 pos) {
		if (pos > m_items.size ()) return false;
		m_items.insert (m_items.begin () + pos, item);
		return true;
	}
	bool deleteNthItem (UT_uint32 ndx) {
		if (ndx >= m_items.size ()) return false;
		m_items.erase (m_items.begin () + ndx);
		return true;
	}
	T getNthItem (UT_uint32 ndx) const {
		return (ndx < m_items.size ()) ? m_items[ndx] : T ();
	}
	UT_uint32 getItemCount () const { return (UT_uint32)m_items.size (); }
	bool setNthItem (T item, UT_uint32 ndx) {
		if (ndx >= m_items.size ()) return false;
		m_items[ndx] = item;
		return true;
	}
	bool findItem (T item, UT_uint32 * pNdx) const {
		for (UT_uint32 i = 0; i < m_items.size (); i++) {
			if (m_items[i] == item) {
				if (pNdx) *pNdx = i;
				return true;
			}
		}
		return false;
	}

private:
	std::vector<T> m_items;
};

#endif /* UT_VECTOR_H */
