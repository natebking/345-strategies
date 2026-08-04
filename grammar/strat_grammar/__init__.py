"""The Strat grammar: precise definitions of TheStrat's price action states.

The whole model is one tuple per candle. Everything else is a projection of it:

    >>> from strat_grammar import Candle, classify
    >>> prior = Candle(open=100, high=110, low=90, close=105)
    >>> current = Candle(open=106, high=115, low=95, close=101)
    >>> state = classify(current, prior)
    >>> state.structure
    <Structure.TWO_UP: '2u'>
    >>> state.above_open
    False
    >>> state.failed          # closed back inside the prior range
    True
    >>> state.notation()
    'F2u'

Structure and sign are orthogonal. A 2u can close red; that is what `failed`
is for. See SPEC.md for the definitions this implements.
"""

from .model import Candle, Structure, State, FailedMethod, PatternMethod, Continuity
from .classify import classify, structure_of, is_failed
from .patterns import is_hammer, is_shooter
from .continuity import continuity
from .combos import combo

__version__ = "0.1.0"

__all__ = [
    "Candle",
    "Structure",
    "State",
    "FailedMethod",
    "PatternMethod",
    "Continuity",
    "classify",
    "structure_of",
    "is_failed",
    "is_hammer",
    "is_shooter",
    "continuity",
    "combo",
]
