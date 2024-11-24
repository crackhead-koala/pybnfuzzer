# BNF Fuzzer in Python
A simple tool to generate random strings based on a [BNF grammar](https://en.wikipedia.org/wiki/Backus–Naur_form). Inspired by [BNF Fuzzer in Go](https://github.com/rexim/bnfuzzer) by @rexim; although no code was taken from their project, just the idea.

## Quick Start
Clone this repo and install the requirements. Note that you must use Python version 3.12 or higher:

```shell
$ python3.12 -m venv ./.venv
$ source ./.venv/bin/activate
$ pip install -r ./requirements.txt
```

Then you can use it as any python module:

```shell
$ python -m pybnfuzzer -h
usage: pybnfuzzer [-h] [-s] [-o <file>] [-r <n>] [--emit-ast] file

a simple program to generate random strings based on a BNF grammar

positional arguments:
  file                 file containing a BNF description of a grammar

options:
  -h, --help           show this help message and exit
  -s, --syntax-help    show a brief description of the supported BNF syntax
                       and exit
  -o, --output <file>  file to write generated strings to; by default,
                       outputs results to stdout
  -r, --recursion <n>  change recursion depth limit; the default is 1000
  --emit-ast           if set, will emit parsed AST of the provided BNF
                       grammar instead of a generated string; useful for
                       debugging
```

## Quick BNF Syntax Reference
The BNF syntax inplemented by this tool can be accessed at any time with this command:

```shell
$ python -m pybnfuzzer --syntax-help
```

It is mostly compatable with the syntax described on the [Wikipedia article](https://en.wikipedia.org/wiki/Backus–Naur_form).

Rules are defined with the following notation:

```
<symbol> ::= [rule] ;
```

Rule names must be enclosed in angle brackets (`<` and `>`) and can contain only lower- and uppercase letters, digits, and `-` and `_` characters. The semicolon at the end is requred. All whitespace is for formatting and styling purposes only and is ignored by the parser.

`pybnfuzzer` additionally  requires the grammar to have a special <start> rule, which is used as an entry point for string generation.

Terminal rules are expressed between double or single quotes:

```
<this-is-a-terminal>      ::= "#" ;
<this-is-also-a-terminal> ::= '@' ;
```

Everything from `#` until the end of a line is treated as a comment:

```
# this is the start of my grammar
<start> ::= "grammar" ;  # a literal grammar!
```

Choices between several variants are denoted by a vertical bar `|`:

```
<digits> ::= "0" | "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9" ;
```

For convenience, regular expressions can be used to describe terminal rules. The expression must be enclosed between slash symbols `/`:

```
<digits>        ::= /[0-9]/ ;
<variable-name> ::= /[A-Za-z0-9_]+/ ;
```

Literal `/` within regular expressions must be escaped with a `'`. A literal `'` must be escaped as well:

```
<five-slashes>            ::= /'/{5}/ ;
<digits-in-single-quotes> ::= /''\d+''/ ;
```

Not all Python regexp features are supported; for more information, please refer to the [rstr module documentation](https://github.com/leapfrogonline/rstr).

Some extra rule modifiers are also supported. The `?` denotes an optional rule that appers once or not at all:

```
<one-or-more-octothorps> ::= "#" <one-or-more-octothorps>? ;
```

The `+` denotes that the rule it modifies may appear one or more times:

```
<one-or-more-octothorps> ::= "#"+ ;
```

The `*` denotes a rule that appears several times or not at all:

```
<octothorps-or-an-empty-string> ::= "#"* ;
```

This covers all of the supported BNF syntax.
