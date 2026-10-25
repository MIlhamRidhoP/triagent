'use strict';

// A tiny in-memory SQL engine so the benchmark has no native database dependency.
// Supported: SELECT <cols|*> FROM <table> [WHERE <expr>] [ORDER BY <col> [ASC|DESC]]
// where <expr> uses = != < > <= >=, AND, OR, parentheses, string and number literals,
// column names and ? placeholders. A trailing "--" starts a comment, like in real SQL.

const SYMBOLS = ['<=', '>=', '!=', '=', '<', '>', '(', ')', ',', '*', '?', ';'];

function tokenize(sql) {
  const out = [];
  let i = 0;
  while (i < sql.length) {
    const ch = sql[i];
    if (ch === ' ' || ch === '\t' || ch === '\n' || ch === '\r') {
      i += 1;
      continue;
    }
    if (ch === '-' && sql[i + 1] === '-') {
      break;
    }
    if (ch === "'") {
      let text = '';
      let j = i + 1;
      let closed = false;
      while (j < sql.length) {
        if (sql[j] === "'") {
          if (sql[j + 1] === "'") {
            text += "'";
            j += 2;
            continue;
          }
          closed = true;
          break;
        }
        text += sql[j];
        j += 1;
      }
      if (!closed) {
        throw new Error('SQL syntax error: unterminated string');
      }
      out.push({ kind: 'str', value: text });
      i = j + 1;
      continue;
    }
    const num = /^[0-9]+(\.[0-9]+)?/.exec(sql.slice(i));
    if (num) {
      out.push({ kind: 'num', value: Number(num[0]) });
      i += num[0].length;
      continue;
    }
    const word = /^[A-Za-z_][A-Za-z_0-9]*/.exec(sql.slice(i));
    if (word) {
      out.push({ kind: 'word', value: word[0] });
      i += word[0].length;
      continue;
    }
    const sym = SYMBOLS.find(function (candidate) {
      return sql.startsWith(candidate, i);
    });
    if (!sym) {
      throw new Error('SQL syntax error near ' + ch);
    }
    out.push({ kind: 'sym', value: sym });
    i += sym.length;
  }
  return out;
}

class Parser {
  constructor(tokens, params) {
    this.tokens = tokens;
    this.pos = 0;
    this.params = params;
    this.nextParam = 0;
  }

  peek() {
    return this.tokens[this.pos];
  }

  isWord(text) {
    const tok = this.peek();
    return Boolean(tok) && tok.kind === 'word' && tok.value.toUpperCase() === text;
  }

  isSym(text) {
    const tok = this.peek();
    return Boolean(tok) && tok.kind === 'sym' && tok.value === text;
  }

  expectWord(text) {
    if (!this.isWord(text)) {
      throw new Error('SQL syntax error: expected ' + text);
    }
    this.pos += 1;
  }

  take() {
    const tok = this.tokens[this.pos];
    if (!tok) {
      throw new Error('SQL syntax error: unexpected end');
    }
    this.pos += 1;
    return tok;
  }

  parseOr() {
    let left = this.parseAnd();
    while (this.isWord('OR')) {
      this.pos += 1;
      const right = this.parseAnd();
      const prev = left;
      left = function (row) {
        return prev(row) || right(row);
      };
    }
    return left;
  }

  parseAnd() {
    let left = this.parseCompare();
    while (this.isWord('AND')) {
      this.pos += 1;
      const right = this.parseCompare();
      const prev = left;
      left = function (row) {
        return prev(row) && right(row);
      };
    }
    return left;
  }

  parseValue() {
    const tok = this.take();
    if (tok.kind === 'str' || tok.kind === 'num') {
      return function () {
        return tok.value;
      };
    }
    if (tok.kind === 'sym' && tok.value === '?') {
      if (this.nextParam >= this.params.length) {
        throw new Error('SQL error: missing parameter');
      }
      const bound = this.params[this.nextParam];
      this.nextParam += 1;
      return function () {
        return bound;
      };
    }
    if (tok.kind === 'word') {
      return function (row) {
        return row[tok.value];
      };
    }
    throw new Error('SQL syntax error near ' + tok.value);
  }

  parseCompare() {
    if (this.isSym('(')) {
      this.pos += 1;
      const inner = this.parseOr();
      if (!this.isSym(')')) {
        throw new Error('SQL syntax error: expected )');
      }
      this.pos += 1;
      return inner;
    }
    const left = this.parseValue();
    const op = this.take();
    if (op.kind !== 'sym' || ['=', '!=', '<', '>', '<=', '>='].indexOf(op.value) < 0) {
      throw new Error('SQL syntax error: expected comparison');
    }
    const right = this.parseValue();
    return function (row) {
      const a = left(row);
      const b = right(row);
      switch (op.value) {
        case '=':
          return a === b;
        case '!=':
          return a !== b;
        case '<':
          return a < b;
        case '>':
          return a > b;
        case '<=':
          return a <= b;
        default:
          return a >= b;
      }
    };
  }
}

class MiniDb {
  constructor() {
    this.tables = new Map();
  }

  createTable(name, rows) {
    this.tables.set(name, rows);
  }

  query(sql, params) {
    const parser = new Parser(tokenize(sql), params || []);
    parser.expectWord('SELECT');
    const columns = [];
    if (parser.isSym('*')) {
      parser.pos += 1;
      columns.push('*');
    } else {
      columns.push(parser.take().value);
      while (parser.isSym(',')) {
        parser.pos += 1;
        columns.push(parser.take().value);
      }
    }
    parser.expectWord('FROM');
    const table = parser.take().value;
    if (!this.tables.has(table)) {
      throw new Error('SQL error: no such table ' + table);
    }
    let where = function () {
      return true;
    };
    if (parser.isWord('WHERE')) {
      parser.pos += 1;
      where = parser.parseOr();
    }
    let orderBy = null;
    let descending = false;
    if (parser.isWord('ORDER')) {
      parser.pos += 1;
      parser.expectWord('BY');
      orderBy = parser.take().value;
      if (parser.isWord('DESC')) {
        descending = true;
        parser.pos += 1;
      } else if (parser.isWord('ASC')) {
        parser.pos += 1;
      }
    }
    if (parser.isSym(';')) {
      parser.pos += 1;
    }
    if (parser.peek()) {
      throw new Error('SQL syntax error: unexpected ' + parser.peek().value);
    }
    let rows = this.tables.get(table).filter(where);
    if (orderBy) {
      const key = orderBy;
      if (rows.length > 0 && !(key in rows[0])) {
        throw new Error('SQL error: no such column ' + key);
      }
      rows = rows.slice().sort(function (a, b) {
        if (a[key] === b[key]) {
          return 0;
        }
        return (a[key] < b[key] ? -1 : 1) * (descending ? -1 : 1);
      });
    }
    return rows.map(function (row) {
      if (columns[0] === '*') {
        return Object.assign({}, row);
      }
      const picked = {};
      columns.forEach(function (col) {
        if (!(col in row)) {
          throw new Error('SQL error: no such column ' + col);
        }
        picked[col] = row[col];
      });
      return picked;
    });
  }
}

module.exports = { Database: MiniDb };
