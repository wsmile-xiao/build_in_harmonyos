
#line 1 "ada.rl"
// ada.rl written by Mitchell Foral. mitchell<att>caladbolg<dott>net.

/************************* Required for every parser *************************/
#ifndef OHCOUNT_ADA_PARSER_H
#define OHCOUNT_ADA_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *ADA_LANG = LANG_ADA;

// the languages entities
const char *ada_entities[] = {
  "space", "comment", "string", "any"
};

// constants associated with the entities
enum {
  ADA_SPACE = 0, ADA_COMMENT, ADA_STRING, ADA_ANY
};

/*****************************************************************************/


#line 28 "ada.h"
static const char _ada_actions[] = {
	0, 1, 1, 1, 2, 1, 3, 1, 
	4, 1, 5, 1, 6, 1, 7, 1, 
	8, 1, 10, 1, 13, 1, 14, 1, 
	15, 1, 16, 1, 17, 1, 18, 1, 
	19, 1, 20, 1, 21, 2, 3, 11, 
	2, 4, 12, 3, 9, 0, 4
};

static const char _ada_cond_offsets[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	1, 1, 1, 1, 1
};

static const char _ada_cond_lengths[] = {
	0, 0, 0, 0, 0, 0, 0, 1, 
	0, 0, 0, 0, 0
};

static const short _ada_cond_keys[] = {
	13, 13, 0
};

static const char _ada_cond_spaces[] = {
	0, 0
};

static const char _ada_key_offsets[] = {
	0, 0, 4, 5, 9, 12, 13, 16, 
	28, 30, 34, 35, 38
};

static const short _ada_trans_keys[] = {
	10, 34, 12, 13, 10, 32, 45, 9, 
	13, 32, 9, 13, 45, 10, 12, 13, 
	9, 10, 12, 32, 34, 45, 269, 525, 
	0, 8, 14, 255, 9, 32, 10, 34, 
	12, 13, 45, 10, 12, 13, 10, 0
};

static const char _ada_single_lengths[] = {
	0, 2, 1, 2, 1, 1, 1, 8, 
	2, 2, 1, 1, 1
};

static const char _ada_range_lengths[] = {
	0, 1, 0, 1, 1, 0, 1, 2, 
	0, 1, 0, 1, 0
};

static const char _ada_index_offsets[] = {
	0, 0, 4, 6, 10, 13, 15, 18, 
	29, 32, 36, 38, 41
};

static const char _ada_trans_targs[] = {
	7, 7, 7, 1, 7, 0, 4, 5, 
	4, 3, 4, 4, 3, 6, 3, 3, 
	3, 6, 8, 7, 7, 8, 9, 10, 
	2, 12, 7, 7, 0, 8, 8, 7, 
	7, 7, 7, 1, 11, 7, 7, 7, 
	11, 7, 7, 7, 3, 3, 3, 7, 
	7, 7, 7, 7, 0
};

static const char _ada_trans_actions[] = {
	27, 17, 27, 0, 37, 0, 9, 11, 
	9, 29, 9, 9, 31, 11, 35, 33, 
	33, 11, 3, 37, 37, 3, 43, 7, 
	5, 5, 40, 40, 0, 3, 3, 19, 
	25, 17, 25, 0, 1, 25, 21, 21, 
	0, 37, 23, 27, 31, 35, 33, 19, 
	25, 25, 21, 23, 0
};

static const char _ada_to_state_actions[] = {
	0, 0, 0, 13, 0, 0, 0, 13, 
	0, 0, 0, 0, 0
};

static const char _ada_from_state_actions[] = {
	0, 0, 0, 15, 0, 0, 0, 15, 
	0, 0, 0, 0, 0
};

static const char _ada_eof_trans[] = {
	0, 44, 0, 0, 45, 46, 47, 0, 
	48, 50, 50, 51, 52
};

static const int ada_start = 3;
static const int ada_first_final = 3;
static const int ada_error = 0;

static const int ada_en_ada_line = 7;
static const int ada_en_ada_entity = 3;


#line 73 "ada.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with Ada code.
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
void parse_ada(char *buffer, int length, int count,
               void (*callback) (const char *lang, const char *entity, int s,
                                 int e, void *udata),
               void *userdata
  ) {
  init

  
#line 151 "ada.h"
	{
	cs = ada_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 96 "ada.rl"
  cs = (count) ? ada_en_ada_line : ada_en_ada_entity;
  
#line 162 "ada.h"
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
	_acts = _ada_actions + _ada_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 8:
#line 1 "NONE"
	{ts = p;}
	break;
#line 184 "ada.h"
		}
	}

	_widec = (*p);
	_klen = _ada_cond_lengths[cs];
	_keys = _ada_cond_keys + (_ada_cond_offsets[cs]*2);
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
				switch ( _ada_cond_spaces[_ada_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
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

	_keys = _ada_trans_keys + _ada_key_offsets[cs];
	_trans = _ada_index_offsets[cs];

	_klen = _ada_single_lengths[cs];
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

	_klen = _ada_range_lengths[cs];
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
	cs = _ada_trans_targs[_trans];

	if ( _ada_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _ada_actions + _ada_trans_actions[_trans];
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
#line 52 "ada.rl"
	{ entity = ADA_SPACE; }
	break;
	case 3:
#line 55 "ada.rl"
	{ entity = NEWLINE;   }
	break;
	case 4:
#line 56 "ada.rl"
	{ entity = ADA_ANY;   }
	break;
	case 5:
#line 68 "ada.rl"
	{ entity = ADA_SPACE;   }
	break;
	case 6:
#line 69 "ada.rl"
	{ entity = ADA_COMMENT; }
	break;
	case 9:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 10:
#line 54 "ada.rl"
	{te = p+1;}
	break;
	case 11:
#line 31 "ada.rl"
	{te = p+1;{
    switch(entity) {
    case ADA_SPACE:
      ls
      break;
    case ADA_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(ADA_LANG)
      break;
    case NEWLINE:
      std_newline(ADA_LANG)
    }
  }}
	break;
	case 12:
#line 31 "ada.rl"
	{te = p+1;{
    switch(entity) {
    case ADA_SPACE:
      ls
      break;
    case ADA_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(ADA_LANG)
      break;
    case NEWLINE:
      std_newline(ADA_LANG)
    }
  }}
	break;
	case 13:
#line 31 "ada.rl"
	{te = p;p--;{
    switch(entity) {
    case ADA_SPACE:
      ls
      break;
    case ADA_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(ADA_LANG)
      break;
    case NEWLINE:
      std_newline(ADA_LANG)
    }
  }}
	break;
	case 14:
#line 53 "ada.rl"
	{te = p;p--;}
	break;
	case 15:
#line 31 "ada.rl"
	{te = p;p--;{
    switch(entity) {
    case ADA_SPACE:
      ls
      break;
    case ADA_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(ADA_LANG)
      break;
    case NEWLINE:
      std_newline(ADA_LANG)
    }
  }}
	break;
	case 16:
#line 31 "ada.rl"
	{te = p;p--;{
    switch(entity) {
    case ADA_SPACE:
      ls
      break;
    case ADA_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(ADA_LANG)
      break;
    case NEWLINE:
      std_newline(ADA_LANG)
    }
  }}
	break;
	case 17:
#line 31 "ada.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case ADA_SPACE:
      ls
      break;
    case ADA_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(ADA_LANG)
      break;
    case NEWLINE:
      std_newline(ADA_LANG)
    }
  }}
	break;
	case 18:
#line 71 "ada.rl"
	{te = p+1;}
	break;
	case 19:
#line 61 "ada.rl"
	{te = p;p--;{
    callback(ADA_LANG, ada_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 20:
#line 61 "ada.rl"
	{te = p;p--;{
    callback(ADA_LANG, ada_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 21:
#line 71 "ada.rl"
	{te = p;p--;}
	break;
#line 456 "ada.h"
		}
	}

_again:
	_acts = _ada_actions + _ada_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 7:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 469 "ada.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _ada_eof_trans[cs] > 0 ) {
		_trans = _ada_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 98 "ada.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(ADA_LANG) }
}

#endif

/*****************************************************************************/
