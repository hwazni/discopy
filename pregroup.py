# -*- coding: utf-8 -*-

"""
Implements disco models in the category of matrices and circuits.

>>> s, n = Ty('s'), Ty('n')
>>> Alice, Bob = Word('Alice', n), Word('Bob', n)
>>> loves = Word('loves', n.r @ s @ n.l)
>>> grammar = Cup(n, n.r) @ Id(s) @ Cup(n.l, n)
>>> sentence = grammar << Alice @ loves @ Bob
>>> ob = {s: 1, n: 2}
>>> ar = {Alice: [1, 0], loves: [0, 1, 1, 0], Bob: [0, 1]}
>>> F = Model(ob, ar)
>>> assert F(sentence) == True
"""

from functools import reduce as fold
import matplotlib.pyplot as plt
from matplotlib.path import Path
from matplotlib.patches import PathPatch

from discopy import config, rigidcat
from discopy.rigidcat import Ty, Box, Id, Cup
from discopy.matrix import MatrixFunctor
from discopy.circuit import CircuitFunctor


class Word(Box):
    """ Implements words as boxes with a pregroup type as codomain.

    >>> Alice = Word('Alice', Ty('n'))
    >>> loves = Word('loves',
    ...     Ty('n').r @ Ty('s') @ Ty('n').l)
    >>> Alice
    Word('Alice', Ty('n'))
    >>> loves
    Word('loves', Ty(Ob('n', z=1), 's', Ob('n', z=-1)))
    """
    def __init__(self, w, t, _dagger=False):
        """
        >>> Word('Alice', Ty('n'))
        Word('Alice', Ty('n'))
        """
        if not isinstance(w, str):
            raise TypeError(config.Msg.type_err(str, w))
        if not isinstance(t, Ty):
            raise TypeError(config.Msg.type_err(Ty, t))
        self._word, self._type = w, t
        dom, cod = (t, Ty()) if _dagger else (Ty(), t)
        Box.__init__(self, (w, t), dom, cod, _dagger=_dagger)

    def dagger(self):
        """
        >>> Word('Alice', Ty('n')).dagger()
        Word('Alice', Ty('n')).dagger()
        """
        return Word(self._word, self._type, not self._dagger)

    @property
    def word(self):
        """
        >>> Word('Alice', Ty('n')).word
        'Alice'
        """
        return self._word

    @property
    def type(self):
        """
        >>> Word('Alice', Ty('n')).type
        Ty('n')
        """
        return self._type

    def __repr__(self):
        """
        >>> Word('Alice', Ty('n'))
        Word('Alice', Ty('n'))
        >>> Word('Alice', Ty('n')).dagger()
        Word('Alice', Ty('n')).dagger()
        """
        return "Word({}, {}){}".format(repr(self.word), repr(self.type),
                                       ".dagger()" if self._dagger else "")

    def __str__(self):
        """
        >>> print(Word('Alice', Ty('n')))
        Alice
        """
        return str(self.word)


class Model(MatrixFunctor):
    """ Implements functors from pregroup grammars to matrices.

    >>> n, s = Ty('n'), Ty('s')
    >>> Alice, jokes = Word('Alice', n), Word('jokes', n.r @ s)
    >>> F = Model({s: 1, n: 2}, {Alice: [0, 1], jokes: [1, 1]})
    >>> assert F(Alice @ jokes >> Cup(n, n.r) @ Id(s))
    """
    def __repr__(self):
        """
        >>> Model({}, {Word('Alice', Ty('n')): [0, 1]})
        Model(ob={}, ar={Word('Alice', Ty('n')): [0, 1]})
        """
        return super().__repr__().replace("MatrixFunctor", "Model")


class CircuitModel(CircuitFunctor):
    """
    >>> from discopy.circuit import sqrt, H, X, Ket, CX
    >>> s, n = Ty('s'), Ty('n')
    >>> Alice = Word('Alice', n)
    >>> loves = Word('loves', n.r @ s @ n.l)
    >>> Bob = Word('Bob', n)
    >>> grammar = Cup(n, n.r) @ Id(s) @ Cup(n.l, n)
    >>> sentence = grammar << Alice @ loves @ Bob
    >>> ob = {s: 0, n: 1}
    >>> ar = {Alice: Ket(0),
    ...       loves: CX << sqrt(2) @ H @ X << Ket(0, 0),
    ...       Bob: Ket(1)}
    >>> F = CircuitModel(ob, ar)
    >>> BornRule = lambda c: abs(c.eval().array) ** 2
    >>> assert BornRule(F(sentence))
    """
    def __repr__(self):
        """
        >>> from discopy.circuit import Ket
        >>> CircuitModel({Ty('n'): 1}, {Word('Alice', Ty('n')): Ket(0)})
        CircuitModel(ob={Ty('n'): 1}, ar={Word('Alice', Ty('n')): Ket(0)})
        """
        return super().__repr__().replace("CircuitFunctor", "CircuitModel")


def eager_parse(*words, target=Ty('s')):
    """
    Tries to parse a given list of words in an eager fashion.
    """
    result = fold(lambda x, y: x @ y, words)
    scan = result.cod
    while True:
        fail = True
        for i in range(len(scan) - 1):
            if scan[i: i + 1].r != scan[i + 1: i + 2]:
                continue
            cup = Cup(scan[i: i + 1], scan[i + 1: i + 2])
            result = result >> Id(scan[: i]) @ cup @ Id(scan[i + 2:])
            scan, fail = result.cod, False
            break
        if result.cod == target:
            return result
        if fail:
            raise NotImplementedError


def brute_force(*vocab, target=Ty('s')):
    """
    Given a vocabulary, search for grammatical sentences.
    """
    test = [()]
    for words in test:
        for word in vocab:
            try:
                yield eager_parse(*(words + (word, )), target=target)
            except NotImplementedError:
                pass
            test.append(words + (word, ))


def draw(diagram, draw_types=False):  # pragma: no cover
    """
    Draws a pregroup diagram.
    """
    words, *cups = diagram.slice().boxes
    is_pregroup = all(isinstance(box, Word) for box in words.boxes)\
        and all(isinstance(box, Cup) for s in cups for box in s.boxes)
    if not is_pregroup:
        return diagram.draw()
    fig, ax = plt.subplots()
    words, scan = words.normal_form(), []
    for i, (word, off) in enumerate(zip(words.boxes, words.offsets)):
        for j, _ in enumerate(word.cod):
            scan.append(3 * i + (2. / (len(word.cod) + 1)) * (j + 1))
            if draw_types:
                ax.text(scan[-1] + .1, -.2, str(word.cod[j]))
        verts = [(3 * i, 0),
                 (3 * i + 2, 0),
                 (3 * i + 1, 1),
                 (3 * i, 0)]
        codes = [Path.MOVETO, Path.LINETO, Path.LINETO, Path.CLOSEPOLY]
        ax.add_patch(PathPatch(Path(verts, codes), facecolor='none'))
        ax.text(3 * i + 1, .1, str(word), ha='center')
    for j, slice in enumerate(cups):
        for off in slice.offsets:
            middle = .5 * (scan[off] + scan[off + 1])
            verts = [(scan[off], 0),
                     (scan[off], - j - 1),
                     (middle, - j - 1)]
            codes = [Path.MOVETO, Path.CURVE3, Path.CURVE3]
            ax.add_patch(PathPatch(Path(verts, codes), facecolor='none'))
            verts = [(middle, - j - 1),
                     (scan[off + 1], - j - 1),
                     (scan[off + 1], 0)]
            codes = [Path.MOVETO, Path.CURVE3, Path.CURVE3]
            ax.add_patch(PathPatch(Path(verts, codes), facecolor='none'))
            scan = scan[:off] + scan[off + 2:]
    for i, _ in enumerate(diagram.cod):
        verts = [(scan[i], 0), (scan[i], - len(cups) - 1)]
        codes = [Path.MOVETO, Path.LINETO]
        ax.add_patch(PathPatch(Path(verts, codes)))
        if draw_types:
            ax.text(scan[i] + .1, - len(cups) - 1, str(diagram.cod[i]))
    ax.set_xlim(0, 3 * len(words.boxes) - 1)
    ax.set_ylim(- len(cups) - 1, 1)
    ax.set_aspect('equal')
    plt.axis('off')
    plt.show()
