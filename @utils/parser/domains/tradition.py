#!/usr/bin/env python
# -*- coding: utf-8 -*-

from parsing import BlockToken
from domains import Collection


class Tradition(object):
    def __init__(self, name: str):
        self.__name = name
        self.__is_adopted = False
        self.__is_finished = False

    @property
    def name(self) -> str:
        return self.__name

    @property
    def is_adopted(self) -> bool:
        return self.__is_adopted

    @is_adopted.setter
    def is_adopted(self, value: bool):
        self.__is_adopted = value

    @property
    def is_finished(self) -> bool:
        return self.__is_finished

    @is_finished.setter
    def is_finished(self, value: bool):
        self.__is_finished = value


class Category(object):
    def __init__(self, name: str):
        self.__name = name
        self.__traditions = dict()

    def __str__(self):
        return '%s [%s]' % (self.__name, self.traditions.keys())

    @property
    def name(self) -> str:
        return self.__name

    @property
    def category(self) -> str:
        return self.__name.replace('tradition_', '')

    @property
    def traditions(self) -> dict:
        return self.__traditions

    @staticmethod
    def from_token(token: BlockToken):
        category = Category(token.name)
        for name in token.properties.get('traditions'):
            category.traditions[name] = Tradition(name)

        name = token.properties.get('adoption_bonus')
        tradition = Tradition(name)
        tradition.is_adopted = True
        category.traditions[name] = tradition
        name = token.properties.get('finish_bonus')
        tradition = Tradition(name)
        tradition.is_finished = True
        category.traditions[name] = tradition

        return category


class Categories(Collection):
    def __contains__(self, category: Category):
        if not isinstance(category, Category):
            raise ValueError('Unexpected argument')

        if category in self._items:
            return True

        for item in self._items:  # type: Category
            if item.name == category.name:
                return True

        return False

    def add(self, category: Category):
        if not isinstance(category, Category):
            raise ValueError('Unexpected argument')

        self._items.add(category)

    def sorted(self):
        for category in sorted(self._items, key=lambda category: category.name):
            yield category
