
#line 1 "sql.rl"
// sql.rl written by Mitchell Foral. mitchell<att>caladbolg<dott>net.

/************************* Required for every parser *************************/
#ifndef OHCOUNT_SQL_PARSER_H
#define OHCOUNT_SQL_PARSER_H

#include "../parser_macros.h"

// the name of the language
const char *SQL_LANG = LANG_SQL;

// the languages entities
const char *sql_entities[] = {
  "space", "comment", "string", "any",
};

// constants associated with the entities
enum {
  SQL_SPACE = 0, SQL_COMMENT, SQL_STRING, SQL_ANY
};

/*****************************************************************************/


#line 28 "sql.h"
static const char _sql_actions[] = {
	0, 1, 1, 1, 5, 1, 6, 1, 
	7, 1, 8, 1, 9, 1, 10, 1, 
	11, 1, 13, 1, 14, 1, 17, 1, 
	18, 1, 19, 1, 20, 1, 21, 1, 
	23, 1, 24, 1, 25, 1, 26, 1, 
	27, 2, 1, 7, 2, 3, 2, 2, 
	4, 2, 2, 6, 15, 2, 7, 16, 
	2, 9, 22, 2, 12, 7, 2, 12, 
	9, 3, 3, 2, 1, 3, 4, 2, 
	1, 3, 4, 2, 13, 3, 12, 0, 
	7, 3, 12, 1, 7
};

static const char _sql_cond_offsets[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 1, 2, 3, 3, 4, 5, 5, 
	5, 5, 5, 5, 5, 5, 5, 6, 
	6, 6, 6, 6, 6, 6, 7
};

static const char _sql_cond_lengths[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	1, 1, 1, 0, 1, 1, 0, 0, 
	0, 0, 0, 0, 0, 0, 1, 0, 
	0, 0, 0, 0, 0, 1, 0
};

static const short _sql_cond_keys[] = {
	13, 13, 13, 13, 13, 13, 13, 13, 
	13, 13, 13, 13, 13, 13, 0
};

static const char _sql_cond_spaces[] = {
	0, 0, 0, 0, 0, 0, 0, 0
};

static const char _sql_key_offsets[] = {
	0, 0, 1, 3, 4, 9, 12, 17, 
	20, 31, 42, 54, 55, 66, 77, 78, 
	79, 86, 89, 92, 93, 95, 96, 112, 
	114, 119, 122, 127, 128, 130, 141
};

static const short _sql_trans_keys[] = {
	42, 42, 47, 125, 10, 34, 92, 12, 
	13, 10, 12, 13, 10, 39, 92, 12, 
	13, 10, 12, 13, 9, 10, 12, 32, 
	42, 269, 525, 0, 11, 14, 255, 9, 
	10, 12, 32, 42, 269, 525, 0, 11, 
	14, 255, 9, 10, 12, 32, 42, 47, 
	269, 525, 0, 11, 14, 255, 10, 9, 
	10, 12, 32, 125, 269, 525, 0, 11, 
	14, 255, 9, 10, 12, 32, 125, 269, 
	525, 0, 11, 14, 255, 10, 10, 32, 
	35, 45, 47, 123, 9, 13, 32, 9, 
	13, 10, 12, 13, 45, 42, 47, 125, 
	9, 10, 12, 32, 34, 35, 39, 45, 
	47, 123, 269, 525, 0, 8, 14, 255, 
	9, 32, 10, 34, 92, 12, 13, 10, 
	12, 13, 10, 39, 92, 12, 13, 45, 
	42, 47, 9, 10, 12, 32, 125, 269, 
	525, 0, 11, 14, 255, 10, 0
};

static const char _sql_single_lengths[] = {
	0, 1, 2, 1, 3, 1, 3, 1, 
	7, 7, 8, 1, 7, 7, 1, 1, 
	5, 1, 1, 1, 2, 1, 12, 2, 
	3, 1, 3, 1, 2, 7, 1
};

static const char _sql_range_lengths[] = {
	0, 0, 0, 0, 1, 1, 1, 1, 
	2, 2, 2, 0, 2, 2, 0, 0, 
	1, 1, 1, 0, 0, 0, 2, 0, 
	1, 1, 1, 0, 0, 2, 0
};

static const char _sql_index_offsets[] = {
	0, 0, 2, 5, 7, 12, 15, 20, 
	23, 33, 43, 54, 56, 66, 76, 78, 
	80, 87, 90, 93, 95, 98, 100, 115, 
	118, 123, 126, 131, 133, 136, 146
};

static const char _sql_indicies[] = {
	2, 1, 2, 3, 1, 3, 4, 5, 
	7, 8, 5, 6, 5, 5, 6, 5, 
	7, 10, 5, 9, 5, 5, 9, 12, 
	13, 13, 12, 14, 15, 13, 11, 11, 
	5, 17, 18, 18, 17, 19, 20, 18, 
	16, 16, 5, 12, 13, 13, 12, 14, 
	21, 15, 13, 11, 11, 5, 13, 5, 
	23, 24, 24, 23, 21, 25, 24, 22, 
	22, 5, 27, 28, 28, 27, 29, 30, 
	28, 26, 26, 5, 24, 5, 31, 32, 
	34, 35, 36, 37, 38, 34, 33, 34, 
	34, 39, 40, 40, 35, 35, 41, 1, 
	35, 41, 3, 4, 43, 31, 31, 43, 
	44, 45, 46, 47, 48, 49, 50, 51, 
	42, 42, 32, 43, 43, 52, 53, 7, 
	8, 53, 6, 54, 54, 55, 53, 7, 
	10, 53, 9, 56, 53, 11, 56, 53, 
	23, 24, 24, 23, 21, 25, 24, 22, 
	22, 53, 31, 57, 0
};

static const char _sql_trans_targs[] = {
	16, 1, 2, 16, 3, 22, 4, 22, 
	5, 6, 7, 8, 8, 9, 10, 11, 
	8, 8, 9, 10, 11, 22, 12, 12, 
	13, 14, 12, 12, 13, 22, 14, 22, 
	0, 16, 17, 18, 19, 20, 21, 16, 
	16, 16, 22, 23, 24, 25, 26, 27, 
	28, 29, 15, 30, 22, 22, 22, 25, 
	25, 22
};

static const char _sql_trans_actions[] = {
	39, 11, 11, 56, 11, 29, 0, 19, 
	0, 0, 0, 1, 0, 0, 1, 0, 
	65, 44, 44, 65, 44, 17, 1, 0, 
	0, 0, 69, 47, 47, 73, 47, 50, 
	0, 31, 9, 11, 11, 62, 62, 33, 
	35, 37, 53, 3, 77, 41, 77, 7, 
	59, 81, 5, 5, 21, 27, 23, 0, 
	1, 25
};

static const char _sql_to_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	13, 0, 0, 0, 0, 0, 13, 0, 
	0, 0, 0, 0, 0, 0, 0
};

static const char _sql_from_state_actions[] = {
	0, 0, 0, 0, 0, 0, 0, 0, 
	0, 0, 0, 0, 0, 0, 0, 0, 
	15, 0, 0, 0, 0, 0, 15, 0, 
	0, 0, 0, 0, 0, 0, 0
};

static const char _sql_eof_trans[] = {
	0, 1, 1, 1, 6, 6, 6, 6, 
	6, 6, 6, 6, 6, 6, 6, 0, 
	0, 40, 41, 42, 42, 42, 0, 53, 
	54, 55, 54, 54, 54, 54, 58
};

static const int sql_start = 16;
static const int sql_first_final = 16;
static const int sql_error = 0;

static const int sql_en_sql_line = 22;
static const int sql_en_sql_entity = 16;


#line 96 "sql.rl"


/************************* Required for every parser *************************/

/* Parses a string buffer with SQL code.
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
void parse_sql(char *buffer, int length, int count,
               void (*callback) (const char *lang, const char *entity, int s,
                                 int e, void *udata),
               void *userdata
  ) {
  init

  
#line 212 "sql.h"
	{
	cs = sql_start;
	ts = 0;
	te = 0;
	act = 0;
	}

#line 119 "sql.rl"
  cs = (count) ? sql_en_sql_line : sql_en_sql_entity;
  
#line 223 "sql.h"
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
	_acts = _sql_actions + _sql_from_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 11:
#line 1 "NONE"
	{ts = p;}
	break;
#line 245 "sql.h"
		}
	}

	_widec = (*p);
	_klen = _sql_cond_lengths[cs];
	_keys = _sql_cond_keys + (_sql_cond_offsets[cs]*2);
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
				switch ( _sql_cond_spaces[_sql_cond_offsets[cs] + ((_mid - _keys)>>1)] ) {
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

	_keys = _sql_trans_keys + _sql_key_offsets[cs];
	_trans = _sql_index_offsets[cs];

	_klen = _sql_single_lengths[cs];
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

	_klen = _sql_range_lengths[cs];
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
	_trans = _sql_indicies[_trans];
_eof_trans:
	cs = _sql_trans_targs[_trans];

	if ( _sql_trans_actions[_trans] == 0 )
		goto _again;

	_acts = _sql_actions + _sql_trans_actions[_trans];
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
#line 31 "sql.rl"
	{
    switch(entity) {
    case SQL_SPACE:
      ls
      break;
    case SQL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(SQL_LANG)
      break;
    case NEWLINE:
      std_newline(SQL_LANG)
    }
  }
	break;
	case 3:
#line 50 "sql.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 4:
#line 58 "sql.rl"
	{ entity = INTERNAL_NL; }
	break;
	case 5:
#line 71 "sql.rl"
	{ entity = SQL_SPACE; }
	break;
	case 6:
#line 74 "sql.rl"
	{ entity = NEWLINE;   }
	break;
	case 7:
#line 75 "sql.rl"
	{ entity = SQL_ANY;   }
	break;
	case 8:
#line 91 "sql.rl"
	{ entity = SQL_SPACE;   }
	break;
	case 9:
#line 92 "sql.rl"
	{ entity = SQL_COMMENT; }
	break;
	case 12:
#line 1 "NONE"
	{te = p+1;}
	break;
	case 13:
#line 72 "sql.rl"
	{te = p+1;}
	break;
	case 14:
#line 73 "sql.rl"
	{te = p+1;}
	break;
	case 15:
#line 31 "sql.rl"
	{te = p+1;{
    switch(entity) {
    case SQL_SPACE:
      ls
      break;
    case SQL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(SQL_LANG)
      break;
    case NEWLINE:
      std_newline(SQL_LANG)
    }
  }}
	break;
	case 16:
#line 31 "sql.rl"
	{te = p+1;{
    switch(entity) {
    case SQL_SPACE:
      ls
      break;
    case SQL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(SQL_LANG)
      break;
    case NEWLINE:
      std_newline(SQL_LANG)
    }
  }}
	break;
	case 17:
#line 31 "sql.rl"
	{te = p;p--;{
    switch(entity) {
    case SQL_SPACE:
      ls
      break;
    case SQL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(SQL_LANG)
      break;
    case NEWLINE:
      std_newline(SQL_LANG)
    }
  }}
	break;
	case 18:
#line 72 "sql.rl"
	{te = p;p--;}
	break;
	case 19:
#line 31 "sql.rl"
	{te = p;p--;{
    switch(entity) {
    case SQL_SPACE:
      ls
      break;
    case SQL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(SQL_LANG)
      break;
    case NEWLINE:
      std_newline(SQL_LANG)
    }
  }}
	break;
	case 20:
#line 31 "sql.rl"
	{te = p;p--;{
    switch(entity) {
    case SQL_SPACE:
      ls
      break;
    case SQL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(SQL_LANG)
      break;
    case NEWLINE:
      std_newline(SQL_LANG)
    }
  }}
	break;
	case 21:
#line 31 "sql.rl"
	{{p = ((te))-1;}{
    switch(entity) {
    case SQL_SPACE:
      ls
      break;
    case SQL_ANY:
      code
      break;
    case INTERNAL_NL:
      std_internal_newline(SQL_LANG)
      break;
    case NEWLINE:
      std_newline(SQL_LANG)
    }
  }}
	break;
	case 22:
#line 80 "sql.rl"
	{te = p+1;{
    callback(SQL_LANG, sql_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 23:
#line 94 "sql.rl"
	{te = p+1;}
	break;
	case 24:
#line 80 "sql.rl"
	{te = p;p--;{
    callback(SQL_LANG, sql_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 25:
#line 80 "sql.rl"
	{te = p;p--;{
    callback(SQL_LANG, sql_entities[entity], cint(ts), cint(te), userdata);
  }}
	break;
	case 26:
#line 94 "sql.rl"
	{te = p;p--;}
	break;
	case 27:
#line 94 "sql.rl"
	{{p = ((te))-1;}}
	break;
#line 558 "sql.h"
		}
	}

_again:
	_acts = _sql_actions + _sql_to_state_actions[cs];
	_nacts = (unsigned int) *_acts++;
	while ( _nacts-- > 0 ) {
		switch ( *_acts++ ) {
	case 10:
#line 1 "NONE"
	{ts = 0;}
	break;
#line 571 "sql.h"
		}
	}

	if ( cs == 0 )
		goto _out;
	if ( ++p != pe )
		goto _resume;
	_test_eof: {}
	if ( p == eof )
	{
	if ( _sql_eof_trans[cs] > 0 ) {
		_trans = _sql_eof_trans[cs] - 1;
		goto _eof_trans;
	}
	}

	_out: {}
	}

#line 121 "sql.rl"

  // if no newline at EOF; callback contents of last line
  if (count) { process_last_line(SQL_LANG) }
}

#endif

/*****************************************************************************/
