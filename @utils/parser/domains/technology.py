#!/usr/bin/env python
# -*- coding: utf-8 -*-

from parsing import BlockToken
from .common import Collection


class Technology(object):
    def __init__(self, name: str):
        self.__name = name
        self.__area = None
        self.__categories = list()
        self.__is_rare = False
        self.__is_dangerous = False

    def __str__(self):
        return self.__name

    @property
    def name(self):
        return self.__name

    @property
    def area(self):
        return self.__area

    @area.setter
    def area(self, value: str):
        self.__area = value

    @property
    def categories(self):
        return self.__categories

    @property
    def is_rare(self):
        return self.__is_rare

    @is_rare.setter
    def is_rare(self, value: bool):
        self.__is_rare = value

    @property
    def is_dangerous(self):
        return self.__is_dangerous

    @is_dangerous.setter
    def is_dangerous(self, value: bool):
        self.__is_dangerous = value

    @staticmethod
    def from_token(token: BlockToken):
        tech = Technology(token.name)
        tech.area = token.properties.get('area')
        tech.categories.extend(token.properties.get('category', list()))
        if token.properties.get('is_rare', 'no') == 'yes':
            tech.is_rare = True
        if token.properties.get('is_dangerous', 'no') == 'yes':
            tech.is_dangerous = True

        return tech


class Technologies(Collection):
    def __contains__(self, technology: Technology):
        if not isinstance(technology, Technology):
            raise ValueError('Unexpected argument')

        if technology in self._items:
            return True

        for item in self._items:  # type: Technology
            if item.name == technology.name and item.area == technology.area:
                return True

        return False

    def add(self, technology: Technology):
        if not isinstance(technology, Technology):
            raise ValueError('Unexpected argument')

        self._items.add(technology)

    def sorted(self):
        for technology in sorted(self._items, key=lambda technology: technology.area + '_' + technology.name):
            yield technology

    def names(self, category: str = None, area: str = None) -> list:
        _self = self
        if category is not None:
            _self = _self.filter(lambda technology: category in technology.categories)
        if area is not None:
            _self = _self.filter(lambda technology: area == technology.area)

        return _self.map(lambda technology: technology.name, sort=True)

    def categories(self) -> set:
        categories = set()
        for technology in self._items:
            for category in technology.categories:
                categories.add(category)

        return categories
