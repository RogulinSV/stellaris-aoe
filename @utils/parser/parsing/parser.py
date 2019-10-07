#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pyparsing import Word, Literal, Forward, Dict, Group, Optional, Combine, ZeroOrMore, OneOrMore, ParseException, \
    ParseResults, alphanums, nums, dblQuotedString, removeQuotes, pythonStyleComment, ParserElement


class Token(object):
    def __init__(self, name: str):
        self.__token_name = name

    def __str__(self):
        return self.__token_name

    @property
    def name(self) -> str:
        return self.__token_name


class PropertyToken(Token):
    def __init__(self, name: str):
        super(PropertyToken, self).__init__(name)
        self.__token_value = None

    def __str__(self):
        return str(self.__token_value)

    @property
    def value(self):
        return self.__token_value

    @value.setter
    def value(self, value: str):
        self.__token_value = value


class EnumerationToken(Token):
    def __init__(self, name: str):
        super(EnumerationToken, self).__init__(name)
        self.__elements = list()

    def __str__(self):
        return '[' + ', '.join(self.__elements) + ']'

    def __iter__(self):
        for value in self.__elements:
            yield value

    def __len__(self):
        return len(self.__elements)

    def append(self, value: str):
        self.__elements.append(value)


class BlockToken(Token):
    def __init__(self, name: str):
        super(BlockToken, self).__init__(name)
        self.__properties = dict()
        self.__tokens = list()

    def __str__(self):
        s = [super(BlockToken, self).__str__(), '=', '{']
        for p in self.__properties:
            ln = len(self.__properties.get(p))
            if ln > 1:
                s.extend([p, '=', '{'])
                for v in self.__properties.get(p):
                    s.append(v)
                s.append('}')
            elif ln == 1:
                s.extend([p, '=', self.__properties.get(p)[0]])
        for t in self.__tokens:
            s.append(str(t))
        s.append('}')

        return ' '.join(s)

    def __iter__(self):
        for child in self.__tokens:
            yield child

    def __len__(self):
        return len(self.__tokens)

    def append(self, token: Token):
        self.__tokens.append(token)

    @property
    def includes(self) -> dict:
        return {token.name: token for token in self.__tokens if isinstance(token, BlockToken)}

    @property
    def properties(self):
        return self.__properties


class VariableToken(Token):
    def __init__(self, name: str):
        super(VariableToken, self).__init__(name)
        self.__token_value = None

    @property
    def value(self):
        return self.__token_value

    @value.setter
    def value(self, value: str):
        self.__token_value = value


class NamespaceToken(Token):
    pass


def token_property_visitor(stack: str, lineno: int, tokens: ParseResults) -> None:
    tokens[0] = PropertyToken(tokens[0])


def token_block_visitor(stack: str, lineno: int, tokens: ParseResults) -> None:
    tokens[0] = BlockToken(tokens[0])


def token_variable_visitor(stack: str, lineno: int, tokens: ParseResults) -> None:
    tokens[0] = VariableToken(tokens[0])


def token_enumeration_visitor(stack: str, lineno: int, tokens: ParseResults) -> None:
    tokens[0] = EnumerationToken(tokens[0])


def token_namespace_visitor(stack: str, lineno: int, tokens: ParseResults) -> None:
    tokens[0] = NamespaceToken(tokens[1])


def create_grammar() -> ParserElement:
    """Creating grammar rules

    :rtype: ParserElement
    """
    minus = Literal('-')
    lbrack = Literal('{').suppress()
    rbrack = Literal('}').suppress()
    assign = Literal('=').suppress()
    compare = Literal('>=').suppress() | Literal('<=').suppress() | Literal('>').suppress() | Literal('<').suppress()
    letters = alphanums + '_'
    entity = letters + '-:.'
    numbers = Combine(Optional(minus) + Word(nums) + Optional(Word('.', nums))) | Word('.', nums)

    namespace = Word('namespace') + assign + Word(letters)
    namespace.setParseAction(token_namespace_visitor)
    namespace.setResultsName('namespace')
    # namespace = namespace.suppress()
    variable = Word('@', letters) + assign + numbers
    variable.setParseAction(token_variable_visitor)
    variable.setResultsName('variable')
    value = dblQuotedString.setParseAction(removeQuotes)
    prop = Word(entity) + (assign | compare) + (numbers | value | Word(entity) | Word('@', letters))
    prop.setParseAction(token_property_visitor)
    prop.setResultsName('property')
    # enums = Forward()
    enums = Word(entity) + assign + lbrack + OneOrMore(Group(Word(entity) | value)) + rbrack
    enums.setParseAction(token_enumeration_visitor)
    enums.setResultsName('enumeration')
    block = Forward()
    # block << (value | Word(letters)) + assign + lbrack + Dict(ZeroOrMore(Group(prop | block))) + rbrack
    block << (value | Word(entity)) + (assign | compare) + lbrack + ZeroOrMore(Group(prop | block | enums)) + rbrack
    block.setParseAction(token_block_visitor)
    block.setResultsName('block')
    # context = Dict(ZeroOrMore(Group(block | variable)))
    context = Optional(Group(namespace)) + ZeroOrMore(Group(block | variable))
    context.ignore(pythonStyleComment)

    return context


def parse_token(parsed) -> Token:
    if isinstance(parsed[0], NamespaceToken):
        token = parsed[0]  # type: NamespaceToken
    elif isinstance(parsed[0], VariableToken):
        token = parsed[0]  # type: VariableToken
        token.value = str(parsed[1])
    elif isinstance(parsed[0], PropertyToken):
        token = parsed[0]  # type: PropertyToken
        token.value = str(parsed[1])
    elif isinstance(parsed[0], EnumerationToken):
        token = parsed[0]  # type: EnumerationToken
        for value in parsed[1:]:
            token.append(str(value[0]))
    elif isinstance(parsed[0], BlockToken):
        token = parsed[0]  # type: BlockToken
        parsed.pop(0)
        for node in parsed:
            _token = parse_token(node)
            if isinstance(_token, PropertyToken):
                token.properties[_token.name] = _token.value
            elif isinstance(_token, EnumerationToken):
                token.properties[_token.name] = list(_token)
            elif isinstance(_token, BlockToken):
                token.append(_token)
            else:
                raise TypeError('Unknown token type %s' % _token)
    else:
        raise TypeError('Unknown token type %s' % parsed)

    return token


def parse_tokens(parsed) -> list:
    tokens = []
    for node in parsed:
        tokens.append(parse_token(node))

    return tokens


def parse_string(string: str) -> list:
    """Parsing specified string

    :param string: File content for parsing
    :type string: str
    :rtype: list
    :raises: ParseException
    """
    parsed = create_grammar().parseString(string, parseAll=True)

    return parse_tokens(parsed)


def parse_file(filepath: str) -> list:
    """Parsing content of specified file

    :param filepath: Path to file with content for parsing
    :type filepath: str
    :rtype: list
    :raises: ParseException
    """
    parsed = create_grammar().parseFile(filepath, parseAll=True)

    return parse_tokens(parsed)


def parse_settings(settings: str):
    minus = Literal('-')
    lbrack = Literal('{').suppress()
    rbrack = Literal('}').suppress()
    assign = Literal('=').suppress()
    compare = Literal('>=').suppress() | Literal('<=').suppress() | Literal('>').suppress() | Literal('<').suppress()
    letters = alphanums + '_'
    entity = letters + '-:.'
    numbers = Combine(Optional(minus) + Word(nums) + Optional(Word('.', nums))) | Word('.', nums)

    variable = Word('@', letters) + assign + numbers
    variable.setParseAction(token_variable_visitor)
    variable.setResultsName('variable')
    value = dblQuotedString.setParseAction(removeQuotes)
    prop = Word(entity) + (assign | compare) + (numbers | value | Word(entity) | Word('@', letters))
    prop.setParseAction(token_property_visitor)
    prop.setResultsName('property')
    # enums = Forward()
    enums = Word(entity) + assign + lbrack + OneOrMore(Group(Word(entity) | value)) + rbrack
    enums.setParseAction(token_enumeration_visitor)
    enums.setResultsName('enumeration')
    block = Forward()
    # block << Word(letters) + assign + lbrack + Dict(ZeroOrMore(Group(prop | block))) + rbrack
    block << Word(entity) + (assign | compare) + lbrack + ZeroOrMore(Group(prop | block | enums)) + rbrack
    block.setParseAction(token_block_visitor)
    block.setResultsName('block')
    # context = Dict(ZeroOrMore(Group(block | variable)))
    context = ZeroOrMore(Group(block | variable | prop | enums))
    context.ignore(pythonStyleComment)

    parsed = context.parseFile(settings, parseAll=True)

    return parse_tokens(parsed)
