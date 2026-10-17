
#line 1 "rebol.rl"
// rebol.rl written by Andreas Bolka.

/************************* Required for every parser *************************/
#ifndef OHCOUNT_REBOL_PARSER_H
#define OHCOUNT_REBOL_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *REBOL_LANG = LANG_REBOL;

// the languages entities
const char *rebol_entities[] = {
  "space", "comment", "string", "any"
};

// constants associated with the entities
enum {
  REBOL_SPACE = 0, REBOL_COMMENT, REBOL_STRING, REBOL_ANY
};

/*****************************************************************************/


#line 28 "rebol.h"
static const char _rebol_actions[] = {
	0, 1, 0, 1, 6, 1, 7, 1, 
	9, 1, 10, 1, 11, 1, 13, 1, 
	14, 1, 18, 1, 21, 1, 22, 1, 
	23, 1, 24, 1, 25, 1, 30, 1, 
	31, 1, 32, 1, 33, 2, 0, 18, 
	2, 1, 8, 2, 2, 0, 2, 2, 
	11, 2, 3, 0, 2, 3, 11, 2, 
	7, 19, 2, 8, 20, 2, 10, 12, 
	2, 11, 28, 2, 12, 29, 2, 15, 
	16, 3, 2, 0, 18, 3, 2, 11, 
	28, 3, 3, 0, 18, 3, 3, 11, 
	28, 3, 5, 4, 0, 3, 15, 0, 
	16, 3, 15, 11, 26, 4, 5, 4, 
	0, 18, 4, 15, 0, 8, 17, 4, 
	15, 2, 0, 16, 4, 15, 2, 11, 
	26, 4, 15, 3, 0, 16, 4, 15, 
	3, 11, 26, 4, 15, 11, 12, 27, 
	5, 15, 5, 4, 0, 16
};

static const char _rebol_cond_offsets[] = {
	0, 0, 0, 0, 1, 2, 3, 3, 
	3, 5, 7, 9, 11, 11, 11, 11, 
	11, 11, 12, 13, 14, 14, 14, 14, 
	16, 18
};

static const char _rebol_cond_lengths[] = {
	0, 0, 0, 1, 1, 1, 0, 0, 
	2, 2, 2, 2, 0, 0, 0, 0, 
	0, 1, 1, 1, 0, 0, 0, 2, 
	2, 0
};

static const short _rebol_cond_keys[] = {
	125, 125, 125, 125, 125, 125, 13, 13, 
	125, 125, 13, 13, 125, 125, 13, 13, 
	125, 125, 13, 13, 125, 125, 125, 125, 
	125, 125, 13, 13, 13, 13, 125, 125, 
	13, 13, 125, 125, 0
};

static const char _rebol_cond_spaces[] = {
	1, 1, 1, 0, 1, 0, 1, 0, 
	1, 0, 1, 1, 1, 0, 0, 1, 
	0, 1, 0
};

static const char _rebol_key_offsets[] = {
	0, 0, 5, 10, 18, 26, 34, 39, 
	44, 58, 72, 86, 100, 101, 107, 110, 
	115, 118, 126, 134, 147, 149, 154, 157, 
	171, 185
};

static const short _rebol_trans_keys[] = {
	10, 34, 94, 12, 13, 10, 34, 94, 
	12, 13, 94, 123, 893, 1149, 0, 124, 
	126, 255, 94, 123, 893, 1149, 0, 124, 
	126, 255, 94, 123, 893, 1149, 0, 124, 
	126, 255, 10, 34, 94, 12, 13, 10, 
	34, 94, 12, 13, 10, 12, 94, 123, 
	269, 525, 893, 1149, 0, 11, 14, 124, 
	126, 255, 10, 12, 94, 123, 269, 525, 
	893, 1149, 0, 11, 14, 124, 126, 255, 
	10, 12, 94, 123, 269, 525, 893, 1149, 
	0, 11, 14, 124, 126, 255, 10, 12, 
	94, 123, 269, 525, 893, 1149, 0, 11, 
	14, 124, 126, 255, 10, 32, 34, 59, 
	123, 9, 13, 32, 9, 13, 10, 34, 
	94, 12, 13, 10, 12, 13, 94, 123, 
	893, 1149, 0, 124, 126, 255, 94, 123, 
	893, 1149, 0, 124, 126, 255, 9, 10, 
	12, 32, 34, 59, 123, 269, 525, 0, 
	8, 14, 255, 9, 32, 10, 34, 94, 
	12, 13, 10, 12, 13, 10, 12, 94, 
	123, 269, 525, 893, 1149, 0, 11, 14, 
	124, 126, 255, 10, 12, 94, 123, 269, 
	525, 893, 1149, 0, 11, 14, 124, 126, 
	255, 10, 0
};

static const char _rebol_single_lengths[] = {
	0, 3, 3, 4, 4, 4, 3, 3, 
	8, 8, 8, 8, 1, 4, 1, 3, 
	1, 4, 4, 9, 2, 3, 1, 8, 
	8, 1
};

static const char _rebol_range_lengths[] = {
	0, 1, 1, 2, 2, 2, 1, 1, 
	3, 3, 3, 3, 0, 1, 1, 1, 
	1, 2, 2, 2, 0, 1, 1, 3, 
	3, 0
};

static const char _rebol_index_offsets[] = {
	0, 0, 5, 10, 17, 24, 31, 36, 
	41, 53, 65, 77, 89, 91, 97, 100, 
	105, 108, 115, 122, 134, 137, 142, 145, 
	157, 169
};

static const char _rebol_indicies[] = {
	2, 2, 3, 2, 1, 2, 4, 3, 
	2, 1, 6, 7, 2, 8, 5, 5, 
	0, 6, 7, 9, 8, 5, 5, 0, 
	11, 12, 13, 14, 10, 10, 0, 17, 
	17, 18, 17, 16, 17, 19, 18, 17, 
	16, 21, 21, 22, 23, 20, 21, 24, 
	25, 20, 20, 20, 15, 27, 27, 28, 
	29, 26, 27, 30, 31, 26, 26, 26, 
	15, 21, 21, 22, 23, 20, 21, 32, 
	25, 20, 20, 20, 15, 34, 34, 35, 
	36, 33, 34, 37, 38, 33, 33, 33, 
	15, 39, 40, 42, 43, 44, 45, 42, 
	41, 42, 42, 46, 2, 2, 3, 2, 
	1, 47, 47, 48, 6, 7, 2, 8, 
	5, 5, 0, 51, 52, 53, 54, 50, 
	50, 49, 56, 39, 39, 56, 57, 58, 
	59, 60, 61, 55, 55, 40, 56, 56, 
	62, 17, 17, 18, 17, 16, 63, 63, 
	64, 21, 21, 22, 23, 20, 21, 24, 
	25, 20, 20, 20, 15, 67, 67, 68, 
	69, 66, 67, 70, 71, 66, 66, 66, 
	65, 39, 72, 0
};

static const char _rebol_trans_targs[] = {
	13, 1, 13, 2, 15, 3, 4, 5, 
	18, 17, 3, 4, 5, 13, 18, 19, 
	6, 19, 7, 21, 8, 9, 10, 11, 
	19, 24, 8, 9, 10, 11, 19, 24, 
	23, 8, 9, 10, 11, 19, 24, 19, 
	0, 13, 14, 15, 16, 17, 13, 13, 
	16, 13, 3, 4, 5, 13, 18, 19, 
	20, 21, 22, 23, 12, 25, 19, 19, 
	22, 19, 8, 9, 10, 11, 19, 24, 
	19
};

static const char _rebol_trans_actions[] = {
	35, 11, 64, 11, 97, 11, 11, 11, 
	97, 97, 46, 46, 46, 77, 116, 27, 
	0, 17, 0, 70, 1, 1, 1, 1, 
	37, 93, 89, 89, 89, 89, 101, 136, 
	93, 43, 43, 43, 43, 73, 111, 55, 
	0, 67, 7, 131, 61, 131, 29, 31, 
	9, 33, 52, 52, 52, 85, 126, 58, 
	3, 106, 40, 106, 5, 5, 19, 21, 
	0, 23, 49, 49, 49, 49, 81, 121, 
	25
};

static const char _rebol_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 13, 0, 0, 
	0, 0, 0, 13, 0, 0, 0, 0, 
	0, 0
};

static const char _rebol_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 15, 0, 0, 
	0, 0, 0, 15, 0, 0, 0, 0, 
	0, 0
};

static const char _rebol_eof_trans[] = {
	0, 1, 1, 1, 1, 1, 16, 16, 
	16, 16, 16, 16, 0, 0, 47, 1, 
	48, 1, 50, 0, 63, 16, 64, 16, 
	66, 73
};

static const int rebol_start = 13;
static const int rebol_first_final = 13;
static const int rebol_error = 0;

static const int rebol_en_rebol_line = 19;
static const int rebol_en_rebol_entity = 13;


#line 92 "rebol.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with REBOL code.
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
void parse_rebol(char *buffer, int length, int count,
                 void (*callback) (const char *lang, const char *entity, int s,
                                   int e, void *udata),
                 void *userdata
  ) {
  // For {..} multi-line strings which require proper balancing of {}'s.
  int rebol_string_level = 0;
  init

  
#line 239 "rebol.h"
	{
	cs = rebol_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 117 "rebol.rl"
  cs = (count) ? rebol_en_rebol_line : rebol_en_rebol_entity;
  
#line 250 "rebol.h"
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
	_acts = _rebol_actions + _rebol_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 14:
#line 1 "NONE"
	{ts = p;}
	break;
#line 272 "rebol.h"
		}
	}

	_widec = (*p);
	_klen = _rebol_cond_lengths[cs];
	_keys = _rebol_cond_keys + (_rebol_cond_offsets[cs]*2);
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
				switch ( _rebol_cond_spaces[_rebol_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
	case 0: {
		_widec = (short)(256 + ((*p) - 0));
		if ( 
#line 9 "common.rl"
 p+1 < pe && *(p+1) != '\n'  ) _widec += 256;
		break;
	}
	case 1: {
		_widec = (short)(768 + ((*p) - 0));
		if ( 
#line 31 "rebol.rl"
 rebol_string_level > 0  ) _widec += 256;
		break;
	}
				}
				break;
			}
		}
	}

	_keys = _rebol_trans_keys + _rebol_key_offsets[cs];
	_trans = _rebol_index_offsets[cs];

	_klen = _rebol_single_lengths[cs];
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

	_klen = _rebol_range_lengths[cs];
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
	_trans = _rebol_indicies[_trans];
_eof_trans:
	cs = _rebol_trans_targs[_trans];

	if ( _rebol_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _rebol_actions + _rebol_trans_actions[_trans];
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
#line 29 "rebol.rl"
	{ ++rebol_string_level; }
	break;
	case 3:
#line 30 "rebol.rl"
	{ --rebol_string_level; }
	break;
	case 4:
#line 38 "rebol.rl"
	{
    switch(entity) {
    case REBOL_SPACE:
      ls
      break;
    case REBOL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(REBOL_LANG)
      break;
    case NEWLINE:
      std_newline(REBOL_LANG)
    }
  }
	break;
	case 5:
#line 59 "rebol.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 6:
#line 65 "rebol.rl"
	{ entity = REBOL_SPACE; }
	break;
	case 7:
#line 68 "rebol.rl"
	{ entity = NEWLINE; }
	break;
	case 8:
#line 69 "rebol.rl"
	{ entity = REBOL_ANY; }
	break;
	case 9:
#line 86 "rebol.rl"
	{ entity = REBOL_SPACE; }
	break;
	case 10:
#line 87 "rebol.rl"
	{ entity = REBOL_COMMENT; }
	break;
	case 11:
#line 88 "rebol.rl"
	{ entity = REBOL_STRING; }
	break;
	case 12:
#line 89 "rebol.rl"
	{ entity = REBOL_ANY; }
	break;
	case 15:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 16:
#line 67 "rebol.rl"
	{act = 3;}
	break;
	case 17:
#line 38 "rebol.rl"
	{act = 5;}
	break;
	case 18:
#line 67 "rebol.rl"
	{te = p+1;}
	break;
	case 19:
#line 38 "rebol.rl"
	{te = p+1;{
    switch(entity) {
    case REBOL_SPACE:
      ls
      break;
    case REBOL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(REBOL_LANG)
      break;
    case NEWLINE:
      std_newline(REBOL_LANG)
    }
  }}
	break;
	case 20:
#line 38 "rebol.rl"
	{te = p+1;{
    switch(entity) {
    case REBOL_SPACE:
      ls
      break;
    case REBOL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(REBOL_LANG)
      break;
    case NEWLINE:
      std_newline(REBOL_LANG)
    }
  }}
	break;
	case 21:
#line 38 "rebol.rl"
	{te = p;p--;{
    switch(entity) {
    case REBOL_SPACE:
      ls
      break;
    case REBOL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(REBOL_LANG)
      break;
    case NEWLINE:
      std_newline(REBOL_LANG)
    }
  }}
	break;
	case 22:
#line 66 "rebol.rl"
	{te = p;p--;}
	break;
	case 23:
#line 67 "rebol.rl"
	{te = p;p--;}
	break;
	case 24:
#line 38 "rebol.rl"
	{te = p;p--;{
    switch(entity) {
    case REBOL_SPACE:
      ls
      break;
    case REBOL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(REBOL_LANG)
      break;
    case NEWLINE:
      std_newline(REBOL_LANG)
    }
  }}
	break;
	case 25:
#line 1 "NONE"
	{	switch( act ) {
	case 5:
	{{p = ((te))-1;}
    switch(entity) {
    case REBOL_SPACE:
      ls
      break;
    case REBOL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(REBOL_LANG)
      break;
    case NEWLINE:
      std_newline(REBOL_LANG)
    }
  }
	break;
	default:
	{{p = ((te))-1;}}
	break;
	}
	}
	break;
	case 26:
#line 74 "rebol.rl"
	{act = 8;}
	break;
	case 27:
#line 74 "rebol.rl"
	{act = 9;}
	break;
	case 28:
#line 74 "rebol.rl"
	{te = p+1;{
    callback(REBOL_LANG, rebol_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 29:
#line 74 "rebol.rl"
	{te = p+1;{
    callback(REBOL_LANG, rebol_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 30:
#line 74 "rebol.rl"
	{te = p;p--;{
    callback(REBOL_LANG, rebol_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 31:
#line 74 "rebol.rl"
	{te = p;p--;{
    callback(REBOL_LANG, rebol_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 32:
#line 74 "rebol.rl"
	{te = p;p--;{
    callback(REBOL_LANG, rebol_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 33:
#line 1 "NONE"
	{	switch( act ) {
	case 8:
	{{p = ((te))-1;}
    callback(REBOL_LANG, rebol_entities[entity], cint(ts), cint(te), userdata);
  }
	break;
	case 9:
	{{p = ((te))-1;}
    callback(REBOL_LANG, rebol_entities[entity], cint(ts), cint(te), userdata);
  }
	break;
	}
	}
	break;
#line 626 "rebol.h"
		}
	}

_again:
	_acts = _rebol_actions + _rebol_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 13:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 639 "rebol.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _rebol_eof_trans[cs] > 0 ) {
		_trans = _rebol_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 119 "rebol.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(REBOL_LANG) }
}

#endif

/*****************************************************************************/

// vim: set ts=2 syn=c:
