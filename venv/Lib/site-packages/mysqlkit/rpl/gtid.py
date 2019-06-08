import operator

from itertools import product
from functools import wraps, reduce


def range_parameter(fn):
    # Decorator to make GTIDRange functions work with tuples and GTIDRange parameters the same way
    def test(arg):
        return isinstance(arg, tuple) and len(arg) in (1, 2)

    @wraps(fn)
    def wrapped(*args, **kwargs):
        kwargs.update(dict([
            (k, GTIDRange(*v) if test(v) else v) for k, v in kwargs.items()
        ]))

        args = [GTIDRange(*arg) if test(arg) else arg for arg in args]

        return fn(*args, **kwargs)

    return wrapped


class GTIDRange(object):
    __slots__ = ('first', 'last')

    def __init__(self, first, last=None):
        if last is None:
            if isinstance(first, str) and '-' in first:
                first, last = map(int, first.split('-', 1))
            else:
                last = first

        self.first, self.last = map(int, (first, last))

        if self.last < self.first:
            raise ValueError('Last trx ID cannot be less than first')

    def __str__(self):
        if self.is_single():
            return str(self.first)

        return '{first}-{last}'.format(first=self.first, last=self.last)

    def __repr__(self):
        return '<GTIDRange:{r}>'.format(r=str(self))

    def __hash__(self):
        return hash(self.as_tuple())

    def __len__(self):
        return self.last - self.first + 1

    @range_parameter
    def __lt__(self, other):
        return self.as_tuple() < other.as_tuple()

    @range_parameter
    def __gt__(self, other):
        return self.as_tuple() > other.as_tuple()

    @range_parameter
    def __eq__(self, other):
        return self.as_tuple() == other.as_tuple()

    @range_parameter
    def __ne__(self, other):
        return self.as_tuple() != other.as_tuple()

    def __getitem__(self, item):
        if item == 0:
            return self.first
        elif item == 1:
            return self.last

        raise IndexError('{range} does not have {item} item'.format(range=self, item=item))

    @range_parameter
    def __contains__(self, item):
        if self.first <= item.first and self.last >= item.last:
            return True

        return False

    @range_parameter
    def __add__(self, other):
        """ Sums up to GTIDRange
        :param other: GTIDRange or tuple
        :return: GTIDRangeList
        """
        if self.is_overlapping(other) or self.is_consecutive(other) or other.is_consecutive(self):
            return GTIDRangeList(GTIDRange(
                min(self.first, other.first),
                max(self.last, other.last),
            ))
        else:
            return GTIDRangeList(self, other)

    @range_parameter
    def __sub__(self, other):
        """ Subtracts two GTIDRange
        :param other: GTIDRange or tuple
        :return: GTIDRangeList
        """
        if other == self:
            return GTIDRangeList()  # Return empty list

        if not self.is_overlapping(other):
            return GTIDRangeList(self)  # Return itself if the two are not overlapping (little speed improvement)

        ranges = []
        markers = sorted(list(set([self.first, self.last + 1] + [other.first, other.last + 1])))
        for f, l in zip(markers[:-1], markers[1:]):
            range = GTIDRange(f, l - 1)
            if range in self and range not in other:
                ranges.append(range)

        return GTIDRangeList(*ranges)

    def is_single(self):
        """ Checks if the range consists of single transaction
        :return: Booleans
        """
        return self.first == self.last

    def is_consecutive(self, other):
        """ Checks if the other range follows this consecutively
        :param other: GTIDRange or tuple
        :return: Boolean

        > GTIDRange(1, 100).is_consecutive(GTIDRange(101, 200))
        True
        > GTIDRange(1, 100).is_consecutive(GTIDRange(102, 200))
        False
        """
        if not isinstance(other, GTIDRange):
            raise TypeError('Can only compare GTIDRanges not {cls}'.format(cls=type(self)))

        return self.last + 1 == other.first

    @range_parameter
    def is_overlapping(self, other):
        """ Checks if the two GTIDRange is overlapping
        :param other: GTIDRange or tuple
        :return: Boolean

        > GTIDRange(1, 100).is_consecutive(GTIDRange(95, 200))
        True
        > GTIDRange(1, 100).is_consecutive(GTIDRange(101, 200))
        False
        """
        return other.first <= self.first <= other.last or other.first <= self.last <= other.last or other in self

    def as_tuple(self):
        """ Returns the tuple of first and last transaction
        :return: tuple
        """
        return self.first, self.last


class GTIDRangeList(object):
    __slots__ = ('ranges', )

    def __init__(self, *ranges):
        if len(ranges) == 1 and isinstance(ranges[0], str):
            ranges = ranges[0]
        self.ranges = sorted(list(self.parse(ranges)))

    def __repr__(self):
        return '<GTIDRangeList:[{lst}]>'.format(lst=str(self))

    def __str__(self):
        return ':'.join([str(r) for r in self.ranges])

    def __eq__(self, other):
        if not isinstance(other, GTIDRangeList):
            raise TypeError('Cannot compare GTIDRangeList with {cls}'.format(cls=type(self)))
        return self.ranges == other.ranges

    def __iter__(self):
        for r in self.ranges:
            yield r

    def __len__(self):
        return len(self.ranges)

    def __getitem__(self, item):
        return self.ranges[item]

    def __contains__(self, item):
        if isinstance(item, GTIDRange):
            return any(map(lambda r: item in r, self.ranges))
        elif isinstance(item, GTIDRangeList):
            return all(map(lambda i: i in self, item))
        else:
            raise TypeError('Item has to be GTIDRange or GTIDRangeList. {cls} provided'.format(cls=type(item)))

    def __add__(self, other):
        if isinstance(other, GTIDRange):
            return GTIDRangeList(*self.ranges)._append(other)

        if not other:
            return GTIDRangeList(*self.ranges)

        ranges = sorted(self.ranges + other.ranges)
        return reduce(operator.add, ranges)

    def __sub__(self, other):
        if not isinstance(other, (GTIDRangeList, GTIDRange)):
            raise TypeError('Cannot subtract {cls} from GTIDRangeList'.format(cls=type(other)))

        if isinstance(other, GTIDRangeList) and other == self:
            return GTIDRangeList()

        ranges = []
        for r in self:
            if isinstance(other, GTIDRangeList):
                ranges += reduce(operator.sub, other.ranges, r)
            else:
                ranges += r - other

        return GTIDRangeList(*ranges)

    def __hash__(self):
        return hash(tuple(self.ranges))

    def _append(self, item):
        # This method is meant to be used only if the item is really at the end of the list
        # RangeList should always be sorted
        trail = self.ranges.pop()
        if trail > item:
            raise ValueError('{item} is less than {trail}. Cannot append.'.format(
                item=item,
                trail=trail,
            ))

        for r in trail + item:
            self.ranges.append(r)

        return self

    def count(self):
        return sum([len(r) for r in self])

    @staticmethod
    def parse(ranges):
        """ Parses GTID range list of instances GTIDRanges, tuples os strings
        :param ranges: list of GTIDRanges, tuples or strings
        :return: generator

        > list(GTIDRangeList.parse(['1-200:202:207-251'))
        [<GTIDRange:1-200>, <GTIDRange:202>, <GTIDRange:207-251>]
        """
        if not ranges:
            return

        if isinstance(ranges, str):
            ranges = ranges.split(':')

        for r in ranges:
            if isinstance(r, GTIDRange):
                yield r
            elif isinstance(r, tuple):
                yield GTIDRange(*r)
            elif isinstance(r, str):
                yield GTIDRange(r)


class GTIDSet(object):

    def __init__(self, sources):
        self.sets = self.parse(gtid_set=sources)

    def __str__(self):
        return ',\n'.join(['{uuid}:{ranges}'.format(uuid=u, ranges=r) for u, r in sorted(self.sets.items())])

    def __repr__(self):
        return '<GTIDSet:{s}>'.format(s=str(self))

    def __iter__(self):
        for uuid, ranges in self.sets.items():
            yield uuid, ranges

    def __bool__(self):
        return bool(self.sets)

    __nonzero__ = __bool__

    def __getitem__(self, item):
        return self.sets[item]

    def __setitem__(self, key, value):
        self.sets[key] = value

    def __eq__(self, other):
        return self.sets == other.sets

    def __add__(self, other):
        gs = GTIDSet('')
        for uuid in set(self.sets.keys()).union(set(other.sets.keys())):
            s = self.sets.get(uuid, GTIDRangeList()) + other.sets.get(uuid, GTIDRangeList())
            if s:
                gs[uuid] = s

        return gs

    def __sub__(self, other):
        gs = GTIDSet('')
        for uuid, ranges in self:
            residues = ranges - other[uuid] if other.has(uuid) else ranges
            if residues:
                gs[uuid] = residues

        return gs

    def count(self):
        return sum([r.count() for _, r in self])

    def has(self, item):
        return item in self.sets

    @staticmethod
    def parse(gtid_set):
        """ Parses gtid set literal and returns dictionary where key is the uuid and values are GTIDRangeLists
        :param gtid_set: str
        :return: dictionary

        > GTIDSet.parse("84d15910-b6a4-11e4-af2c-080027880ca6:1,966073f3-b6a4-11e4-af2c-080027880ca6:1-29")
        {'84d15910-b6a4-11e4-af2c-080027880ca6': <GTIDRangeList:[1]>,
         '966073f3-b6a4-11e4-af2c-080027880ca6': <GTIDRangeList:[1-29]>}
        """
        _sets = {}
        for uuid, range_list in [s.split(':', 1) for s in map(lambda s: s.strip('\n '), gtid_set.split(',')) if s]:
            _sets[uuid] = GTIDRangeList(range_list)

        return _sets
