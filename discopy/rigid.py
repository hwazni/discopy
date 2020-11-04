# -*- coding: utf-8 -*-

"""
Implements the free rigid monoidal category.

The objects are given by the free pregroup, the arrows by planar diagrams.

>>> unit, s, n = Ty(), Ty('s'), Ty('n')
>>> t = n.r @ s @ n.l
>>> assert t @ unit == t == unit @ t
>>> assert t.l.r == t == t.r.l
>>> left_snake, right_snake = Id(n.r).transpose(left=True), Id(n.l).transpose()
>>> assert left_snake.normal_form() == Id(n) == right_snake.normal_form()
"""

from discopy import cat, monoidal, messages
from discopy.cat import AxiomError


class Ob(cat.Ob):
    """
    Implements simple pregroup types: basic types and their iterated adjoints.

    >>> a = Ob('a')
    >>> assert a.l.r == a.r.l == a and a != a.l.l != a.r.r
    """
    @property
    def z(self):
        """ Winding number """
        return self._z

    @property
    def l(self):
        """ Left adjoint """
        return Ob(self.name, self.z - 1)

    @property
    def r(self):
        """ Right adjoint """
        return Ob(self.name, self.z + 1)

    def __init__(self, name, z=0):
        if not isinstance(z, int):
            raise TypeError(messages.type_err(int, z))
        self._z = z
        super().__init__(name)

    def __eq__(self, other):
        if not isinstance(other, Ob):
            if isinstance(other, cat.Ob):
                return self.z == 0 and self.name == other.name
            return False
        return (self.name, self.z) == (other.name, other.z)

    def __hash__(self):
        return hash(self.name if not self.z else (self.name, self.z))

    def __repr__(self):
        return "Ob({}{})".format(
            repr(self.name), ", z=" + repr(self.z) if self.z else '')

    def __str__(self):
        return str(self.name) + (
            - self.z * '.l' if self.z < 0 else self.z * '.r')


class Ty(monoidal.Ty, Ob):
    """ Implements pregroup types as lists of simple types.

    >>> s, n = Ty('s'), Ty('n')
    >>> assert n.l.r == n == n.r.l
    >>> assert (s @ n).l == n.l @ s.l and (s @ n).r == n.r @ s.r
    """
    @staticmethod
    def upgrade(typ):
        return Ty(*typ.objects)

    @property
    def l(self):
        return Ty(*[x.l for x in self.objects[::-1]])

    @property
    def r(self):
        return Ty(*[x.r for x in self.objects[::-1]])

    @property
    def z(self):
        if len(self) != 1:
            raise TypeError(messages.no_winding_number_for_complex_types())
        return self[0].z

    def __init__(self, *t):
        t = [x if isinstance(x, Ob)
             else Ob(x.name) if isinstance(x, cat.Ob)
             else Ob(x) for x in t]
        monoidal.Ty.__init__(self, *t)
        Ob.__init__(self, str(self))

    def __repr__(self):
        return "Ty({})".format(', '.join(
            repr(x if x.z else x.name) for x in self.objects))

    def __lshift__(self, other):
        return self @ other.l

    def __rshift__(self, other):
        return self.r @ other


class PRO(monoidal.PRO, Ty):
    """
    Objects of the free rigid monoidal category generated by 1.
    """
    @staticmethod
    def upgrade(typ):
        return PRO(len(monoidal.PRO.upgrade(typ)))

    @property
    def l(self):
        """
        >>> assert PRO(2).l == PRO(2)
        """
        return self

    @property
    def r(self):
        return self


class Diagram(monoidal.Diagram):
    """ Implements diagrams in the free rigid monoidal category.

    >>> I, n, s = Ty(), Ty('n'), Ty('s')
    >>> Alice, jokes = Box('Alice', I, n), Box('jokes', I, n.r @ s)
    >>> boxes, offsets = [Alice, jokes, Cup(n, n.r)], [0, 1, 0]
    >>> print(Diagram(Alice.dom @ jokes.dom, s, boxes, offsets))
    Alice >> Id(n) @ jokes >> Cup(n, n.r) @ Id(s)
    """
    @staticmethod
    def upgrade(diagram):
        """
        Takes a monoidal.Diagram and returns a rigid.Diagram.
        """
        return Diagram(Ty(*diagram.dom), Ty(*diagram.cod),
                       diagram.boxes, diagram.offsets, layers=diagram.layers)

    @staticmethod
    def id(dom):
        return Id(dom)

    @staticmethod
    def swap(left, right):
        return monoidal.swap(
            left, right, ar_factory=Diagram, swap_factory=Swap)

    @staticmethod
    def permutation(perm, dom=None):
        if dom is None:
            dom = PRO(len(perm))
        return monoidal.permutation(perm, dom, ar_factory=Diagram)

    def foliate(self, yield_slices=False):
        """
        >>> x = Ty('x')
        >>> f = Box('f', x, x)
        >>> gen = (f @ Id(x) >> (f @ f)).foliate()
        >>> print(next(gen))
        f @ Id(x) >> Id(x) @ f >> f @ Id(x)
        """
        for diagram in super().foliate(yield_slices=yield_slices):
            if isinstance(diagram, cat.Arrow):
                yield self.upgrade(diagram)
            else:
                yield [self.upgrade(diagram[i]) for i in range(len(diagram))]

    @staticmethod
    def cups(left, right):
        """ Constructs nested cups witnessing adjointness of x and y.

        >>> a, b = Ty('a'), Ty('b')
        >>> assert Diagram.cups(a, a.r) == Cup(a, a.r)
        >>> assert Diagram.cups(a @ b, (a @ b).r) ==\\
        ...     Id(a) @ Cup(b, b.r) @ Id(a.r) >> Cup(a, a.r)
        """
        return cups(left, right)

    @staticmethod
    def caps(left, right):
        """ Constructs nested cups witnessing adjointness of x and y.

        >>> a, b = Ty('a'), Ty('b')
        >>> assert Diagram.caps(a, a.l) == Cap(a, a.l)
        >>> assert Diagram.caps(a @ b, (a @ b).l) == (Cap(a, a.l)
        ...                 >> Id(a) @ Cap(b, b.l) @ Id(a.l))
        """
        return caps(left, right)

    @staticmethod
    def fa(left, right):
        """ Forward application. """
        off = -len(right) or len(left)
        return Id(left[:off]) @ Diagram.cups(left[off:], right)

    @staticmethod
    def ba(left, right):
        """ Backward application. """
        off = -len(left) or len(right)
        return Diagram.cups(left, right[:off]) @ Id(right[off:])

    @staticmethod
    def fc(left, middle, right):
        """ Forward composition. """
        return Id(left) @ Diagram.cups(middle.l, middle) @ Id(right.l)

    @staticmethod
    def curry(diagram, n_wires=1, left=False):
        """ Diagram currying. """
        if left:
            wires = diagram.dom[:n_wires]
            return Diagram.caps(wires.r, wires) @ Id(diagram.dom[n_wires:])\
                >> Id(wires.r) @ diagram
        wires = diagram.dom[-n_wires or len(diagram.dom):]
        return Id(diagram.dom[:-n_wires]) @ Diagram.caps(wires, wires.l)\
            >> diagram @ Id(wires.l)

    def transpose(self, left=False):
        """
        >>> a, b = Ty('a'), Ty('b')
        >>> double_snake = Id(a @ b).transpose()
        >>> two_snakes = Id(b).transpose() @ Id(a).transpose()
        >>> double_snake == two_snakes
        False
        >>> *_, two_snakes_nf = monoidal.Diagram.normalize(two_snakes)
        >>> assert double_snake == two_snakes_nf
        >>> f = Box('f', a, b)

        >>> a, b = Ty('a'), Ty('b')
        >>> double_snake = Id(a @ b).transpose(left=True)
        >>> snakes = Id(b).transpose(left=True) @ Id(a).transpose(left=True)
        >>> double_snake == two_snakes
        False
        >>> *_, two_snakes_nf = monoidal.Diagram.normalize(
        ...     snakes, left=True)
        >>> assert double_snake == two_snakes_nf
        >>> f = Box('f', a, b)
        """
        if left:
            return self.id(self.cod.l) @ self.caps(self.dom, self.dom.l)\
                >> self.id(self.cod.l) @ self @ self.id(self.dom.l)\
                >> self.cups(self.cod.l, self.cod) @ self.id(self.dom.l)
        return self.caps(self.dom.r, self.dom) @ self.id(self.cod.r)\
            >> self.id(self.dom.r) @ self @ self.id(self.cod.r)\
            >> self.id(self.dom.r) @ self.cups(self.cod, self.cod.r)

    def normalize(self, left=False):
        """
        Return a generator which yields normalization steps.

        >>> n, s = Ty('n'), Ty('s')
        >>> cup, cap = Cup(n, n.r), Cap(n.r, n)
        >>> f, g, h = Box('f', n, n), Box('g', s @ n, n), Box('h', n, n @ s)
        >>> diagram = g @ cap >> f[::-1] @ Id(n.r) @ f >> cup @ h
        >>> for d in diagram.normalize(): print(d)  # doctest: +ELLIPSIS
        g... >> Cup(n, n.r) @ Id(n)...
        g >> f[::-1] >> Id(n) @ Cap(n.r, n) >> Cup(n, n.r) @ Id(n) >> f >> h
        g >> f[::-1] >> f >> h
        """
        def follow_wire(diagram, i, j):
            """
            Given a diagram, the index of a box i and the offset j of an output
            wire, returns (i, j, obstructions) where:
            - i is the index of the box which takes this wire as input, or
            len(diagram) if it is connected to the bottom boundary.
            - j is the offset of the wire at its bottom end.
            - obstructions is a pair of lists of indices for the boxes on
            the left and right of the wire we followed.
            """
            left_obstruction, right_obstruction = [], []
            while i < len(diagram) - 1:
                i += 1
                box, off = diagram.boxes[i], diagram.offsets[i]
                if off <= j < off + len(box.dom):
                    return i, j, (left_obstruction, right_obstruction)
                if off <= j:
                    j += len(box.cod) - len(box.dom)
                    left_obstruction.append(i)
                else:
                    right_obstruction.append(i)
            return len(diagram), j, (left_obstruction, right_obstruction)

        def find_snake(diagram):
            """
            Given a diagram, returns (cup, cap, obstructions, left_snake)
            if there is a yankable pair, otherwise returns None.
            """
            for cap in range(len(diagram)):
                if not isinstance(diagram.boxes[cap], Cap):
                    continue
                for left_snake, wire in [(True, diagram.offsets[cap]),
                                         (False, diagram.offsets[cap] + 1)]:
                    cup, wire, obstructions =\
                        follow_wire(diagram, cap, wire)
                    not_yankable =\
                        cup == len(diagram)\
                        or not isinstance(diagram.boxes[cup], Cup)\
                        or left_snake and diagram.offsets[cup] + 1 != wire\
                        or not left_snake and diagram.offsets[cup] != wire
                    if not_yankable:
                        continue
                    return cup, cap, obstructions, left_snake
            return None

        def unsnake(diagram, cup, cap, obstructions, left_snake=False):
            """
            Given a diagram and the indices for a cup and cap pair
            and a pair of lists of obstructions on the left and right,
            returns a new diagram with the snake removed.

            A left snake is one of the form Id @ Cap >> Cup @ Id.
            A right snake is one of the form Cap @ Id >> Id @ Cup.
            """
            left_obstruction, right_obstruction = obstructions
            if left_snake:
                for box in left_obstruction:
                    diagram = diagram.interchange(box, cap)
                    yield diagram
                    for i, right_box in enumerate(right_obstruction):
                        if right_box < box:
                            right_obstruction[i] += 1
                    cap += 1
                for box in right_obstruction[::-1]:
                    diagram = diagram.interchange(box, cup)
                    yield diagram
                    cup -= 1
            else:
                for box in left_obstruction[::-1]:
                    diagram = diagram.interchange(box, cup)
                    yield diagram
                    for i, right_box in enumerate(right_obstruction):
                        if right_box > box:
                            right_obstruction[i] -= 1
                    cup -= 1
                for box in right_obstruction:
                    diagram = diagram.interchange(box, cap)
                    yield diagram
                    cap += 1
            boxes = diagram.boxes[:cap] + diagram.boxes[cup + 1:]
            offsets = diagram.offsets[:cap] + diagram.offsets[cup + 1:]
            layers = diagram.layers[:cap] >> diagram.layers[cup + 1:]
            yield Diagram(diagram.dom, diagram.cod, boxes, offsets, layers)

        diagram = self
        while True:
            yankable = find_snake(diagram)
            if yankable is None:
                break
            for _diagram in unsnake(diagram, *yankable):
                yield _diagram
                diagram = _diagram
        for _diagram in monoidal.Diagram.normalize(diagram, left=left):
            yield _diagram

    def normal_form(self, normalize=None, **params):
        """
        Implements the normalisation of rigid monoidal categories,
        see arxiv:1601.05372, definition 2.12.
        """
        return super().normal_form(
            normalize=normalize or Diagram.normalize, **params)


class Id(monoidal.Id, Diagram):
    """ Define an identity arrow in a free rigid category

    >>> t = Ty('a', 'b', 'c')
    >>> assert Id(t) == Diagram(t, t, [], [])
    """
    def __init__(self, dom):
        monoidal.Id.__init__(self, dom)
        Diagram.__init__(self, dom, dom, [], [], layers=cat.Id(dom))


class Box(monoidal.Box, Diagram):
    """ Implements generators of rigid monoidal diagrams.

    >>> a, b = Ty('a'), Ty('b')
    >>> Box('f', a, b.l @ b, data={42})
    Box('f', Ty('a'), Ty(Ob('b', z=-1), 'b'), data={42})
    """
    def __init__(self, name, dom, cod, data=None, _dagger=False):
        monoidal.Box.__init__(self, name, dom, cod, data=data, _dagger=_dagger)
        Diagram.__init__(self, dom, cod, [self], [0], layers=self.layers)


class Swap(monoidal.Swap, Box):
    """ Implements swaps of basic types in a rigid category. """
    def __init__(self, left, right):
        monoidal.Swap.__init__(self, left, right)
        dom, cod = left @ right, right @ left
        Box.__init__(self, "Swap({}, {})".format(left, right), dom, cod)


class Cup(Box):
    """ Defines cups for simple types.

    >>> n = Ty('n')
    >>> Cup(n, n.r)
    Cup(Ty('n'), Ty(Ob('n', z=1)))
    """
    def __init__(self, left, right):
        if not isinstance(left, Ty):
            raise TypeError(messages.type_err(Ty, left))
        if not isinstance(right, Ty):
            raise TypeError(messages.type_err(Ty, right))
        if len(left) != 1 or len(right) != 1:
            raise ValueError(messages.cup_vs_cups(left, right))
        if left.r != right and left != right.r:
            raise AxiomError(messages.are_not_adjoints(left, right))
        if left == right.r:
            raise AxiomError(messages.wrong_adjunction(left, right, cup=True))
        self.left, self.right, self.draw_as_wire = left, right, True
        super().__init__("Cup({}, {})".format(left, right), left @ right, Ty())

    def dagger(self):
        return Cap(self.left, self.right)

    def __repr__(self):
        return "Cup({}, {})".format(repr(self.left), repr(self.right))


class Cap(Box):
    """ Defines cups for simple types.

    >>> n = Ty('n')
    >>> Cap(n, n.l)
    Cap(Ty('n'), Ty(Ob('n', z=-1)))
    """
    def __init__(self, left, right):
        if not isinstance(left, Ty):
            raise TypeError(messages.type_err(Ty, left))
        if not isinstance(right, Ty):
            raise TypeError(messages.type_err(Ty, right))
        if len(left) != 1 or len(right) != 1:
            raise ValueError(messages.cap_vs_caps(left, right))
        if left != right.r and left.r != right:
            raise AxiomError(messages.are_not_adjoints(left, right))
        if left.r == right:
            raise AxiomError(messages.wrong_adjunction(left, right, cup=False))
        self.left, self.right, self.draw_as_wire = left, right, True
        super().__init__("Cap({}, {})".format(left, right), Ty(), left @ right)

    def dagger(self):
        return Cup(self.left, self.right)

    def __repr__(self):
        return "Cap({}, {})".format(repr(self.left), repr(self.right))


class Functor(monoidal.Functor):
    """
    Implements rigid monoidal functors, i.e. preserving cups and caps.

    >>> s, n = Ty('s'), Ty('n')
    >>> Alice, Bob = Box("Alice", Ty(), n), Box("Bob", Ty(), n)
    >>> loves = Box('loves', Ty(), n.r @ s @ n.l)
    >>> love_box = Box('loves', n @ n, s)
    >>> ob = {s: s, n: n}
    >>> ar = {Alice: Alice, Bob: Bob}
    >>> ar.update({loves: Cap(n.r, n) @ Cap(n, n.l)
    ...                   >> Id(n.r) @ love_box @ Id(n.l)})
    >>> F = Functor(ob, ar)
    >>> sentence = Alice @ loves @ Bob >> Cup(n, n.r) @ Id(s) @ Cup(n.l, n)
    >>> assert F(sentence).normal_form() == Alice >> Id(n) @ Bob >> love_box
    """
    def __init__(self, ob, ar, ob_factory=Ty, ar_factory=Diagram):
        super().__init__(ob, ar, ob_factory=ob_factory, ar_factory=ar_factory)

    def __call__(self, diagram):
        if isinstance(diagram, monoidal.Ty):
            def adjoint(obj):
                result = self.ob[type(diagram)(type(obj)(obj.name, z=0))]
                if obj.z < 0:
                    for _ in range(-obj.z):
                        result = result.l
                elif obj.z > 0:
                    for _ in range(obj.z):
                        result = result.r
                return result
            return self.ob_factory().tensor(*map(adjoint, diagram.objects))
        if isinstance(diagram, Cup):
            return self.ar_factory.cups(
                self(diagram.dom[:1]), self(diagram.dom[1:]))
        if isinstance(diagram, Cap):
            return self.ar_factory.caps(
                self(diagram.cod[:1]), self(diagram.cod[1:]))
        if isinstance(diagram, monoidal.Diagram):
            return super().__call__(diagram)
        raise TypeError(messages.type_err(Diagram, diagram))


def cups(left, right, ar_factory=Diagram, cup_factory=Cup, reverse=False):
    """ Constructs a diagram of nested cups. """
    for typ in left, right:
        if not isinstance(typ, Ty):
            raise TypeError(messages.type_err(Ty, typ))
    if left.r != right and right.r != left:
        raise AxiomError(messages.are_not_adjoints(left, right))
    result = ar_factory.id(left @ right)
    for i in range(len(left)):
        j = len(left) - i - 1
        cup = cup_factory(left[j:j + 1], right[i:i + 1])
        layer = ar_factory.id(left[:j]) @ cup @ ar_factory.id(right[i + 1:])
        result = result << layer if reverse else result >> layer
    return result


def caps(left, right, ar_factory=Diagram, cap_factory=Cap):
    """ Constructs a diagram of nested caps. """
    return cups(left, right, ar_factory, cap_factory, reverse=True)
