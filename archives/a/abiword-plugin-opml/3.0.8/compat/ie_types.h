/* compat/ie_types.h — OHOS minimal AbiWord ie_types.h shim */
#ifndef IE_TYPES_H
#define IE_TYPES_H

#include <string>
#include "ut_types.h"

typedef UT_sint32 IEFileType;
#define IEFT_Bogus   ((IEFileType)-1)
#define IEFT_Unknown ((IEFileType)0)

typedef UT_sint32 IEGraphicFileType;
#define IEGFT_Bogus  ((IEGraphicFileType)-1)
#define IEGFT_Unknown ((IEGraphicFileType)0)

enum IE_MimeMatch {
	IE_MIME_MATCH_BOGUS,
	IE_MIME_MATCH_CLASS,
	IE_MIME_MATCH_FULL
};

struct IE_MimeConfidence {
	IE_MimeMatch   match;
	std::string    mimetype;
	UT_Confidence_t confidence;
};

struct IE_SuffixConfidence {
	std::string      suffix;
	UT_Confidence_t  confidence;
};

#endif /* IE_TYPES_H */
