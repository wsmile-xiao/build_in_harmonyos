
#line 1 "vhdl.rl"
// vhdl.rl written by Mitchell Foral. mitchell<att>caladbolg<dott>net.

/************************* Required for every parser *************************/
#ifndef OHCOUNT_VHDL_PARSER_H
#define OHCOUNT_VHDL_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *VHDL_LANG = LANG_VHDL;

// the languages entities
const char *vhdl_entities[] = {
  "space", "comment", "string", "any"
};

// constants associated with the entities
enum {
  VHDL_SPACE = 0, VHDL_COMMENT, VHDL_STRING, VHDL_ANY
};

/*****************************************************************************/


#line 28 "vhdl.h"
static const char _vhdl_actions[] = {
	0, 1, 1, 1, 2, 1, 3, 1, 
	4, 1, 5, 1, 6, 1, 7, 1, 
	8, 1, 10, 1, 13, 1, 14, 1, 
	15, 1, 16, 1, 17, 1, 18, 1, 
	19, 1, 20, 1, 21, 2, 3, 11, 
	2, 4, 12, 3, 9, 0, 4
};

static const char _vhdl_cond_offsets[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 1, 1, 1, 1, 1, 1
};

static const char _vhdl_cond_lengths[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	1, 0, 0, 0, 0, 0, 0
};

static const short _vhdl_cond_keys[] = {
	13, 13, 0
};

static const char _vhdl_cond_spaces[] = {
	0, 0
};

static const char _vhdl_key_offsets[] = {
	0, 0, 4, 5, 6, 10, 13, 14, 
	17, 30, 32, 36, 40, 41, 44
};

static const short _vhdl_trans_keys[] = {
	10, 34, 12, 13, 39, 10, 32, 45, 
	9, 13, 32, 9, 13, 45, 10, 12, 
	13, 9, 10, 12, 32, 34, 39, 45, 
	269, 525, 0, 8, 14, 255, 9, 32, 
	10, 34, 12, 13, 10, 39, 12, 13, 
	45, 10, 12, 13, 10, 0
};

static const char _vhdl_single_lengths[] = {
	0, 2, 1, 1, 2, 1, 1, 1, 
	9, 2, 2, 2, 1, 1, 1
};

static const char _vhdl_range_lengths[] = {
	0, 1, 0, 0, 1, 1, 0, 1, 
	2, 0, 1, 1, 0, 1, 0
};

static const char _vhdl_index_offsets[] = {
	0, 0, 4, 6, 8, 12, 15, 17, 
	20, 32, 35, 39, 43, 45, 48
};

static const char _vhdl_trans_targs[] = {
	8, 8, 8, 1, 8, 8, 8, 0, 
	5, 6, 5, 4, 5, 5, 4, 7, 
	4, 4, 4, 7, 9, 8, 8, 9, 
	10, 11, 12, 3, 14, 8, 8, 0, 
	9, 9, 8, 8, 8, 8, 1, 8, 
	8, 8, 2, 13, 8, 8, 8, 13, 
	8, 8, 8, 8, 4, 4, 4, 8, 
	8, 8, 8, 8, 8, 0
};

static const char _vhdl_trans_actions[] = {
	27, 17, 27, 0, 17, 27, 37, 0, 
	9, 11, 9, 29, 9, 9, 31, 11, 
	35, 33, 33, 11, 3, 37, 37, 3, 
	43, 43, 7, 5, 5, 40, 40, 0, 
	3, 3, 19, 25, 17, 25, 0, 25, 
	25, 25, 0, 1, 25, 21, 21, 0, 
	37, 23, 27, 27, 31, 35, 33, 19, 
	25, 25, 25, 21, 23, 0
};

static const char _vhdl_to_state_actions[] = {
	0, 0, 0, 0, 13, 0, 0, 0, 
	13, 0, 0, 0, 0, 0, 0
};

static const char _vhdl_from_state_actions[] = {
	0, 0, 0, 0, 15, 0, 0, 0, 
	15, 0, 0, 0, 0, 0, 0
};

static const char _vhdl_eof_trans[] = {
	0, 52, 52, 0, 0, 53, 54, 55, 
	0, 56, 59, 59, 59, 60, 61
};

static const int vhdl_start = 4;
static const int vhdl_first_final = 4;
static const int vhdl_error = 0;

static const int vhdl_en_vhdl_line = 8;
static const int vhdl_en_vhdl_entity = 4;


#line 75 "vhdl.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with VHDL code.
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
void parse_vhdl(char *buffer, int length, int count,
                void (*callback) (const char *lang, const char *entity, int s,
                                  int e, void *udata),
                void *userdata
  ) {
  init

  
#line 154 "vhdl.h"
	{
	cs = vhdl_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 98 "vhdl.rl"
  cs = (count) ? vhdl_en_vhdl_line : vhdl_en_vhdl_entity;
  
#line 165 "vhdl.h"
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
	_acts = _vhdl_actions + _vhdl_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 8:
#line 1 "NONE"
	{ts = p;}
	break;
#line 187 "vhdl.h"
		}
	}

	_widec = (*p);
	_klen = _vhdl_cond_lengths[cs];
	_keys = _vhdl_cond_keys + (_vhdl_cond_offsets[cs]*2);
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
				switch ( _vhdl_cond_spaces[_vhdl_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
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

	_keys = _vhdl_trans_keys + _vhdl_key_offsets[cs];
	_trans = _vhdl_index_offsets[cs];

	_klen = _vhdl_single_lengths[cs];
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

	_klen = _vhdl_range_lengths[cs];
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
	cs = _vhdl_trans_targs[_trans];

	if ( _vhdl_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _vhdl_actions + _vhdl_trans_actions[_trans];
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
#line 54 "vhdl.rl"
	{ entity = VHDL_SPACE; }
	break;
	case 3:
#line 57 "vhdl.rl"
	{ entity = NEWLINE;    }
	break;
	case 4:
#line 58 "vhdl.rl"
	{ entity = VHDL_ANY;   }
	break;
	case 5:
#line 70 "vhdl.rl"
	{ entity = VHDL_SPACE; }
	break;
	case 6:
#line 71 "vhdl.rl"
	{ entity = VHDL_COMMENT; }
	break;
	case 9:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 10:
#line 56 "vhdl.rl"
	{te = p+1;}
	break;
	case 11:
#line 31 "vhdl.rl"
	{te = p+1;{
    switch(entity) {
    case VHDL_SPACE:
      ls
      break;
    case VHDL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(VHDL_LANG)
      break;
    case NEWLINE:
      std_newline(VHDL_LANG)
    }
  }}
	break;
	case 12:
#line 31 "vhdl.rl"
	{te = p+1;{
    switch(entity) {
    case VHDL_SPACE:
      ls
      break;
    case VHDL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(VHDL_LANG)
      break;
    case NEWLINE:
      std_newline(VHDL_LANG)
    }
  }}
	break;
	case 13:
#line 31 "vhdl.rl"
	{te = p;p--;{
    switch(entity) {
    case VHDL_SPACE:
      ls
      break;
    case VHDL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(VHDL_LANG)
      break;
    case NEWLINE:
      std_newline(VHDL_LANG)
    }
  }}
	break;
	case 14:
#line 55 "vhdl.rl"
	{te = p;p--;}
	break;
	case 15:
#line 31 "vhdl.rl"
	{te = p;p--;{
    switch(entity) {
    case VHDL_SPACE:
      ls
      break;
    case VHDL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(VHDL_LANG)
      break;
    case NEWLINE:
      std_newline(VHDL_LANG)
    }
  }}
	break;
	case 16:
#line 31 "vhdl.rl"
	{te = p;p--;{
    switch(entity) {
    case VHDL_SPACE:
      ls
      break;
    case VHDL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(VHDL_LANG)
      break;
    case NEWLINE:
      std_newline(VHDL_LANG)
    }
  }}
	break;
	case 17:
#line 31 "vhdl.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case VHDL_SPACE:
      ls
      break;
    case VHDL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(VHDL_LANG)
      break;
    case NEWLINE:
      std_newline(VHDL_LANG)
    }
  }}
	break;
	case 18:
#line 73 "vhdl.rl"
	{te = p+1;}
	break;
	case 19:
#line 63 "vhdl.rl"
	{te = p;p--;{
    callback(VHDL_LANG, vhdl_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 20:
#line 63 "vhdl.rl"
	{te = p;p--;{
    callback(VHDL_LANG, vhdl_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 21:
#line 73 "vhdl.rl"
	{te = p;p--;}
	break;
#line 459 "vhdl.h"
		}
	}

_again:
	_acts = _vhdl_actions + _vhdl_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 7:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 472 "vhdl.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _vhdl_eof_trans[cs] > 0 ) {
		_trans = _vhdl_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 100 "vhdl.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(VHDL_LANG) }
}

#endif

/*****************************************************************************/
