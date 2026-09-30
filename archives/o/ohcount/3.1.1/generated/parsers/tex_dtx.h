
#line 1 "tex_dtx.rl"
// tex_dtx.rl written by Raphael Pinson,
// based on tex.rl by Mitchell Foral. mitchell<att>caladbolg<dott>net.

/************************* Required for every parser *************************/
#ifndef OHCOUNT_TEX_DTX_PARSER_H
#define OHCOUNT_TEX_DTX_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *TEX_DTX_LANG = LANG_TEX_DTX;

// the languages entities
const char *tex_dtx_entities[] = {
  "space", "comment", "string", "any"
};

// constants associated with the entities
enum {
  TEX_DTX_SPACE = 0, TEX_DTX_COMMENT, TEX_DTX_STRING, TEX_DTX_ANY
};

/*****************************************************************************/


#line 29 "tex_dtx.h"
static const char _tex_dtx_actions[] = {
	0, 1, 0, 1, 1, 1, 2, 1, 
	3, 1, 4, 1, 5, 1, 6, 1, 
	7, 1, 10, 1, 11, 1, 12, 1, 
	13, 1, 14, 1, 15, 1, 16, 1, 
	17, 2, 2, 8, 2, 3, 9
};

static const char _tex_dtx_cond_offsets[] = {
	0, 0, 0, 0, 0, 0, 0, 1, 
	1, 1, 1
};

static const char _tex_dtx_cond_lengths[] = {
	0, 0, 0, 0, 0, 0, 1, 0, 
	0, 0, 0
};

static const short _tex_dtx_cond_keys[] = {
	13, 13, 0
};

static const char _tex_dtx_cond_spaces[] = {
	0, 0
};

static const char _tex_dtx_key_offsets[] = {
	0, 0, 1, 5, 8, 9, 12, 23, 
	25, 26, 29
};

static const short _tex_dtx_trans_keys[] = {
	10, 32, 37, 9, 13, 32, 9, 13, 
	37, 10, 12, 13, 9, 10, 12, 32, 
	37, 269, 525, 0, 8, 14, 255, 9, 
	32, 37, 10, 12, 13, 10, 0
};

static const char _tex_dtx_single_lengths[] = {
	0, 1, 2, 1, 1, 1, 7, 2, 
	1, 1, 1
};

static const char _tex_dtx_range_lengths[] = {
	0, 0, 1, 1, 0, 1, 2, 0, 
	0, 1, 0
};

static const char _tex_dtx_index_offsets[] = {
	0, 0, 2, 6, 9, 11, 14, 24, 
	27, 29, 32
};

static const char _tex_dtx_trans_targs[] = {
	6, 0, 3, 4, 3, 2, 3, 3, 
	2, 5, 2, 2, 2, 5, 7, 6, 
	6, 7, 8, 1, 10, 6, 6, 0, 
	7, 7, 6, 9, 6, 6, 6, 9, 
	6, 6, 2, 2, 2, 6, 6, 6, 
	6, 0
};

static const char _tex_dtx_trans_actions[] = {
	33, 0, 9, 11, 9, 25, 9, 9, 
	27, 11, 31, 29, 29, 11, 3, 33, 
	33, 3, 7, 5, 5, 36, 36, 0, 
	3, 3, 17, 1, 23, 19, 19, 0, 
	33, 21, 27, 31, 29, 17, 23, 19, 
	21, 0
};

static const char _tex_dtx_to_state_actions[] = {
	0, 0, 13, 0, 0, 0, 13, 0, 
	0, 0, 0
};

static const char _tex_dtx_from_state_actions[] = {
	0, 0, 15, 0, 0, 0, 15, 0, 
	0, 0, 0
};

static const char _tex_dtx_eof_trans[] = {
	0, 0, 0, 35, 36, 37, 0, 38, 
	39, 40, 41
};

static const int tex_dtx_start = 2;
static const int tex_dtx_first_final = 2;
static const int tex_dtx_error = 0;

static const int tex_dtx_en_tex_dtx_line = 6;
static const int tex_dtx_en_tex_dtx_entity = 2;


#line 71 "tex_dtx.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with Tex markup.
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
void parse_tex_dtx(char *buffer, int length, int count,
               void (*callback) (const char *lang, const char *entity, int s,
                                 int e, void *udata),
               void *userdata
  ) {
  init

  
#line 148 "tex_dtx.h"
	{
	cs = tex_dtx_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 94 "tex_dtx.rl"
  cs = (count) ? tex_dtx_en_tex_dtx_line : tex_dtx_en_tex_dtx_entity;
  
#line 159 "tex_dtx.h"
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
	_acts = _tex_dtx_actions + _tex_dtx_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 7:
#line 1 "NONE"
	{ts = p;}
	break;
#line 181 "tex_dtx.h"
		}
	}

	_widec = (*p);
	_klen = _tex_dtx_cond_lengths[cs];
	_keys = _tex_dtx_cond_keys + (_tex_dtx_cond_offsets[cs]*2);
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
				switch ( _tex_dtx_cond_spaces[_tex_dtx_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
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

	_keys = _tex_dtx_trans_keys + _tex_dtx_key_offsets[cs];
	_trans = _tex_dtx_index_offsets[cs];

	_klen = _tex_dtx_single_lengths[cs];
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

	_klen = _tex_dtx_range_lengths[cs];
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
	cs = _tex_dtx_trans_targs[_trans];

	if ( _tex_dtx_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _tex_dtx_actions + _tex_dtx_trans_actions[_trans];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 )
	{
		switch ( *_acts++ )
		{
	case 0:
#line 58 "common.rl"
	{
  if (!line_contains_code) {
    whole_line_comment = 1;
    if (!line_start) line_start = ts;
  }
}
	break;
	case 1:
#line 51 "tex_dtx.rl"
	{ entity = TEX_DTX_SPACE; }
	break;
	case 2:
#line 53 "tex_dtx.rl"
	{ entity = NEWLINE;   }
	break;
	case 3:
#line 54 "tex_dtx.rl"
	{ entity = TEX_DTX_ANY;   }
	break;
	case 4:
#line 66 "tex_dtx.rl"
	{ entity = TEX_DTX_SPACE;   }
	break;
	case 5:
#line 67 "tex_dtx.rl"
	{ entity = TEX_DTX_COMMENT; }
	break;
	case 8:
#line 32 "tex_dtx.rl"
	{te = p+1;{
    switch(entity) {
    case TEX_DTX_SPACE:
      ls
      break;
    case TEX_DTX_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(TEX_DTX_LANG)
      break;
    case NEWLINE:
      std_newline(TEX_DTX_LANG)
    }
  }}
	break;
	case 9:
#line 32 "tex_dtx.rl"
	{te = p+1;{
    switch(entity) {
    case TEX_DTX_SPACE:
      ls
      break;
    case TEX_DTX_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(TEX_DTX_LANG)
      break;
    case NEWLINE:
      std_newline(TEX_DTX_LANG)
    }
  }}
	break;
	case 10:
#line 32 "tex_dtx.rl"
	{te = p;p--;{
    switch(entity) {
    case TEX_DTX_SPACE:
      ls
      break;
    case TEX_DTX_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(TEX_DTX_LANG)
      break;
    case NEWLINE:
      std_newline(TEX_DTX_LANG)
    }
  }}
	break;
	case 11:
#line 52 "tex_dtx.rl"
	{te = p;p--;}
	break;
	case 12:
#line 32 "tex_dtx.rl"
	{te = p;p--;{
    switch(entity) {
    case TEX_DTX_SPACE:
      ls
      break;
    case TEX_DTX_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(TEX_DTX_LANG)
      break;
    case NEWLINE:
      std_newline(TEX_DTX_LANG)
    }
  }}
	break;
	case 13:
#line 32 "tex_dtx.rl"
	{te = p;p--;{
    switch(entity) {
    case TEX_DTX_SPACE:
      ls
      break;
    case TEX_DTX_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(TEX_DTX_LANG)
      break;
    case NEWLINE:
      std_newline(TEX_DTX_LANG)
    }
  }}
	break;
	case 14:
#line 69 "tex_dtx.rl"
	{te = p+1;}
	break;
	case 15:
#line 59 "tex_dtx.rl"
	{te = p;p--;{
    callback(TEX_DTX_LANG, tex_dtx_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 16:
#line 59 "tex_dtx.rl"
	{te = p;p--;{
    callback(TEX_DTX_LANG, tex_dtx_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 17:
#line 69 "tex_dtx.rl"
	{te = p;p--;}
	break;
#line 420 "tex_dtx.h"
		}
	}

_again:
	_acts = _tex_dtx_actions + _tex_dtx_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 6:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 433 "tex_dtx.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _tex_dtx_eof_trans[cs] > 0 ) {
		_trans = _tex_dtx_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 96 "tex_dtx.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(TEX_DTX_LANG) }
}

#endif

/*****************************************************************************/
