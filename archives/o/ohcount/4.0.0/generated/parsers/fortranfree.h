
#line 1 "fortranfree.rl"
// fortranfree.rl written by Mitchell Foral. mitchell<att>caladbolg<dott>net.

/************************* Required for every parser *************************/
#ifndef OHCOUNT_FORTRANFREE_PARSER_H
#define OHCOUNT_FORTRANFREE_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *FORTRANFREE_LANG = LANG_FORTRANFREE;

// the languages entities
const char *ffree_entities[] = {
  "space", "comment", "string", "any"
};

// constants associated with the entities
enum {
  FFREE_SPACE = 0, FFREE_COMMENT, FFREE_STRING, FFREE_ANY
};

/*****************************************************************************/


#line 28 "fortranfree.h"
static const char _fortranfree_actions[] = {
	0, 1, 0, 1, 5, 1, 6, 1, 
	8, 1, 9, 1, 10, 1, 11, 1, 
	13, 1, 16, 1, 17, 1, 18, 1, 
	19, 1, 20, 1, 21, 1, 22, 1, 
	23, 2, 1, 7, 2, 3, 2, 2, 
	4, 2, 2, 6, 14, 2, 7, 15, 
	3, 3, 2, 0, 3, 3, 2, 13, 
	3, 4, 2, 0, 3, 4, 2, 13, 
	3, 12, 0, 7
};

static const char _fortranfree_cond_offsets[] = {
	0, 0, 1, 2, 2, 3, 4, 4, 
	4, 4, 4, 4, 5, 5, 5, 6, 
	7
};

static const char _fortranfree_cond_lengths[] = {
	0, 1, 1, 0, 1, 1, 0, 0, 
	0, 0, 0, 1, 0, 0, 1, 1, 
	0
};

static const short _fortranfree_cond_keys[] = {
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 13, 13, 13, 13, 0
};

static const char _fortranfree_cond_spaces[] = {
	0, 0, 0, 0, 0, 0, 0, 0
};

static const char _fortranfree_key_offsets[] = {
	0, 0, 11, 22, 23, 34, 45, 46, 
	47, 51, 54, 57, 70, 72, 75, 86, 
	97
};

static const short _fortranfree_trans_keys[] = {
	9, 10, 12, 32, 34, 269, 525, 0, 
	11, 14, 255, 9, 10, 12, 32, 34, 
	269, 525, 0, 11, 14, 255, 10, 9, 
	10, 12, 32, 39, 269, 525, 0, 11, 
	14, 255, 9, 10, 12, 32, 39, 269, 
	525, 0, 11, 14, 255, 10, 10, 32, 
	33, 9, 13, 32, 9, 13, 10, 12, 
	13, 9, 10, 12, 32, 33, 34, 39, 
	269, 525, 0, 8, 14, 255, 9, 32, 
	10, 12, 13, 9, 10, 12, 32, 34, 
	269, 525, 0, 11, 14, 255, 9, 10, 
	12, 32, 39, 269, 525, 0, 11, 14, 
	255, 10, 0
};

static const char _fortranfree_single_lengths[] = {
	0, 7, 7, 1, 7, 7, 1, 1, 
	2, 1, 1, 9, 2, 1, 7, 7, 
	1
};

static const char _fortranfree_range_lengths[] = {
	0, 2, 2, 0, 2, 2, 0, 0, 
	1, 1, 1, 2, 0, 1, 2, 2, 
	0
};

static const char _fortranfree_index_offsets[] = {
	0, 0, 10, 20, 22, 32, 42, 44, 
	46, 50, 53, 56, 68, 71, 74, 84, 
	94
};

static const char _fortranfree_indicies[] = {
	2, 3, 3, 2, 4, 5, 3, 1, 
	1, 0, 7, 8, 8, 7, 9, 10, 
	8, 6, 6, 0, 3, 0, 12, 13, 
	13, 12, 4, 14, 13, 11, 11, 0, 
	16, 17, 17, 16, 18, 19, 17, 15, 
	15, 0, 13, 0, 20, 21, 23, 24, 
	23, 22, 23, 23, 25, 26, 26, 24, 
	28, 20, 20, 28, 29, 30, 31, 32, 
	33, 27, 27, 21, 28, 28, 34, 35, 
	35, 36, 2, 3, 3, 2, 4, 5, 
	3, 1, 1, 37, 12, 13, 13, 12, 
	4, 14, 13, 11, 11, 37, 20, 38, 
	0
};

static const char _fortranfree_trans_targs[] = {
	11, 1, 1, 2, 11, 3, 1, 1, 
	2, 11, 3, 4, 4, 5, 6, 4, 
	4, 5, 11, 6, 11, 0, 8, 9, 
	10, 8, 8, 11, 12, 13, 14, 15, 
	7, 16, 11, 11, 13, 11, 11
};

static const char _fortranfree_trans_actions[] = {
	25, 1, 0, 0, 15, 0, 56, 39, 
	39, 60, 39, 1, 0, 0, 0, 48, 
	36, 36, 52, 36, 42, 0, 27, 7, 
	9, 29, 31, 45, 3, 33, 64, 64, 
	5, 5, 17, 19, 0, 23, 21
};

static const char _fortranfree_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	11, 0, 0, 11, 0, 0, 0, 0, 
	0
};

static const char _fortranfree_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	13, 0, 0, 13, 0, 0, 0, 0, 
	0
};

static const char _fortranfree_eof_trans[] = {
	0, 1, 1, 1, 1, 1, 1, 0, 
	0, 26, 27, 0, 35, 36, 38, 38, 
	39
};

static const int fortranfree_start = 8;
static const int fortranfree_first_final = 8;
static const int fortranfree_error = 0;

static const int fortranfree_en_ffree_line = 11;
static const int fortranfree_en_ffree_entity = 8;


#line 90 "fortranfree.rl"


/* Parses a string buffer with Fortran Freeform code.
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
void parse_fortranfree(char *buffer, int length, int count,
                       void (*callback) (const char *lang, const char *entity,
                                         int s, int e, void *udata),
                       void *userdata
  ) {
  init

  
#line 182 "fortranfree.h"
	{
	cs = fortranfree_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 111 "fortranfree.rl"
  cs = (count) ? fortranfree_en_ffree_line : fortranfree_en_ffree_entity;
  
#line 193 "fortranfree.h"
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
	_acts = _fortranfree_actions + _fortranfree_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 11:
#line 1 "NONE"
	{ts = p;}
	break;
#line 215 "fortranfree.h"
		}
	}

	_widec = (*p);
	_klen = _fortranfree_cond_lengths[cs];
	_keys = _fortranfree_cond_keys + (_fortranfree_cond_offsets[cs]*2);
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
				switch ( _fortranfree_cond_spaces[_fortranfree_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
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

	_keys = _fortranfree_trans_keys + _fortranfree_key_offsets[cs];
	_trans = _fortranfree_index_offsets[cs];

	_klen = _fortranfree_single_lengths[cs];
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

	_klen = _fortranfree_range_lengths[cs];
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
	_trans = _fortranfree_indicies[_trans];
_eof_trans:
	cs = _fortranfree_trans_targs[_trans];

	if ( _fortranfree_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _fortranfree_actions + _fortranfree_trans_actions[_trans];
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
#line 31 "fortranfree.rl"
	{
    switch(entity) {
    case FFREE_SPACE:
      ls
      break;
    case FFREE_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(FORTRANFREE_LANG)
      break;
    case NEWLINE:
      std_newline(FORTRANFREE_LANG)
    }
  }
	break;
	case 3:
#line 51 "fortranfree.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 4:
#line 59 "fortranfree.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 5:
#line 68 "fortranfree.rl"
	{ entity = FFREE_SPACE; }
	break;
	case 6:
#line 71 "fortranfree.rl"
	{ entity = NEWLINE;     }
	break;
	case 7:
#line 72 "fortranfree.rl"
	{ entity = FFREE_ANY;   }
	break;
	case 8:
#line 85 "fortranfree.rl"
	{ entity = FFREE_SPACE;   }
	break;
	case 9:
#line 86 "fortranfree.rl"
	{ entity = FFREE_COMMENT; }
	break;
	case 12:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 13:
#line 70 "fortranfree.rl"
	{te = p+1;}
	break;
	case 14:
#line 31 "fortranfree.rl"
	{te = p+1;{
    switch(entity) {
    case FFREE_SPACE:
      ls
      break;
    case FFREE_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(FORTRANFREE_LANG)
      break;
    case NEWLINE:
      std_newline(FORTRANFREE_LANG)
    }
  }}
	break;
	case 15:
#line 31 "fortranfree.rl"
	{te = p+1;{
    switch(entity) {
    case FFREE_SPACE:
      ls
      break;
    case FFREE_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(FORTRANFREE_LANG)
      break;
    case NEWLINE:
      std_newline(FORTRANFREE_LANG)
    }
  }}
	break;
	case 16:
#line 31 "fortranfree.rl"
	{te = p;p--;{
    switch(entity) {
    case FFREE_SPACE:
      ls
      break;
    case FFREE_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(FORTRANFREE_LANG)
      break;
    case NEWLINE:
      std_newline(FORTRANFREE_LANG)
    }
  }}
	break;
	case 17:
#line 69 "fortranfree.rl"
	{te = p;p--;}
	break;
	case 18:
#line 31 "fortranfree.rl"
	{te = p;p--;{
    switch(entity) {
    case FFREE_SPACE:
      ls
      break;
    case FFREE_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(FORTRANFREE_LANG)
      break;
    case NEWLINE:
      std_newline(FORTRANFREE_LANG)
    }
  }}
	break;
	case 19:
#line 31 "fortranfree.rl"
	{te = p;p--;{
    switch(entity) {
    case FFREE_SPACE:
      ls
      break;
    case FFREE_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(FORTRANFREE_LANG)
      break;
    case NEWLINE:
      std_newline(FORTRANFREE_LANG)
    }
  }}
	break;
	case 20:
#line 31 "fortranfree.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case FFREE_SPACE:
      ls
      break;
    case FFREE_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(FORTRANFREE_LANG)
      break;
    case NEWLINE:
      std_newline(FORTRANFREE_LANG)
    }
  }}
	break;
	case 21:
#line 88 "fortranfree.rl"
	{te = p+1;}
	break;
	case 22:
#line 77 "fortranfree.rl"
	{te = p;p--;{
    callback(FORTRANFREE_LANG, ffree_entities[entity], cint(ts), cint(te),
             userdata);
  }}
	break;
	case 23:
#line 77 "fortranfree.rl"
	{te = p;p--;{
    callback(FORTRANFREE_LANG, ffree_entities[entity], cint(ts), cint(te),
             userdata);
  }}
	break;
#line 512 "fortranfree.h"
		}
	}

_again:
	_acts = _fortranfree_actions + _fortranfree_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 10:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 525 "fortranfree.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _fortranfree_eof_trans[cs] > 0 ) {
		_trans = _fortranfree_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 113 "fortranfree.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(FORTRANFREE_LANG) }
}

#endif
