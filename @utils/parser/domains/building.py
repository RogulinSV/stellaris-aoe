#!/usr/bin/env python
# -*- coding: utf-8 -*-

from parsing import BlockToken
from .common import Collection


class Upgrades(object):
    __instance = None

    def __new__(cls):
        if cls.__instance is None:
            cls.__instance = super(Upgrades, cls).__new__(cls)
            cls.__instance.__upgrades_from = dict()
            cls.__instance.__upgrades_into = dict()

        return cls.__instance

    def set(self, building: str, upgrades: list):
        for upgrade in upgrades:
            self.add(building, upgrade)

    def add(self, building: str, upgrade: str):
        if building not in self.__upgrades_into:
            self.__upgrades_into[building] = set()
        if upgrade not in self.__upgrades_from:
            self.__upgrades_from[upgrade] = set()

        self.__upgrades_from[upgrade].add(building)
        self.__upgrades_into[building].add(upgrade)

    def path(self, building: str) -> list:
        if building not in self.__upgrades_from:
            return list()

        upgrades = list()
        for upgrade in self.__upgrades_from.get(building):
            upgrades_path = self.path(upgrade)
            if len(upgrades_path) > 0:
                for upgrade_path in upgrades_path:
                    upgrades.append((upgrade, *(upgrade_path)))
            else:
                upgrades.append((upgrade,))

        upgrades.sort(key=lambda upgrades: len(upgrades), reverse=True)

        return upgrades


class Building(object):
    def __init__(self, name: str):
        self.__name = name
        self.__category = None
        self.__buildtime = 0
        self.__upgrades = Upgrades()

    @property
    def name(self) -> str:
        return self.__name

    @property
    def description(self) -> str:
        return ' '.join([part.lower().capitalize() for part in self.__name.replace('building_', '').split('_')])

    @property
    def localization(self) -> str:
        return '_'.join([part.upper() for part in self.__name.replace('building_', '').split('_')])

    @property
    def category(self) -> str:
        return self.__category

    @category.setter
    def category(self, category: str):
        self.__category = category

    @property
    def buildtime(self) -> int:
        return self.__buildtime

    @buildtime.setter
    def buildtime(self, value: int):
        self.__buildtime = value

    @property
    def upgrade(self) -> list:
        return self.__upgrades.path(self.__name)

    @upgrade.setter
    def upgrade(self, upgrade: str):
        self.__upgrades.add(self.__name, upgrade)

    @staticmethod
    def from_token(token: BlockToken):
        building = Building(token.name)
        building.category = token.properties.get('category')
        if 'base_buildtime' in token.properties:
            building.buildtime = int(token.properties.get('base_buildtime'))
        if 'upgrades' in token.properties:
            for upgrade in token.properties.get('upgrades'):
                building.upgrade = upgrade

        return building


class Buildings(Collection):
    def __contains__(self, building: Building):
        if not isinstance(building, Building):
            raise ValueError('Unexpected argument')

        if building in self._items:
            return True

        for item in self._items:  # type: Building
            if item.name == building.name and item.category == building.category:
                return True

        return False

    def add(self, building: Building):
        if not isinstance(building, Building):
            raise ValueError('Unexpected argument')

        self._items.add(building)

    def sorted(self):
        for building in sorted(self._items, key=lambda building: str(building.category) + '_' + building.name):
            yield building

    def categories(self) -> set:
        categories = set()
        for building in self._items:
            if building.category is not None:
                categories.add(building.category)

        return categories
