
#line 1 "metapost_with_tex.rl.tmp"
// mp_with_tex.rl written by Mitchell Foral. mitchell<att>caladbolg<dott>net.

/************************* Required for every parser *************************/
#ifndef OHCOUNT_MPTEX_PARSER_H
#define OHCOUNT_MPTEX_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *MPTEX_LANG = LANG_METAPOST;

// the languages entities
const char *mptex_entities[] = {
  "space", "comment", "string", "any"
};


// constants associated with the entities
enum {
  MPTEX_SPACE = 0, MPTEX_COMMENT, MPTEX_STRING, MPTEX_ANY
};

/*****************************************************************************/

#include "tex.h"


#line 31 "metapost_with_tex.h"
static const char _mptex_actions[] = {
	0, 1, 3, 1, 4, 1, 6, 1, 
	7, 1, 11, 1, 12, 1, 16, 1, 
	17, 1, 20, 1, 21, 1, 22, 1, 
	23, 1, 24, 1, 25, 1, 26, 1, 
	29, 1, 30, 1, 31, 1, 32, 1, 
	33, 1, 34, 1, 38, 1, 39, 1, 
	40, 1, 41, 1, 42, 1, 44, 1, 
	47, 1, 48, 1, 49, 1, 50, 1, 
	51, 1, 53, 1, 54, 1, 55, 1, 
	56, 1, 57, 1, 58, 1, 59, 1, 
	60, 1, 61, 1, 62, 1, 63, 2, 
	1, 5, 2, 1, 13, 2, 4, 27, 
	2, 5, 28, 2, 12, 36, 2, 13, 
	37, 2, 17, 45, 2, 18, 46, 2, 
	19, 52, 2, 26, 13, 2, 26, 18, 
	3, 9, 1, 18, 3, 26, 0, 18, 
	4, 2, 0, 10, 35, 5, 0, 14, 
	8, 15, 43
};

static const char _mptex_cond_offsets[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 1, 1, 1, 1, 1, 1, 
	1, 2, 2, 2, 2, 2, 3, 3, 
	3, 3, 3, 3, 3, 3, 3, 3
};

static const char _mptex_cond_lengths[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 1, 0, 0, 0, 0, 0, 0, 
	1, 0, 0, 0, 0, 1, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0
};

static const short _mptex_cond_keys[] = {
	13, 13, 13, 13, 13, 13, 0
};

static const char _mptex_cond_spaces[] = {
	0, 0, 0, 0
};

static const char _mptex_key_offsets[] = {
	0, 0, 1, 2, 3, 4, 5, 6, 
	7, 8, 9, 10, 11, 12, 13, 18, 
	21, 22, 23, 24, 25, 26, 27, 28, 
	29, 30, 31, 32, 33, 39, 42, 45, 
	46, 47, 58, 60, 63, 64, 68, 71, 
	74, 86, 88, 91, 92, 93, 107, 109, 
	114, 117, 118, 119, 120, 125, 128, 131
};

static const short _mptex_trans_keys[] = {
	101, 120, 114, 98, 97, 116, 105, 109, 
	116, 10, 101, 120, 10, 10, 34, 92, 
	12, 13, 10, 12, 13, 101, 120, 114, 
	98, 97, 116, 105, 109, 116, 10, 101, 
	120, 32, 37, 98, 118, 9, 13, 32, 
	9, 13, 10, 12, 13, 116, 101, 9, 
	10, 12, 32, 37, 269, 525, 0, 8, 
	14, 255, 9, 32, 10, 12, 13, 10, 
	32, 37, 9, 13, 32, 9, 13, 10, 
	12, 13, 9, 10, 12, 32, 37, 101, 
	269, 525, 0, 8, 14, 255, 9, 32, 
	10, 12, 13, 116, 10, 9, 10, 12, 
	32, 34, 37, 98, 118, 269, 525, 0, 
	8, 14, 255, 9, 32, 10, 34, 92, 
	12, 13, 10, 12, 13, 116, 101, 10, 
	32, 37, 101, 9, 13, 32, 9, 13, 
	10, 12, 13, 116, 0
};

static const char _mptex_single_lengths[] = {
	0, 1, 1, 1, 1, 1, 1, 1, 
	1, 1, 1, 1, 1, 1, 3, 1, 
	1, 1, 1, 1, 1, 1, 1, 1, 
	1, 1, 1, 1, 4, 1, 1, 1, 
	1, 7, 2, 1, 1, 2, 1, 1, 
	8, 2, 1, 1, 1, 10, 2, 3, 
	1, 1, 1, 1, 3, 1, 1, 1
};

static const char _mptex_range_lengths[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 1, 1, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 1, 1, 1, 0, 
	0, 2, 0, 1, 0, 1, 1, 1, 
	2, 0, 1, 0, 0, 2, 0, 1, 
	1, 0, 0, 0, 1, 1, 1, 0
};

static const char _mptex_index_offsets[] = {
	0, 0, 2, 4, 6, 8, 10, 12, 
	14, 16, 18, 20, 22, 24, 26, 31, 
	34, 36, 38, 40, 42, 44, 46, 48, 
	50, 52, 54, 56, 58, 64, 67, 70, 
	72, 74, 84, 87, 90, 92, 96, 99, 
	102, 113, 116, 119, 121, 123, 136, 139, 
	144, 147, 149, 151, 153, 158, 161, 164
};

static const char _mptex_trans_targs[] = {
	2, 28, 28, 28, 4, 28, 5, 28, 
	6, 28, 7, 28, 8, 28, 9, 28, 
	1, 28, 33, 0, 12, 40, 40, 40, 
	40, 0, 45, 45, 15, 45, 14, 45, 
	45, 14, 17, 45, 45, 45, 19, 45, 
	20, 45, 21, 45, 22, 45, 23, 45, 
	24, 45, 16, 45, 45, 0, 27, 52, 
	52, 52, 29, 30, 31, 32, 29, 28, 
	29, 29, 28, 28, 28, 30, 1, 28, 
	3, 28, 34, 33, 33, 34, 35, 10, 
	36, 33, 33, 0, 34, 34, 33, 33, 
	33, 35, 33, 33, 38, 39, 38, 37, 
	38, 38, 37, 37, 37, 39, 41, 40, 
	40, 41, 42, 43, 13, 44, 40, 40, 
	0, 41, 41, 40, 40, 40, 42, 11, 
	40, 40, 40, 46, 45, 45, 46, 47, 
	48, 49, 50, 25, 51, 45, 45, 0, 
	46, 46, 45, 45, 45, 15, 45, 14, 
	45, 45, 48, 16, 45, 18, 45, 45, 
	45, 53, 54, 55, 53, 52, 53, 53, 
	52, 52, 52, 54, 26, 52, 28, 28, 
	28, 28, 28, 28, 28, 28, 28, 40, 
	40, 45, 45, 45, 45, 45, 45, 45, 
	45, 45, 45, 45, 52, 52, 28, 28, 
	28, 28, 33, 33, 33, 37, 37, 40, 
	40, 40, 40, 45, 45, 45, 45, 45, 
	45, 52, 52, 52, 0
};

static const char _mptex_trans_actions[] = {
	0, 85, 75, 85, 0, 85, 0, 85, 
	0, 85, 0, 85, 0, 85, 0, 85, 
	0, 85, 93, 0, 0, 51, 128, 51, 
	99, 0, 63, 53, 0, 63, 0, 63, 
	63, 0, 0, 63, 133, 63, 0, 63, 
	0, 63, 0, 63, 0, 63, 0, 63, 
	0, 63, 0, 63, 105, 0, 0, 73, 
	111, 73, 21, 23, 29, 29, 21, 77, 
	21, 21, 79, 81, 81, 23, 0, 83, 
	0, 83, 1, 93, 93, 1, 87, 3, 
	3, 96, 96, 0, 1, 1, 31, 33, 
	33, 0, 93, 35, 5, 7, 5, 37, 
	5, 5, 39, 41, 41, 7, 9, 99, 
	99, 9, 90, 114, 11, 11, 102, 102, 
	0, 9, 9, 43, 45, 45, 0, 0, 
	49, 99, 47, 13, 105, 105, 13, 124, 
	120, 117, 117, 15, 15, 108, 108, 0, 
	13, 13, 55, 61, 53, 0, 61, 0, 
	57, 57, 0, 0, 61, 0, 61, 105, 
	59, 17, 19, 29, 17, 65, 17, 17, 
	67, 69, 69, 19, 0, 71, 85, 85, 
	85, 85, 85, 85, 85, 85, 85, 51, 
	51, 63, 63, 63, 63, 63, 63, 63, 
	63, 63, 63, 63, 73, 73, 79, 81, 
	83, 83, 31, 33, 35, 39, 41, 43, 
	45, 49, 47, 55, 61, 57, 61, 61, 
	59, 67, 69, 71, 0
};

static const char _mptex_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 25, 0, 0, 0, 
	0, 25, 0, 0, 0, 25, 0, 0, 
	25, 0, 0, 0, 0, 25, 0, 0, 
	0, 0, 0, 0, 25, 0, 0, 0
};

static const char _mptex_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 27, 0, 0, 0, 
	0, 27, 0, 0, 0, 27, 0, 0, 
	27, 0, 0, 0, 0, 27, 0, 0, 
	0, 0, 0, 0, 27, 0, 0, 0
};

static const char _mptex_eof_trans[] = {
	0, 175, 175, 175, 175, 175, 175, 175, 
	175, 175, 0, 177, 177, 0, 188, 188, 
	188, 188, 188, 188, 188, 188, 188, 188, 
	188, 0, 190, 190, 0, 191, 192, 194, 
	194, 0, 195, 196, 197, 0, 198, 199, 
	0, 200, 201, 202, 203, 0, 204, 208, 
	206, 208, 208, 209, 0, 210, 211, 212
};

static const int mptex_start = 28;
static const int mptex_first_final = 28;
static const int mptex_error = 0;

static const int mptex_en_tex_line = 33;
static const int mptex_en_tex_entity = 37;
static const int mptex_en_mptex_tex_line = 40;
static const int mptex_en_mptex_line = 45;
static const int mptex_en_mptex_tex_entity = 52;
static const int mptex_en_mptex_entity = 28;


#line 32 "metapost_with_tex.rl.tmp"


#line 157 "metapost_with_tex.rl.tmp"


/************************* Required for every parser *************************/

/* Parses a string buffer with Metapost code.
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
void parse_mptex(char *buffer, int length, int count,
                 void (*callback) (const char *lang, const char *entity, int s,
                                   int e, void *udata),
                 void *userdata
  ) {
  init

  
#line 270 "metapost_with_tex.h"
	{
	cs = mptex_start;
	top = 0;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 180 "metapost_with_tex.rl.tmp"
  cs = (count) ? mptex_en_mptex_line : mptex_en_mptex_entity;
  
#line 282 "metapost_with_tex.h"
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
	_acts = _mptex_actions + _mptex_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 25:
#line 1 "NONE"
	{ts = p;}
	break;
#line 304 "metapost_with_tex.h"
		}
	}

	_widec = (*p);
	_klen = _mptex_cond_lengths[cs];
	_keys = _mptex_cond_keys + (_mptex_cond_offsets[cs]*2);
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
				switch ( _mptex_cond_spaces[_mptex_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
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

	_keys = _mptex_trans_keys + _mptex_key_offsets[cs];
	_trans = _mptex_index_offsets[cs];

	_klen = _mptex_single_lengths[cs];
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

	_klen = _mptex_range_lengths[cs];
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
	cs = _mptex_trans_targs[_trans];

	if ( _mptex_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _mptex_actions + _mptex_trans_actions[_trans];
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
#line 65 "common.rl"
	{
  if (!line_contains_code && !whole_line_comment) seen = 0;
}
	break;
	case 3:
#line 60 "metapost_with_tex.rl.tmp"
	{ entity = TEX_SPACE; }
	break;
	case 4:
#line 62 "metapost_with_tex.rl.tmp"
	{ entity = NEWLINE;   }
	break;
	case 5:
#line 63 "metapost_with_tex.rl.tmp"
	{ entity = TEX_ANY;   }
	break;
	case 6:
#line 75 "metapost_with_tex.rl.tmp"
	{ entity = TEX_SPACE;   }
	break;
	case 7:
#line 76 "metapost_with_tex.rl.tmp"
	{ entity = TEX_COMMENT; }
	break;
	case 8:
#line 84 "metapost_with_tex.rl.tmp"
	{
    switch(entity) {
    case MPTEX_SPACE:
      ls
      break;
    case MPTEX_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(MPTEX_LANG)
      break;
    case NEWLINE:
      std_newline(MPTEX_LANG)
      break;
    case CHECK_BLANK_ENTRY:
      check_blank_entry(MPTEX_LANG)
    }
  }
	break;
	case 9:
#line 103 "metapost_with_tex.rl.tmp"
	{ p--; }
	break;
	case 10:
#line 110 "metapost_with_tex.rl.tmp"
	{ p = ts; {cs = stack[--top]; goto _again;} }
	break;
	case 11:
#line 112 "metapost_with_tex.rl.tmp"
	{ entity = TEX_SPACE; }
	break;
	case 12:
#line 114 "metapost_with_tex.rl.tmp"
	{ entity = NEWLINE;   }
	break;
	case 13:
#line 115 "metapost_with_tex.rl.tmp"
	{ entity = TEX_ANY;   }
	break;
	case 14:
#line 119 "metapost_with_tex.rl.tmp"
	{ entity = CHECK_BLANK_ENTRY; }
	break;
	case 15:
#line 120 "metapost_with_tex.rl.tmp"
	{ saw(TEX_LANG); }
	break;
	case 16:
#line 122 "metapost_with_tex.rl.tmp"
	{ entity = MPTEX_SPACE; }
	break;
	case 17:
#line 125 "metapost_with_tex.rl.tmp"
	{ entity = NEWLINE;        }
	break;
	case 18:
#line 126 "metapost_with_tex.rl.tmp"
	{ entity = MPTEX_ANY;   }
	break;
	case 19:
#line 138 "metapost_with_tex.rl.tmp"
	{ {cs = stack[--top]; goto _again;} }
	break;
	case 20:
#line 140 "metapost_with_tex.rl.tmp"
	{ entity = TEX_SPACE;   }
	break;
	case 21:
#line 141 "metapost_with_tex.rl.tmp"
	{ entity = TEX_COMMENT; }
	break;
	case 22:
#line 152 "metapost_with_tex.rl.tmp"
	{ entity = MPTEX_SPACE;   }
	break;
	case 23:
#line 153 "metapost_with_tex.rl.tmp"
	{ entity = MPTEX_COMMENT; }
	break;
	case 26:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 27:
#line 41 "metapost_with_tex.rl.tmp"
	{te = p+1;{
    switch(entity) {
    case TEX_SPACE:
      ls
      break;
    case TEX_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(TEX_LANG)
      break;
    case NEWLINE:
      std_newline(TEX_LANG)
    }
  }}
	break;
	case 28:
#line 41 "metapost_with_tex.rl.tmp"
	{te = p+1;{
    switch(entity) {
    case TEX_SPACE:
      ls
      break;
    case TEX_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(TEX_LANG)
      break;
    case NEWLINE:
      std_newline(TEX_LANG)
    }
  }}
	break;
	case 29:
#line 41 "metapost_with_tex.rl.tmp"
	{te = p;p--;{
    switch(entity) {
    case TEX_SPACE:
      ls
      break;
    case TEX_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(TEX_LANG)
      break;
    case NEWLINE:
      std_newline(TEX_LANG)
    }
  }}
	break;
	case 30:
#line 61 "metapost_with_tex.rl.tmp"
	{te = p;p--;}
	break;
	case 31:
#line 41 "metapost_with_tex.rl.tmp"
	{te = p;p--;{
    switch(entity) {
    case TEX_SPACE:
      ls
      break;
    case TEX_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(TEX_LANG)
      break;
    case NEWLINE:
      std_newline(TEX_LANG)
    }
  }}
	break;
	case 32:
#line 78 "metapost_with_tex.rl.tmp"
	{te = p+1;}
	break;
	case 33:
#line 68 "metapost_with_tex.rl.tmp"
	{te = p;p--;{
    callback(TEX_LANG, tex_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 34:
#line 68 "metapost_with_tex.rl.tmp"
	{te = p;p--;{
    callback(TEX_LANG, tex_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 35:
#line 110 "metapost_with_tex.rl.tmp"
	{te = p+1;}
	break;
	case 36:
#line 41 "metapost_with_tex.rl.tmp"
	{te = p+1;{
    switch(entity) {
    case TEX_SPACE:
      ls
      break;
    case TEX_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(TEX_LANG)
      break;
    case NEWLINE:
      std_newline(TEX_LANG)
    }
  }}
	break;
	case 37:
#line 41 "metapost_with_tex.rl.tmp"
	{te = p+1;{
    switch(entity) {
    case TEX_SPACE:
      ls
      break;
    case TEX_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(TEX_LANG)
      break;
    case NEWLINE:
      std_newline(TEX_LANG)
    }
  }}
	break;
	case 38:
#line 41 "metapost_with_tex.rl.tmp"
	{te = p;p--;{
    switch(entity) {
    case TEX_SPACE:
      ls
      break;
    case TEX_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(TEX_LANG)
      break;
    case NEWLINE:
      std_newline(TEX_LANG)
    }
  }}
	break;
	case 39:
#line 113 "metapost_with_tex.rl.tmp"
	{te = p;p--;}
	break;
	case 40:
#line 41 "metapost_with_tex.rl.tmp"
	{te = p;p--;{
    switch(entity) {
    case TEX_SPACE:
      ls
      break;
    case TEX_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(TEX_LANG)
      break;
    case NEWLINE:
      std_newline(TEX_LANG)
    }
  }}
	break;
	case 41:
#line 41 "metapost_with_tex.rl.tmp"
	{te = p;p--;{
    switch(entity) {
    case TEX_SPACE:
      ls
      break;
    case TEX_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(TEX_LANG)
      break;
    case NEWLINE:
      std_newline(TEX_LANG)
    }
  }}
	break;
	case 42:
#line 41 "metapost_with_tex.rl.tmp"
	{{p = ((te))-1;}{
    switch(entity) {
    case TEX_SPACE:
      ls
      break;
    case TEX_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(TEX_LANG)
      break;
    case NEWLINE:
      std_newline(TEX_LANG)
    }
  }}
	break;
	case 43:
#line 120 "metapost_with_tex.rl.tmp"
	{te = p+1;{ {stack[top++] = cs; cs = 40;goto _again;} }}
	break;
	case 44:
#line 124 "metapost_with_tex.rl.tmp"
	{te = p+1;}
	break;
	case 45:
#line 84 "metapost_with_tex.rl.tmp"
	{te = p+1;{
    switch(entity) {
    case MPTEX_SPACE:
      ls
      break;
    case MPTEX_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(MPTEX_LANG)
      break;
    case NEWLINE:
      std_newline(MPTEX_LANG)
      break;
    case CHECK_BLANK_ENTRY:
      check_blank_entry(MPTEX_LANG)
    }
  }}
	break;
	case 46:
#line 84 "metapost_with_tex.rl.tmp"
	{te = p+1;{
    switch(entity) {
    case MPTEX_SPACE:
      ls
      break;
    case MPTEX_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(MPTEX_LANG)
      break;
    case NEWLINE:
      std_newline(MPTEX_LANG)
      break;
    case CHECK_BLANK_ENTRY:
      check_blank_entry(MPTEX_LANG)
    }
  }}
	break;
	case 47:
#line 84 "metapost_with_tex.rl.tmp"
	{te = p;p--;{
    switch(entity) {
    case MPTEX_SPACE:
      ls
      break;
    case MPTEX_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(MPTEX_LANG)
      break;
    case NEWLINE:
      std_newline(MPTEX_LANG)
      break;
    case CHECK_BLANK_ENTRY:
      check_blank_entry(MPTEX_LANG)
    }
  }}
	break;
	case 48:
#line 123 "metapost_with_tex.rl.tmp"
	{te = p;p--;}
	break;
	case 49:
#line 84 "metapost_with_tex.rl.tmp"
	{te = p;p--;{
    switch(entity) {
    case MPTEX_SPACE:
      ls
      break;
    case MPTEX_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(MPTEX_LANG)
      break;
    case NEWLINE:
      std_newline(MPTEX_LANG)
      break;
    case CHECK_BLANK_ENTRY:
      check_blank_entry(MPTEX_LANG)
    }
  }}
	break;
	case 50:
#line 84 "metapost_with_tex.rl.tmp"
	{te = p;p--;{
    switch(entity) {
    case MPTEX_SPACE:
      ls
      break;
    case MPTEX_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(MPTEX_LANG)
      break;
    case NEWLINE:
      std_newline(MPTEX_LANG)
      break;
    case CHECK_BLANK_ENTRY:
      check_blank_entry(MPTEX_LANG)
    }
  }}
	break;
	case 51:
#line 84 "metapost_with_tex.rl.tmp"
	{{p = ((te))-1;}{
    switch(entity) {
    case MPTEX_SPACE:
      ls
      break;
    case MPTEX_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(MPTEX_LANG)
      break;
    case NEWLINE:
      std_newline(MPTEX_LANG)
      break;
    case CHECK_BLANK_ENTRY:
      check_blank_entry(MPTEX_LANG)
    }
  }}
	break;
	case 52:
#line 138 "metapost_with_tex.rl.tmp"
	{te = p+1;}
	break;
	case 53:
#line 143 "metapost_with_tex.rl.tmp"
	{te = p+1;}
	break;
	case 54:
#line 68 "metapost_with_tex.rl.tmp"
	{te = p;p--;{
    callback(TEX_LANG, tex_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 55:
#line 68 "metapost_with_tex.rl.tmp"
	{te = p;p--;{
    callback(TEX_LANG, tex_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 56:
#line 143 "metapost_with_tex.rl.tmp"
	{te = p;p--;}
	break;
	case 57:
#line 143 "metapost_with_tex.rl.tmp"
	{{p = ((te))-1;}}
	break;
	case 58:
#line 150 "metapost_with_tex.rl.tmp"
	{te = p+1;{ {stack[top++] = cs; cs = 52;goto _again;} }}
	break;
	case 59:
#line 155 "metapost_with_tex.rl.tmp"
	{te = p+1;}
	break;
	case 60:
#line 131 "metapost_with_tex.rl.tmp"
	{te = p;p--;{
    callback(MPTEX_LANG, mptex_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 61:
#line 131 "metapost_with_tex.rl.tmp"
	{te = p;p--;{
    callback(MPTEX_LANG, mptex_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 62:
#line 155 "metapost_with_tex.rl.tmp"
	{te = p;p--;}
	break;
	case 63:
#line 155 "metapost_with_tex.rl.tmp"
	{{p = ((te))-1;}}
	break;
#line 929 "metapost_with_tex.h"
		}
	}

_again:
	_acts = _mptex_actions + _mptex_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 24:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 942 "metapost_with_tex.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _mptex_eof_trans[cs] > 0 ) {
		_trans = _mptex_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 182 "metapost_with_tex.rl.tmp"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(MPTEX_LANG) }
}

#endif

/*****************************************************************************/
