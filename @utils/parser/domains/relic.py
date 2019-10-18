#!/usr/bin/env python
# -*- coding: utf-8 -*-

from parsing import BlockToken
from .common import Collection


class Relic(object):
    def __init__(self, name: str):
        self.__name = name
        self.__score = 0

    def __str__(self):
        return self.__name

    @property
    def name(self) -> str:
        return self.__name

    @property
    def score(self) -> int:
        return self.__score

    @score.setter
    def score(self, value: int):
        self.__score = value

    @staticmethod
    def from_token(token: BlockToken):
        relic = Relic(token.name)
        relic.score = int(token.properties.get('score'))

        return relic


class Relics(Collection):
    def __contains__(self, relic: Relic):
        if not isinstance(relic, Relic):
            raise ValueError('Unexpected argument')

        if relic in self._items:
            return True

        for item in self._items:  # type: Relic
            if item.name == relic.name and relic.score == relic.score:
                return True

        return False

    def add(self, relic: Relic):
        if not isinstance(relic, Relic):
            raise ValueError('Unexpected argument')

        self._items.add(relic)

    def sorted(self):
        for relic in sorted(self._items, key=lambda relic: relic.name + '_' + str(relic.score)):
            yield relic
