
#line 1 "dcl.rl"
// dcl.rl written by Mitchell Foral. mitchell<att>caladbolg<dott>net

/************************* Required for every parser *************************/
#ifndef OHCOUNT_DCL_PARSER_H
#define OHCOUNT_DCL_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *DCL_LANG = LANG_DCL;

// the languages entities
const char *dcl_entities[] = {
  "space", "line_start", "comment", "string", "any"
};

// constants associated with the entities
enum {
  DCL_SPACE = 0, DCL_LINE_START, DCL_COMMENT, DCL_STRING, DCL_ANY
};

/*****************************************************************************/


#line 28 "dcl.h"
static const char _dcl_actions[] = {
	0, 1, 3, 1, 4, 1, 6, 1, 
	7, 1, 8, 1, 9, 1, 12, 1, 
	15, 1, 16, 1, 17, 1, 18, 1, 
	19, 1, 20, 1, 21, 1, 22, 2, 
	1, 5, 2, 2, 11, 2, 4, 13, 
	2, 5, 14, 3, 10, 0, 5
};

static const char _dcl_cond_offsets[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	1, 1, 1, 1
};

static const char _dcl_cond_lengths[] = {
	0, 0, 0, 0, 0, 0, 0, 1, 
	0, 0, 0, 0
};

static const short _dcl_cond_keys[] = {
	13, 13, 0
};

static const char _dcl_cond_spaces[] = {
	0, 0
};

static const char _dcl_key_offsets[] = {
	0, 0, 5, 8, 9, 13, 16, 19, 
	32, 34, 37, 42
};

static const short _dcl_trans_keys[] = {
	10, 34, 92, 12, 13, 10, 12, 13, 
	10, 32, 33, 9, 13, 32, 9, 13, 
	10, 12, 13, 9, 10, 12, 32, 33, 
	34, 36, 269, 525, 0, 8, 14, 255, 
	9, 32, 10, 12, 13, 10, 34, 92, 
	12, 13, 10, 0
};

static const char _dcl_single_lengths[] = {
	0, 3, 1, 1, 2, 1, 1, 9, 
	2, 1, 3, 1
};

static const char _dcl_range_lengths[] = {
	0, 1, 1, 0, 1, 1, 1, 2, 
	0, 1, 1, 0
};

static const char _dcl_index_offsets[] = {
	0, 0, 5, 8, 10, 14, 17, 20, 
	32, 35, 38, 43
};

static const char _dcl_trans_targs[] = {
	7, 7, 2, 7, 1, 7, 7, 1, 
	7, 0, 5, 6, 5, 4, 5, 5, 
	4, 4, 4, 6, 8, 7, 7, 8, 
	9, 10, 7, 3, 11, 7, 7, 0, 
	8, 8, 7, 7, 7, 9, 7, 7, 
	2, 7, 1, 7, 7, 7, 7, 4, 
	4, 7, 7, 7, 7, 0
};

static const char _dcl_trans_actions[] = {
	23, 13, 0, 23, 0, 23, 23, 0, 
	37, 0, 5, 7, 5, 25, 5, 5, 
	27, 29, 29, 7, 1, 37, 37, 1, 
	31, 43, 34, 3, 3, 40, 40, 0, 
	1, 1, 15, 17, 17, 0, 21, 13, 
	0, 21, 0, 37, 19, 23, 23, 27, 
	29, 15, 17, 21, 19, 0
};

static const char _dcl_to_state_actions[] = {
	0, 0, 0, 0, 9, 0, 0, 9, 
	0, 0, 0, 0
};

static const char _dcl_from_state_actions[] = {
	0, 0, 0, 0, 11, 0, 0, 11, 
	0, 0, 0, 0
};

static const char _dcl_eof_trans[] = {
	0, 47, 47, 0, 0, 48, 49, 0, 
	50, 51, 52, 53
};

static const int dcl_start = 4;
static const int dcl_first_final = 4;
static const int dcl_error = 0;

static const int dcl_en_dcl_line = 7;
static const int dcl_en_dcl_entity = 4;


#line 75 "dcl.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with DCL code.
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
void parse_dcl(char *buffer, int length, int count,
               void (*callback) (const char *lang, const char *entity, int s,
                                 int e, void *udata),
               void *userdata
  ) {
  init

  
#line 152 "dcl.h"
	{
	cs = dcl_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 98 "dcl.rl"
  cs = (count) ? dcl_en_dcl_line : dcl_en_dcl_entity;
  
#line 163 "dcl.h"
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
	_acts = _dcl_actions + _dcl_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 9:
#line 1 "NONE"
	{ts = p;}
	break;
#line 185 "dcl.h"
		}
	}

	_widec = (*p);
	_klen = _dcl_cond_lengths[cs];
	_keys = _dcl_cond_keys + (_dcl_cond_offsets[cs]*2);
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
				switch ( _dcl_cond_spaces[_dcl_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
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

	_keys = _dcl_trans_keys + _dcl_key_offsets[cs];
	_trans = _dcl_index_offsets[cs];

	_klen = _dcl_single_lengths[cs];
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

	_klen = _dcl_range_lengths[cs];
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
_eof_trans:
	cs = _dcl_trans_targs[_trans];

	if ( _dcl_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _dcl_actions + _dcl_trans_actions[_trans];
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
#line 53 "dcl.rl"
	{ entity = DCL_LINE_START; }
	break;
	case 3:
#line 54 "dcl.rl"
	{ entity = DCL_SPACE;      }
	break;
	case 4:
#line 57 "dcl.rl"
	{ entity = NEWLINE;        }
	break;
	case 5:
#line 58 "dcl.rl"
	{ entity = DCL_ANY;        }
	break;
	case 6:
#line 70 "dcl.rl"
	{ entity = DCL_SPACE;   }
	break;
	case 7:
#line 71 "dcl.rl"
	{ entity = DCL_COMMENT; }
	break;
	case 10:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 11:
#line 31 "dcl.rl"
	{te = p+1;{
    switch(entity) {
    case DCL_SPACE:
    case DCL_LINE_START:
      ls
      break;
    case DCL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(DCL_LANG)
      break;
    case NEWLINE:
      std_newline(DCL_LANG)
    }
  }}
	break;
	case 12:
#line 56 "dcl.rl"
	{te = p+1;}
	break;
	case 13:
#line 31 "dcl.rl"
	{te = p+1;{
    switch(entity) {
    case DCL_SPACE:
    case DCL_LINE_START:
      ls
      break;
    case DCL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(DCL_LANG)
      break;
    case NEWLINE:
      std_newline(DCL_LANG)
    }
  }}
	break;
	case 14:
#line 31 "dcl.rl"
	{te = p+1;{
    switch(entity) {
    case DCL_SPACE:
    case DCL_LINE_START:
      ls
      break;
    case DCL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(DCL_LANG)
      break;
    case NEWLINE:
      std_newline(DCL_LANG)
    }
  }}
	break;
	case 15:
#line 31 "dcl.rl"
	{te = p;p--;{
    switch(entity) {
    case DCL_SPACE:
    case DCL_LINE_START:
      ls
      break;
    case DCL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(DCL_LANG)
      break;
    case NEWLINE:
      std_newline(DCL_LANG)
    }
  }}
	break;
	case 16:
#line 55 "dcl.rl"
	{te = p;p--;}
	break;
	case 17:
#line 31 "dcl.rl"
	{te = p;p--;{
    switch(entity) {
    case DCL_SPACE:
    case DCL_LINE_START:
      ls
      break;
    case DCL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(DCL_LANG)
      break;
    case NEWLINE:
      std_newline(DCL_LANG)
    }
  }}
	break;
	case 18:
#line 31 "dcl.rl"
	{te = p;p--;{
    switch(entity) {
    case DCL_SPACE:
    case DCL_LINE_START:
      ls
      break;
    case DCL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(DCL_LANG)
      break;
    case NEWLINE:
      std_newline(DCL_LANG)
    }
  }}
	break;
	case 19:
#line 31 "dcl.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case DCL_SPACE:
    case DCL_LINE_START:
      ls
      break;
    case DCL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(DCL_LANG)
      break;
    case NEWLINE:
      std_newline(DCL_LANG)
    }
  }}
	break;
	case 20:
#line 73 "dcl.rl"
	{te = p+1;}
	break;
	case 21:
#line 63 "dcl.rl"
	{te = p;p--;{
    callback(DCL_LANG, dcl_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 22:
#line 63 "dcl.rl"
	{te = p;p--;{
    callback(DCL_LANG, dcl_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
#line 482 "dcl.h"
		}
	}

_again:
	_acts = _dcl_actions + _dcl_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 8:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 495 "dcl.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _dcl_eof_trans[cs] > 0 ) {
		_trans = _dcl_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 100 "dcl.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(DCL_LANG) }
}

#endif

/*****************************************************************************/
