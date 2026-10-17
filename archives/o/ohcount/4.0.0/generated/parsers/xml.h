
#line 1 "xml.rl"
// xml.rl written by Mitchell Foral. mitchell<att>caladbolg<dott>net.

/************************* Required for every parser *************************/
#ifndef OHCOUNT_XML_PARSER_H
#define OHCOUNT_XML_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *XML_LANG = LANG_XML;

// the languages entities
const char *xml_entities[] = {
  "space", "comment", "doctype",
  "tag", "entity", "any"
};

// constants associated with the entities
enum {
  XML_SPACE = 0, XML_COMMENT, XML_DOCTYPE,
  XML_TAG, XML_ENTITY, XML_ANY
};

/*****************************************************************************/


#line 30 "xml.h"
static const char _xml_actions[] = {
	0, 1, 0, 1, 1, 1, 5, 1, 
	6, 1, 8, 1, 9, 1, 10, 1, 
	11, 1, 13, 1, 14, 1, 17, 1, 
	18, 1, 19, 1, 20, 1, 22, 1, 
	23, 1, 24, 1, 25, 2, 0, 14, 
	2, 3, 2, 2, 4, 2, 2, 6, 
	15, 2, 7, 16, 2, 9, 21, 2, 
	12, 7, 2, 12, 9, 3, 3, 2, 
	1, 3, 4, 2, 0
};

static const char _xml_cond_offsets[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 1, 2, 3, 4, 4, 
	4, 4, 4, 4, 4, 4, 5, 6, 
	7, 8, 8, 8, 8, 8, 8, 9, 
	9, 9, 9, 9
};

static const char _xml_cond_lengths[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 1, 1, 1, 1, 0, 0, 
	0, 0, 0, 0, 0, 1, 1, 1, 
	1, 0, 0, 0, 0, 0, 1, 0, 
	0, 0, 0, 0
};

static const short _xml_cond_keys[] = {
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 0
};

static const char _xml_cond_spaces[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0
};

static const char _xml_key_offsets[] = {
	0, 0, 1, 2, 3, 4, 6, 10, 
	14, 16, 17, 28, 39, 50, 62, 63, 
	64, 65, 66, 67, 68, 69, 80, 91, 
	102, 114, 115, 116, 120, 123, 124, 137, 
	139, 143, 147, 148
};

static const short _xml_trans_keys[] = {
	45, 45, 45, 45, 45, 62, 10, 34, 
	12, 13, 10, 39, 12, 13, 45, 91, 
	45, 9, 10, 12, 32, 45, 269, 525, 
	0, 11, 14, 255, 9, 10, 12, 32, 
	45, 269, 525, 0, 11, 14, 255, 9, 
	10, 12, 32, 45, 269, 525, 0, 11, 
	14, 255, 9, 10, 12, 32, 45, 62, 
	269, 525, 0, 11, 14, 255, 10, 67, 
	68, 65, 84, 65, 91, 9, 10, 12, 
	32, 93, 269, 525, 0, 11, 14, 255, 
	9, 10, 12, 32, 93, 269, 525, 0, 
	11, 14, 255, 9, 10, 12, 32, 93, 
	269, 525, 0, 11, 14, 255, 9, 10, 
	12, 32, 62, 93, 269, 525, 0, 11, 
	14, 255, 10, 10, 32, 60, 9, 13, 
	32, 9, 13, 33, 9, 10, 12, 32, 
	34, 39, 60, 269, 525, 0, 8, 14, 
	255, 9, 32, 10, 34, 12, 13, 10, 
	39, 12, 13, 33, 10, 0
};

static const char _xml_single_lengths[] = {
	0, 1, 1, 1, 1, 2, 2, 2, 
	2, 1, 7, 7, 7, 8, 1, 1, 
	1, 1, 1, 1, 1, 7, 7, 7, 
	8, 1, 1, 2, 1, 1, 9, 2, 
	2, 2, 1, 1
};

static const char _xml_range_lengths[] = {
	0, 0, 0, 0, 0, 0, 1, 1, 
	0, 0, 2, 2, 2, 2, 0, 0, 
	0, 0, 0, 0, 0, 2, 2, 2, 
	2, 0, 0, 1, 1, 0, 2, 0, 
	1, 1, 0, 0
};

static const char _xml_index_offsets[] = {
	0, 0, 2, 4, 6, 8, 11, 15, 
	19, 22, 24, 34, 44, 54, 65, 67, 
	69, 71, 73, 75, 77, 79, 89, 99, 
	109, 120, 122, 124, 128, 131, 133, 145, 
	148, 152, 156, 158
};

static const char _xml_indicies[] = {
	1, 0, 2, 0, 3, 2, 4, 2, 
	4, 5, 2, 6, 8, 6, 7, 6, 
	8, 6, 9, 10, 11, 6, 12, 6, 
	13, 14, 14, 13, 15, 16, 14, 12, 
	12, 6, 18, 19, 19, 18, 20, 21, 
	19, 17, 17, 6, 13, 14, 14, 13, 
	22, 16, 14, 12, 12, 6, 13, 14, 
	14, 13, 22, 23, 16, 14, 12, 12, 
	6, 14, 6, 24, 6, 25, 6, 26, 
	6, 27, 6, 28, 6, 29, 6, 30, 
	31, 31, 30, 32, 33, 31, 29, 29, 
	6, 35, 36, 36, 35, 37, 38, 36, 
	34, 34, 6, 30, 31, 31, 30, 39, 
	33, 31, 29, 29, 6, 30, 31, 31, 
	30, 40, 39, 33, 31, 29, 29, 6, 
	31, 6, 41, 42, 44, 45, 44, 43, 
	44, 44, 46, 48, 47, 50, 41, 41, 
	50, 51, 52, 53, 54, 55, 49, 49, 
	42, 50, 50, 56, 57, 8, 57, 7, 
	57, 8, 57, 9, 58, 57, 41, 59, 
	0
};

static const char _xml_trans_targs[] = {
	27, 2, 3, 4, 5, 27, 30, 6, 
	30, 7, 9, 15, 10, 10, 11, 12, 
	14, 10, 10, 11, 12, 14, 13, 30, 
	16, 17, 18, 19, 20, 21, 21, 22, 
	23, 25, 21, 21, 22, 23, 25, 24, 
	30, 30, 0, 27, 28, 29, 27, 27, 
	1, 30, 31, 32, 33, 34, 26, 35, 
	30, 30, 8, 30
};

static const char _xml_trans_actions[] = {
	35, 11, 11, 11, 11, 52, 27, 0, 
	37, 0, 0, 0, 3, 0, 0, 3, 
	0, 61, 40, 40, 61, 40, 3, 17, 
	0, 0, 0, 0, 0, 1, 0, 0, 
	1, 0, 65, 43, 43, 65, 43, 1, 
	19, 46, 0, 29, 9, 58, 31, 33, 
	11, 49, 5, 55, 55, 55, 7, 7, 
	21, 25, 0, 23
};

static const char _xml_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 13, 0, 0, 13, 0, 
	0, 0, 0, 0
};

static const char _xml_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 15, 0, 0, 15, 0, 
	0, 0, 0, 0
};

static const char _xml_eof_trans[] = {
	0, 1, 1, 1, 1, 1, 7, 7, 
	7, 7, 7, 7, 7, 7, 7, 7, 
	7, 7, 7, 7, 7, 7, 7, 7, 
	7, 7, 0, 0, 47, 48, 0, 57, 
	58, 58, 58, 60
};

static const int xml_start = 27;
static const int xml_first_final = 27;
static const int xml_error = 0;

static const int xml_en_xml_line = 30;
static const int xml_en_xml_entity = 27;


#line 95 "xml.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with XML markup.
 *
 * @param *buffer The string to parse.
 * @param length The length of the string to parse.
 * @param count Integer flag specifying whether or not to count lines. If yes,
 *   uses the Ragel machine optimized for counting. Otherwise uses the Ragel
 *   machine optimized for returning entity positions.
 * @param *callback Callback function. If count is set, callback is called for
 *   every line of code, comment, or blank with 'lcode', 'lcomment', and
 *   'lblank' respectively. Otherwise callback is called for each entity found.
 */
void parse_xml(char *buffer, int length, int count,
               void (*callback) (const char *lang, const char *entity, int s,
                                 int e, void *udata),
               void *userdata
  ) {
  init

  
#line 226 "xml.h"
	{
	cs = xml_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 118 "xml.rl"
  cs = (count) ? xml_en_xml_line : xml_en_xml_entity;
  
#line 237 "xml.h"
	{
	int _klen;
	unsigned int _trans;
	short _widec;
	const char *_acts;
	unsigned int _nacts;
	const short *_keys;

	if ( p == pe )
		goto _test_eof;
	if ( cs == 0 )
		goto _out;
_resume:
	_acts = _xml_actions + _xml_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 11:
#line 1 "NONE"
	{ts = p;}
	break;
#line 259 "xml.h"
		}
	}

	_widec = (*p);
	_klen = _xml_cond_lengths[cs];
	_keys = _xml_cond_keys + (_xml_cond_offsets[cs]*2);
	if ( _klen > 0 ) {
		const short *_lower = _keys;
		const short *_mid;
		const short *_upper = _keys + (_klen<<1) - 2;
		while (1) {
			if ( _upper < _lower )
				break;

			_mid = _lower + (((_upper-_lower) >> 1) & ~1);
			if ( _widec < _mid[0] )
				_upper = _mid - 2;
			else if ( _widec > _mid[1] )
				_lower = _mid + 2;
			else {
				switch ( _xml_cond_spaces[_xml_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
	case 0: {
		_widec = (short)(256 + ((*p) - 0));
		if ( 
#line 9 "common.rl"
 p+1 < pe && *(p+1) != '\n'  ) _widec += 256;
		break;
	}
				}
				break;
			}
		}
	}

	_keys = _xml_trans_keys + _xml_key_offsets[cs];
	_trans = _xml_index_offsets[cs];

	_klen = _xml_single_lengths[cs];
	if ( _klen > 0 ) {
		const short *_lower = _keys;
		const short *_mid;
		const short *_upper = _keys + _klen - 1;
		while (1) {
			if ( _upper < _lower )
				break;

			_mid = _lower + ((_upper-_lower) >> 1);
			if ( _widec < *_mid )
				_upper = _mid - 1;
			else if ( _widec > *_mid )
				_lower = _mid + 1;
			else {
				_trans += (unsigned int)(_mid - _keys);
				goto _match;
			}
		}
		_keys += _klen;
		_trans += _klen;
	}

	_klen = _xml_range_lengths[cs];
	if ( _klen > 0 ) {
		const short *_lower = _keys;
		const short *_mid;
		const short *_upper = _keys + (_klen<<1) - 2;
		while (1) {
			if ( _upper < _lower )
				break;

			_mid = _lower + (((_upper-_lower) >> 1) & ~1);
			if ( _widec < _mid[0] )
				_upper = _mid - 2;
			else if ( _widec > _mid[1] )
				_lower = _mid + 2;
			else {
				_trans += (unsigned int)((_mid - _keys)>>1);
				goto _match;
			}
		}
		_trans += _klen;
	}

_match:
	_trans = _xml_indicies[_trans];
_eof_trans:
	cs = _xml_trans_targs[_trans];

	if ( _xml_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _xml_actions + _xml_trans_actions[_trans];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 )
	{
		switch ( *_acts++ )
		{
	case 0:
#line 53 "common.rl"
	{
  if (!line_contains_code && !line_start) line_start = ts;
  line_contains_code = 1;
}
	break;
	case 1:
#line 58 "common.rl"
	{
  if (!line_contains_code) {
    whole_line_comment = 1;
    if (!line_start) line_start = ts;
  }
}
	break;
	case 2:
#line 33 "xml.rl"
	{
    switch(entity) {
    case XML_SPACE:
      ls
      break;
    case XML_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(XML_LANG)
      break;
    case NEWLINE:
      std_newline(XML_LANG)
      break;
    case CHECK_BLANK_ENTRY:
      check_blank_entry(XML_LANG)
    }
  }
	break;
	case 3:
#line 54 "xml.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 4:
#line 65 "xml.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 5:
#line 74 "xml.rl"
	{ entity = XML_SPACE; }
	break;
	case 6:
#line 77 "xml.rl"
	{ entity = NEWLINE;   }
	break;
	case 7:
#line 78 "xml.rl"
	{ entity = XML_ANY;   }
	break;
	case 8:
#line 90 "xml.rl"
	{ entity = XML_SPACE;   }
	break;
	case 9:
#line 91 "xml.rl"
	{ entity = XML_COMMENT; }
	break;
	case 12:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 13:
#line 75 "xml.rl"
	{te = p+1;}
	break;
	case 14:
#line 76 "xml.rl"
	{te = p+1;}
	break;
	case 15:
#line 33 "xml.rl"
	{te = p+1;{
    switch(entity) {
    case XML_SPACE:
      ls
      break;
    case XML_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(XML_LANG)
      break;
    case NEWLINE:
      std_newline(XML_LANG)
      break;
    case CHECK_BLANK_ENTRY:
      check_blank_entry(XML_LANG)
    }
  }}
	break;
	case 16:
#line 33 "xml.rl"
	{te = p+1;{
    switch(entity) {
    case XML_SPACE:
      ls
      break;
    case XML_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(XML_LANG)
      break;
    case NEWLINE:
      std_newline(XML_LANG)
      break;
    case CHECK_BLANK_ENTRY:
      check_blank_entry(XML_LANG)
    }
  }}
	break;
	case 17:
#line 33 "xml.rl"
	{te = p;p--;{
    switch(entity) {
    case XML_SPACE:
      ls
      break;
    case XML_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(XML_LANG)
      break;
    case NEWLINE:
      std_newline(XML_LANG)
      break;
    case CHECK_BLANK_ENTRY:
      check_blank_entry(XML_LANG)
    }
  }}
	break;
	case 18:
#line 33 "xml.rl"
	{te = p;p--;{
    switch(entity) {
    case XML_SPACE:
      ls
      break;
    case XML_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(XML_LANG)
      break;
    case NEWLINE:
      std_newline(XML_LANG)
      break;
    case CHECK_BLANK_ENTRY:
      check_blank_entry(XML_LANG)
    }
  }}
	break;
	case 19:
#line 33 "xml.rl"
	{te = p;p--;{
    switch(entity) {
    case XML_SPACE:
      ls
      break;
    case XML_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(XML_LANG)
      break;
    case NEWLINE:
      std_newline(XML_LANG)
      break;
    case CHECK_BLANK_ENTRY:
      check_blank_entry(XML_LANG)
    }
  }}
	break;
	case 20:
#line 33 "xml.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case XML_SPACE:
      ls
      break;
    case XML_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(XML_LANG)
      break;
    case NEWLINE:
      std_newline(XML_LANG)
      break;
    case CHECK_BLANK_ENTRY:
      check_blank_entry(XML_LANG)
    }
  }}
	break;
	case 21:
#line 83 "xml.rl"
	{te = p+1;{
    callback(XML_LANG, xml_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 22:
#line 93 "xml.rl"
	{te = p+1;}
	break;
	case 23:
#line 83 "xml.rl"
	{te = p;p--;{
    callback(XML_LANG, xml_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 24:
#line 93 "xml.rl"
	{te = p;p--;}
	break;
	case 25:
#line 93 "xml.rl"
	{{p = ((te))-1;}}
	break;
#line 583 "xml.h"
		}
	}

_again:
	_acts = _xml_actions + _xml_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 10:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 596 "xml.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _xml_eof_trans[cs] > 0 ) {
		_trans = _xml_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 120 "xml.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(XML_LANG) }
}

#endif

/*****************************************************************************/
