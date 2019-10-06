#!/usr/bin/env python
# -*- coding: utf-8 -*-

import inspect


class Collection(object):
    def __init__(self):
        self._items = set()

    def __contains__(self, item):
        return item in self._items

    def __add__(self, other):
        self.add(other)

    def __call__(self, *args, **kwargs):
        if len(kwargs) > 0:
            raise ValueError('Unexpected named arguments %s' % str(kwargs.keys()))

        result = True
        for arg in args:
            if not self.__contains__(arg):
                self.add(arg)
            else:
                result = False

        return result

    def __iter__(self):
        for item in self._items:
            yield item

    def __len__(self):
        return len(self._items)

    def add(self, item):
        raise NotImplementedError('Method %s not implemented yet...' % inspect.currentframe().f_code.co_name)

    def map(self, callback: callable, sort: bool = False) -> list:
        output = list()
        for item in self._items:
            output.append(callback(item))
        if sort:
            output.sort()

        return output

    def filter(self, callback: callable):
        _self = self.__class__()
        for item in self._items:
            if callback(item):
                _self.add(item)

        return _self