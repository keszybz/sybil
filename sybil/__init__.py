from bisect import bisect
from glob import glob
from os.path import join, dirname, abspath

import sys

from .integration.nose import nose_integration

class Region(object):

    def __init__(self, start, end, parsed, evaluator):
        self.start, self.end, self.parsed, self.evaluator = (
            start, end, parsed, evaluator
        )

    def __repr__(self):
        return '<Region start={} end={} {!r}>'.format(
            self.start, self.end, self.evaluator
        )


class Example(object):

    def __init__(self, path, line, column, region):
        self.path = path
        self.line = line
        self.column = column
        self.region = region

    def __repr__(self):
        return '<Example path={} line={} column={} using {!r}>'.format(
            self.path, self.line, self.column, self.region.evaluator
        )

    def evaluate(self, namespace):
        return self.region.evaluator(self.region.parsed, namespace)


class Document(object):

    def __init__(self, text, path):
        self.text = text
        self.path = path
        self.end = len(text)
        self.regions = []

    def add(self, region):
        if region.start < 0:
            raise ValueError('{!r} is before start of document'.format(region))
        if region.end > self.end:
            raise ValueError('{!r} goes beyond end of document'.format(region))
        entry = (region.start, region)
        index = bisect(self.regions, entry)
        if index > 0:
            previous = self.regions[index-1][1]
            if previous.end > region.start:
                raise ValueError('{!r} overlaps {!r}'.format(previous, region))
        if index < len(self.regions):
            next = self.regions[index][1]
            if next.start < region.end:
                raise ValueError('{!r} overlaps {!r}'.format(region, next))
        self.regions.insert(index, entry)

    def __iter__(self):
        line = 1
        place = 0
        for _, region in self.regions:
            line += self.text.count('\n', place, region.start)
            line_start = self.text.rfind('\n', place, region.start)
            place = region.start
            yield Example(self.path, line, region.start-line_start, region)


class Sybil(object):

    def __init__(self, parsers, pattern, path='.'):
        self.parsers = parsers
        start_dir = dirname(sys._getframe(1).f_globals.get('__file__'))
        self.path = abspath(join(start_dir, path))
        self.pattern = pattern

    def parse(self, path):
        with open(path) as source:
            text = source.read()
        document = Document(text, path)
        for parser in self.parsers:
            for region in parser(document):
                document.add(region)
        return document

    def all_examples(self):
        for path in glob(join(self.path, self.pattern)):
            for example in self.parse(path):
                yield example

    def nose(self, name=None):
        return nose_integration(self, name)
