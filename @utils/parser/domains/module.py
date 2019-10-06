#!/usr/bin/env python
# -*- coding: utf-8 -*-


class Module(object):
    def __init__(self, id: int):
        self.__id = id
        self.__name = None

    def __str__(self):
        return '(%d) %s' % (self.__id, str(self.__name))

    @property
    def id(self) -> int:
        return self.__id

    @property
    def name(self) -> str:
        return self.__name

    @name.setter
    def name(self, value: str):
        self.__name = value

    @property
    def url(self) -> str:
        return 'https://steamcommunity.com/sharedfiles/filedetails/?id=' + str(self.id)


class Settings(object):
    def __init__(self):
        self.__modules = dict()

    def add_module(self, module_id: int, is_enabled: bool):
        if module_id not in self.__modules:
            self.__modules[module_id] = is_enabled

    def get_modules(self) -> tuple:
        return tuple(self.__modules.keys())

    def has_module(self, module: Module, is_enabled: bool = True) -> bool:
        return module.id in self.__modules and self.__modules.get(module.id) == is_enabled
