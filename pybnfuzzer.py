from typing import NoReturn

import sys
import string
import enum
import dataclasses
import random
import re
import argparse

from rstr.xeger import Xeger


BNF_SYNTAX = """\
This a brief description of the BNF syntax supported by pybnfuzzer. It is
mostly compatable with the one described on the Wikipedia article:
https://en.wikipedia.org/wiki/Backus–Naur_form

Rules are defined with the following notation:

    <symbol> ::= [rule] ;

Rule names must be enclosed in angle brackets ("<" and ">") and can contain
only lower- and uppercase letters, digits, and "-" and "_" characters.
The semicolon at the end is requred. All whitespace is for formatting and
styling purposes only and is ignored by the parser.

pybnfuzzer additionally requires the grammar to have a special <start> rule,
which is used as an entry point for string generation.

Terminal rules are expressed between double or single quotes:

    <this-is-a-terminal>      ::= "#" ;
    <this-is-also-a-terminal> ::= '@' ;

Everything from "#" until the end of a line is treated as a comment:

    # this is the start of my grammar
    <start> ::= "grammar" ;  # a literal grammar!

Choices between several variants are denoted by a vertical bar "|":

    <digits> ::= "0" | "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9" ;

For convenience, regular expressions can be used to describe terminal rules.
The expression must be enclosed between slash symbols "/":

    <digits>        ::= /[0-9]/ ;
    <variable-name> ::= /[A-Za-z0-9_]+/ ;

Literal "/" within regular expressions must be escaped with a "'". A literal
"'" must be escaped as well:

    <five-slashes>            ::= /'/{5}/ ;
    <digits-in-single-quotes> ::= /''\\d+''/ ;

Not all Python regexp features are supported; for more information, please
refer to the rstr module documentation:
https://github.com/leapfrogonline/rstr

Some extra rule modifiers are also supported. The "?" denotes an optional rule
that appers once or not at all:

    <one-or-more-octothorps> ::= "#" <one-or-more-octothorps>? ;

The "+" denotes that the rule it modifies may appear one or more times:

    <one-or-more-octothorps> ::= "#"+ ;

The "*" denotes a rule that appears several times or not at all:

    <octothorps-or-an-empty-string> ::= "#"* ;

This covers all of the supported BNF syntax."""

ALLOWED_SYMBOL_NAME_CHARACTERS = string.ascii_letters + string.digits + '-_'
START_LIMIT         = 5
PLUS_LIMIT          = 5
REGEXP_REPEAT_LIMIT = 5


# patch Xeger to generate less characters from * and +
Xegerm = Xeger

def _handle_repeat(self: Xeger, start_range: int, end_range: int, value: str) -> str:
    result = []
    end_range = min((end_range, self.star_plus_limit))
    times = self._random.randint(start_range, end_range)
    for _ in range(times):
        result.append(''.join(self._handle_state(i) for i in value))
    return ''.join(result)

Xegerm._handle_repeat = _handle_repeat
xegerm = Xegerm()

def random_string_from_regex(regex: re.Pattern, star_plus_limit: int = REGEXP_REPEAT_LIMIT) -> str:
    xegerm.star_plus_limit = star_plus_limit
    return xegerm.xeger(regex)


# primitive error handling (not handle anything and just die)
def bold_red(string: str) -> str:
    return f'\x1b[1;31m{string}\x1b[0m'


def report_error_and_exit(error_text: str, exit_code: int = 1) -> NoReturn:
    print(f'{bold_red('error')}: {error_text}')
    raise SystemExit(exit_code)


# tokens
class TokenKind(enum.Enum):
    DEFINE    = enum.auto()
    SYMBOL    = enum.auto()
    LITERAL   = enum.auto()
    SEMICOLON = enum.auto()
    ALTER     = enum.auto()
    REGEX     = enum.auto()
    OPAREN    = enum.auto()
    CPAREN    = enum.auto()
    STAR      = enum.auto()
    PLUS      = enum.auto()
    OPTION    = enum.auto()


@dataclasses.dataclass
class Token:
    kind: TokenKind
    value: str | None


def lex_bnf(bnf: str) -> list[Token]:
    idx = 0
    tokens = []
    while idx < len(bnf):
        if bnf[idx] == '<':
            symbol_name = ''
            idx += 1
            while idx < len(bnf) and bnf[idx] != '>':
                if bnf[idx] not in ALLOWED_SYMBOL_NAME_CHARACTERS:
                    report_error_and_exit(
                        'only ASCII uppercase and lowercase letters, digits, and "-" and "_" '
                        f'characters are allowed in symbol names; got: "{bnf[idx]}"'
                    )
                symbol_name += bnf[idx]
                idx += 1
            if idx == len(bnf):
                report_error_and_exit(f'unterminated rule name near "{symbol_name}"')
            tokens.append(Token(TokenKind.SYMBOL, symbol_name))
            idx += 1

        elif bnf[idx] == ':':
            if idx + 3 <= len(bnf) and bnf[idx:idx + 3] == '::=':
                tokens.append(Token(TokenKind.DEFINE, None))
                idx += 3
            else:
                report_error_and_exit('broken rule definition')

        elif bnf[idx] == '"':
            value = ''
            idx += 1
            while idx < len(bnf) and bnf[idx] != '"':
                if bnf[idx] == '\\':
                    idx += 1
                    if bnf[idx] == 'n':
                        value += '\n'
                        idx += 1
                        continue
                    elif bnf[idx] == 't':
                        value += '\t'
                        idx += 1
                        continue
                    elif bnf[idx] == '\\':
                        value += '\\'
                        idx += 1
                        continue
                    else:
                        report_error_and_exit(f'unrecognized escape sequence: \\"{bnf[idx]}"')
                value += bnf[idx]
                idx += 1
            if idx == len(bnf):
                report_error_and_exit(f'unterminated literal value near "{value}"')
            tokens.append(Token(TokenKind.LITERAL, value))
            idx += 1

        elif bnf[idx] == "'":
            value = ''
            idx += 1
            while idx < len(bnf) and bnf[idx] != "'":
                if bnf[idx] == '\\':
                    idx += 1
                    if bnf[idx] == 'n':
                        value += '\n'
                        idx += 1
                        continue
                    elif bnf[idx] == 't':
                        value += '\t'
                        idx += 1
                        continue
                    elif bnf[idx] == '\\':
                        value += '\\'
                        idx += 1
                        continue
                    else:
                        report_error_and_exit(f'unrecognized escape sequence: \\"{bnf[idx]}"')
                value += bnf[idx]
                idx += 1
            if idx == len(bnf):
                report_error_and_exit(f'unterminated literal value near "{value}"')
            tokens.append(Token(TokenKind.LITERAL, value))
            idx += 1

        elif bnf[idx] == '/':
            regex = ''
            idx += 1
            while idx < len(bnf) and bnf[idx] != '/':
                if bnf[idx] == "'":
                    idx += 1
                    if idx < len(bnf):
                        if bnf[idx] == '/':
                            regex += '/'
                            idx += 1
                            continue
                        elif bnf[idx] == "'":
                            regex += "'"
                            idx += 1
                            continue
                        else:
                            report_error_and_exit('unrecognized escape sequence in regex')
                    else:
                        report_error_and_exit('broken escape sequence in regex')
                regex += bnf[idx]
                idx += 1
            if idx == len(bnf):
                report_error_and_exit(f'unterminated literal value near "{symbol_name}"')
            tokens.append(Token(TokenKind.REGEX, regex))
            idx += 1

        elif bnf[idx] == ';':
            tokens.append(Token(TokenKind.SEMICOLON, None))
            idx += 1

        elif bnf[idx] == '|':
            tokens.append(Token(TokenKind.ALTER, None))
            idx += 1

        elif bnf[idx] == '(':
            tokens.append(Token(TokenKind.OPAREN, None))
            idx += 1

        elif bnf[idx] == ')':
            tokens.append(Token(TokenKind.CPAREN, None))
            idx += 1

        elif bnf[idx] == '*':
            tokens.append(Token(TokenKind.STAR, None))
            idx += 1

        elif bnf[idx] == '+':
            tokens.append(Token(TokenKind.PLUS, None))
            idx += 1

        elif bnf[idx] == '?':
            tokens.append(Token(TokenKind.OPTION, None))
            idx += 1

        elif bnf[idx] == '#':
            while idx < len(bnf) and bnf[idx] != '\n':
                idx += 1

        elif bnf[idx] in string.whitespace:
            idx += 1

        else:
            report_error_and_exit(f'unrecognized symbol: "{bnf[idx]}" (code: {ord(bnf[idx])})')

    return tokens


# rules
type Rule = LiteralRule     \
          | RegexRule       \
          | CompoundRule    \
          | AlterationRule  \
          | ReferenceRule   \
          | OptionalRule    \
          | NoneOrMoreRule  \
          | OneOrMoreRule

type DictOfRules = dict[str, Rule]

@dataclasses.dataclass
class LiteralRule:
    value: str

    def gen(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f'LiteralRule("{self.value.replace('\n', '\\n')}")'

    def __str__(self) -> str:
        return repr(self)


@dataclasses.dataclass
class RegexRule:
    value: re.Pattern

    def gen(self) -> str:
        return random_string_from_regex(self.value)

    def __repr__(self) -> str:
        return f'RegexRule({self.value})'

    def __str__(self) -> str:
        return repr(self)


@dataclasses.dataclass
class CompoundRule:
    values: list[Rule]

    def gen(self) -> str:
        return ''.join(r.gen() for r in self.values)

    def __repr__(self) -> str:
        return f'CompoundRule({', '.join(repr(v) for v in self.values)})'

    def __str__(self) -> str:
        return repr(self)


@dataclasses.dataclass
class AlterationRule:
    values: list[Rule]

    def gen(self) -> str:
        value = random.choice(self.values)
        return value.gen()

    def __repr__(self) -> str:
        return f'AlterationRule({', '.join(repr(v) for v in self.values)})'

    def __str__(self) -> str:
        return repr(self)


@dataclasses.dataclass
class ReferenceRule:
    symbol: str
    context: DictOfRules
    __had_repr_call: bool = False

    def gen(self) -> str:
        value = self.context.get(self.symbol)
        if value is None:
            report_error_and_exit(f'reference to an undefined rule <{self.symbol}>')
        return value.gen()

    def __repr__(self) -> str:
        if self.__had_repr_call:
            return f'ReferenceRule(<{self.symbol}> with reference to self)'
        self.__had_repr_call = True
        value = self.context.get(self.symbol)
        return f'ReferenceRule(<{self.symbol}> with {value})'

    def __str__(self) -> str:
        return repr(self)


@dataclasses.dataclass
class OptionalRule:
    value: Rule

    def gen(self) -> str:
        return self.value.gen() if random.choice((True, False)) else ''

    def __repr__(self) -> str:
        return f'OptionalRule({self.value})'

    def __str__(self) -> str:
        return repr(self)


@dataclasses.dataclass
class NoneOrMoreRule:
    value: Rule

    def gen(self) -> str:
        times = random.randint(0, START_LIMIT)
        return ''.join(self.value.gen() for _ in range(times))

    def __repr__(self) -> str:
        return f'NoneOrMoreRule({self.value})'

    def __str__(self) -> str:
        return repr(self)


@dataclasses.dataclass
class OneOrMoreRule:
    value: Rule

    def gen(self) -> str:
        times = random.randint(1, PLUS_LIMIT)
        return ''.join(self.value.gen() for _ in range(times))

    def __repr__(self) -> str:
        return f'OneOrMoreRule({self.value})'

    def __str__(self) -> str:
        return repr(self)


type DictOfSymbolDefinitions = dict[str, list[Token]]

def parse_all_symbol_definitions(tokens: list[Token]) -> DictOfSymbolDefinitions:
    idx = 0
    definitions: DictOfSymbolDefinitions = {}
    while idx < len(tokens):
        if tokens[idx].kind == TokenKind.DEFINE:
            if idx == 0 or tokens[idx - 1].kind != TokenKind.SYMBOL:
                report_error_and_exit('missing symbol for definition')
            rule_symbol = tokens[idx - 1].value
            rule_tokens: list[Token] = []
            idx += 1
            while idx < len(tokens) and tokens[idx].kind != TokenKind.SEMICOLON:
                rule_tokens.append(tokens[idx])
                idx += 1
            if idx >= len(tokens) or tokens[idx].kind != TokenKind.SEMICOLON:
                report_error_and_exit('missing semicolon for rule definition')
            if rule_symbol in definitions:
                report_error_and_exit(f'attempt to redefine existing rule "{rule_symbol}"')
            definitions[rule_symbol] = rule_tokens
        idx += 1
    return definitions


def parse_bnf_tokens(tokens: list[Token]) -> Rule:
    definitions = parse_all_symbol_definitions(tokens)
    if 'start' not in definitions:
        report_error_and_exit('could not find an entry point; grammar must contain a <start> rule')

    parsed_rules: DictOfRules = {}

    for rule_symbol, rule_tokens in definitions.items():
        alteration_variants: list[LiteralRule | RegexRule | ReferenceRule | CompoundRule] = []
        current_variant_rules: list[LiteralRule | RegexRule | ReferenceRule] = []
        idx = 0
        while idx < len(rule_tokens):
            if rule_tokens[idx].kind == TokenKind.LITERAL:
                current_variant_rules.append(LiteralRule(rule_tokens[idx].value))
                idx += 1

            elif rule_tokens[idx].kind == TokenKind.REGEX:
                current_variant_rules.append(RegexRule(re.compile(rule_tokens[idx].value)))
                idx += 1

            elif rule_tokens[idx].kind == TokenKind.SYMBOL:
                current_variant_rules.append(ReferenceRule(rule_tokens[idx].value, parsed_rules))
                idx += 1

            elif rule_tokens[idx].kind == TokenKind.OPTION:
                to_make_optional = current_variant_rules.pop()
                current_variant_rules.append(OptionalRule(to_make_optional))
                idx += 1

            elif rule_tokens[idx].kind == TokenKind.STAR:
                to_make_repeatable = current_variant_rules.pop()
                current_variant_rules.append(NoneOrMoreRule(to_make_repeatable))
                idx += 1

            elif rule_tokens[idx].kind == TokenKind.PLUS:
                to_make_repeatable = current_variant_rules.pop()
                current_variant_rules.append(OneOrMoreRule(to_make_repeatable))
                idx += 1

            elif rule_tokens[idx].kind == TokenKind.ALTER:
                if len(current_variant_rules) == 0:
                    report_error_and_exit(f'empty alteration variant in rule <{rule_symbol}>')
                elif len(current_variant_rules) == 1:
                    variant = current_variant_rules[0]
                else:
                    variant = CompoundRule(current_variant_rules)
                alteration_variants.append(variant)
                current_variant_rules = []
                idx += 1

            else:
                report_error_and_exit(
                    f'rules of kind {rule_tokens[idx].kind} are not supported yet'
                )

        # last variant is never handled in the loop
        if len(current_variant_rules) == 0:
            report_error_and_exit(f'empty alteration variant in rule <{rule_symbol}>')
        elif len(current_variant_rules) == 1:
            variant = current_variant_rules[0]
        else:
            variant = CompoundRule(current_variant_rules)
        alteration_variants.append(variant)

        if len(alteration_variants) == 0:
            report_error_and_exit(f'rule <{rule_symbol}> is empty')
        elif len(alteration_variants) == 1:
            rule = alteration_variants[0]
        else:
            rule = AlterationRule(alteration_variants)
        parsed_rules[rule_symbol] = rule

    return ReferenceRule('start', parsed_rules)


def parse_bnf(bnf: str) -> ReferenceRule:
    tokens = lex_bnf(bnf)
    return parse_bnf_tokens(tokens)


def main() -> None:
    parser = argparse.ArgumentParser(
        'pybnfuzzer',
        description='a simple program to generate random strings based on a BNF grammar'
    )
    parser.add_argument(
        'file',
        type=argparse.FileType('r'), help='file containing a BNF description of a grammar'
    )
    parser.add_argument(
        '-s', '--syntax-help',
        action='store_true',
        help='show a brief description of the supported BNF syntax and exit'
    )
    parser.add_argument(
        '-o', '--output',
        default=sys.stdout,
        type=argparse.FileType('w'),
        help='file to write generated strings to; by default, outputs results to stdout',
        metavar='<file>'
    )
    parser.add_argument(
        '-r', '--recursion',
        type=int,
        help=f'change recursion depth limit; the default is {sys.getrecursionlimit()}',
        metavar='<n>'
    )
    parser.add_argument(
        '--emit-ast',
        action='store_true',
        help=
            'if set, will emit parsed AST of the provided BNF grammar '
            'instead of a generated string; useful for debugging'
    )

    # a workaround to add another option that behaves like a help message
    # without complaining that a required positional argument was not provided
    # and without making the positional argument optional
    if '--bnf-help' in sys.argv or '-s' in sys.argv:
        print(BNF_SYNTAX)
        exit(0)

    args = parser.parse_args()

    if args.recursion:
        sys.setrecursionlimit(args.recursion)

    with args.file as f:
        bnf = f.read()

    ast_entry_point = parse_bnf(bnf)

    with args.output as f:
        if args.emit_ast:
            f.write(repr(ast_entry_point))
        else:
            try:
                f.write(ast_entry_point.gen())
            except RecursionError:
                report_error_and_exit('maximum recursion depth exceeded')
            except Exception as e:
                raise e


if __name__ == '__main__':
    main()
