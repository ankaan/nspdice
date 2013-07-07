"""Combine dice and compute probabilities for the composite die, also allow rolling of such dice."""
from itertools import *
import operator
import random

class Die(object):
  """A generalized die."""

  def __init__(self,sides):
    """
    Create a die based on a liste of probabilities where the index is the outcome or a fair die with the given number of sides.
    """

    self._normalized = False
    self._reach = None

    if type(sides) is list:
      if len(sides)==0:
        self._sides = [1.0]
      else:
        self._sides = sides
    elif type(sides) is int:
      if sides>=0:
        self._sides = [0.0] + [1.0/sides]*sides
      else:
        raise ValueError('If sides in an integer, it must be greater than 0')
    else:
      raise TypeError('Die.__init() either takes a list or an integer.')

  @classmethod
  def const(called_class,value):
    """
    Create a die that always shows a certain value.
    """
    if type(value) is not int:
      raise TypeError('Die.const() only takes an integer.')

    return called_class([0.0]*value + [1.0])

  def __add__(self,other):
    """
    Create a new composite die by adding two dice together.
    """

    if type(other) is not Die:
      raise TypeError('Only a die can be added to another die.')

    outcomes = [ (sv+ov,sp*op) for (sv,sp) in enumerate(self._sides)
                               for (ov,op) in enumerate(other._sides) ]

    sides = [0.0] + [0.0] * max([ v for (v,p) in outcomes ])
    for (v,p) in outcomes:
      sides[v] += p

    return Die(sides)

  def __eq__(self,other):
    self._normalize()
    other._normalize()
    return self._sides == other._sides

  def similar_to(self,other,ndigits=7):
    self._normalize()
    other._normalize()
    return all([ round(x-y,ndigits)==0.0 for (x,y) in
      zip(self._sides,other._sides) ])

  def duplicate(self,num):
    """Duplicate the die the given number of times."""
    return reduce(operator.add, [self]*num, Die.const(0))

  def _normalize(self):
    """Normalize probabilities."""
    if not self._normalized:
      total_probability = sum(self._sides)
      self._sides = [ s/total_probability for s in self._sides ]
      self._normalized = True

  def probability(self):
    """Get the probabilities for rolling the positional number."""
    self._normalize()
    return self._sides

  def _compute_reach(self):
    """Compute the probabilities to roll at least the positional number."""
    self._normalize()

    if self._reach is None:
      self._reach = []

      s = 1.0
      for w in self._sides:
        self._reach.append(s)
        s -= w

  def probability_reach(self):
    """Get the probabilities to roll at least the positional number."""
    self._compute_reach()
    return self._reach

  def probability_vs(self,opponent):
    """Compute probability to roll higher than opponent die."""
    # For each possible opponent outcome, compute the propability to reach at
    # least 1 more than that. Sum that up and we have the probability to beat
    # the opponent.
    return sum([ p*pr for (p,pr) in 
      zip(opponent.probability(), self.probability_reach()[1:]) ])

  def probability_eq(self,other):
    """Compute probability that two different die roll the same result."""
    return sum([ sp*op for (sp,op) in 
      zip(self.probability(),other.probability()) ])

  def roll(self,rnd=None):
    """Roll the die."""
    if rnd is None: 
      rnd = random.random()
    elif not (0.0 <= rnd < 1.0):
      raise ValueError("rnd must be in [0.0, 1.0)")
    for i, w in enumerate(self._sides):
      rnd -=w
      if rnd < 0:
        return i