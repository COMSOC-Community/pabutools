"""
Module introducing different ways to approximate the voters' satisfaction given their ballots. See the :py:mod:`~pabutools.election.ballot` module for more details on the ballots.

This module introduces general ways to define satisfaction measures together with a large set of already implemented
satisfaction measures.

First thing first, two abstract classes define satisfaction measures:

* :py:class:`~pabutools.election.satisfaction.satisfactionmeasure.SatisfactionMeasure` for individual satisfaction measures;
* :py:class:`~pabutools.election.satisfaction.satisfactionmeasure.GroupSatisfactionMeasure` for group satisfaction measures, i.e., satisfaction profiles.

As is the case for the profiles (see the module :py:mod:`~pabutools.election.profile`), we introduce satisfaction
profiles---in the class :py:class:`~pabutools.election.satisfaction.satisfactionprofile.SatisfactionProfile`---and
satisfaction multiprofiles---in the class
:py:class:`~pabutools.election.satisfaction.satisfactionprofile.SatisfactionMultiProfile`.

Individual satisfaction measures are defined according to three different classes:

* :py:class:`~pabutools.election.satisfaction.functionalsatisfaction.FunctionalSatisfaction` for generic satisfaction measures defined through a function;
* :py:class:`~pabutools.election.satisfaction.additivesatisfaction.AdditiveSatisfaction` for satisfaction measures that can be defined as the sum of a function over projects;
* :py:class:`~pabutools.election.satisfaction.positionalsatisfaction.PositionalSatisfaction` for satisfaction measures defined based on the position of the projects in an ordering.

The following satisfaction measures have already been implemented. Note that they do not apply to all types of ballots.

.. list-table::
   :widths: 25 25 25 25
   :header-rows: 1

   * - Satisfaction Measure
     - Class
     - Type
     - Ballot Type
   * - Chamberlin-Courant
     - :py:class:`~pabutools.election.satisfaction.functionalsatisfaction.CC_Sat`
     - :py:class:`~pabutools.election.satisfaction.functionalsatisfaction.FunctionalSatisfaction`
     - :py:class:`~pabutools.election.ballot.approvalballot.AbstractApprovalBallot` :py:class:`~pabutools.election.ballot.cardinalballot.AbstractCardinalBallot`
   * - Cost
     - :py:class:`~pabutools.election.satisfaction.additivesatisfaction.Cost_Sat`
     - :py:class:`~pabutools.election.satisfaction.additivesatisfaction.AdditiveSatisfaction`
     - all
   * - Relative Cost
     - :py:class:`~pabutools.election.satisfaction.additivesatisfaction.Relative_Cost_Sat`
     - :py:class:`~pabutools.election.satisfaction.additivesatisfaction.AdditiveSatisfaction`
     - all
   * - Approx Normaliser Relative Cost
     - :py:class:`~pabutools.election.satisfaction.additivesatisfaction.Relative_Cost_Approx_Normaliser_Sat`
     - :py:class:`~pabutools.election.satisfaction.additivesatisfaction.AdditiveSatisfaction`
     - all
   * - Cost Square Root
     - :py:class:`~pabutools.election.satisfaction.functionalsatisfaction.Cost_Sqrt_Sat`
     - :py:class:`~pabutools.election.satisfaction.functionalsatisfaction.FunctionalSatisfaction`
     - :py:class:`~pabutools.election.ballot.approvalballot.AbstractApprovalBallot`
   * - Additive Cost Square Root
     - :py:class:`~pabutools.election.satisfaction.additivesatisfaction.Additive_Cost_Sqrt_Sat`
     - :py:class:`~pabutools.election.satisfaction.additivesatisfaction.AdditiveSatisfaction`
     - :py:class:`~pabutools.election.ballot.approvalballot.AbstractApprovalBallot`
   * - Cost Log
     - :py:class:`~pabutools.election.satisfaction.functionalsatisfaction.Cost_Log_Sat`
     - :py:class:`~pabutools.election.satisfaction.functionalsatisfaction.FunctionalSatisfaction`
     - :py:class:`~pabutools.election.ballot.approvalballot.AbstractApprovalBallot`
   * - Additive Cost Log
     - :py:class:`~pabutools.election.satisfaction.additivesatisfaction.Additive_Cost_Log_Sat`
     - :py:class:`~pabutools.election.satisfaction.additivesatisfaction.AdditiveSatisfaction`
     - :py:class:`~pabutools.election.ballot.approvalballot.AbstractApprovalBallot`
   * - Cardinality
     - :py:class:`~pabutools.election.satisfaction.additivesatisfaction.Cardinality_Sat`
     - :py:class:`~pabutools.election.satisfaction.additivesatisfaction.AdditiveSatisfaction`
     - all
   * - Relative Cardinality
     - :py:class:`~pabutools.election.satisfaction.additivesatisfaction.Relative_Cardinality_Sat`
     - :py:class:`~pabutools.election.satisfaction.additivesatisfaction.AdditiveSatisfaction`
     - all
   * - Effort
     - :py:class:`~pabutools.election.satisfaction.additivesatisfaction.Effort_Sat`
     - :py:class:`~pabutools.election.satisfaction.additivesatisfaction.AdditiveSatisfaction`
     - :py:class:`~pabutools.election.ballot.approvalballot.AbstractApprovalBallot`
   * - Additive for Cardinal Ballots
     - :py:class:`~pabutools.election.satisfaction.additivesatisfaction.Additive_Cardinal_Sat`
     - :py:class:`~pabutools.election.satisfaction.additivesatisfaction.AdditiveSatisfaction`
     - :py:class:`~pabutools.election.ballot.cardinalballot.AbstractCardinalBallot`
   * - Relative Additive for Cardinal Ballots
     - :py:class:`~pabutools.election.satisfaction.additivesatisfaction.Additive_Cardinal_Relative_Sat`
     - :py:class:`~pabutools.election.satisfaction.additivesatisfaction.AdditiveSatisfaction`
     - :py:class:`~pabutools.election.ballot.cardinalballot.AbstractCardinalBallot`
   * - Additive Borda
     - :py:class:`~pabutools.election.satisfaction.positionalsatisfaction.Additive_Borda_Sat`
     - :py:class:`~pabutools.election.satisfaction.positionalsatisfaction.PositionalSatisfaction`
     - :py:class:`~pabutools.election.ballot.ordinalballot.AbstractOrdinalBallot`
"""

from pabutools.election.satisfaction.satisfactionmeasure import (
    SatisfactionMeasure,
    GroupSatisfactionMeasure,
)
from pabutools.election.satisfaction.satisfactionprofile import (
    SatisfactionProfile,
    SatisfactionMultiProfile,
)
from pabutools.election.satisfaction.additivesatisfaction import (
    AdditiveSatisfaction,
    Cost_Sat,
    Cardinality_Sat,
    Effort_Sat,
    Relative_Cost_Sat,
    Relative_Cardinality_Sat,
    Relative_Cost_Approx_Normaliser_Sat,
    Additive_Cost_Log_Sat,
    Additive_Cost_Sqrt_Sat,
    Additive_Cardinal_Sat,
    Additive_Cardinal_Relative_Sat,
)
from pabutools.election.satisfaction.functionalsatisfaction import (
    FunctionalSatisfaction,
    CC_Sat,
    Cost_Log_Sat,
    Cost_Sqrt_Sat,
)
from pabutools.election.satisfaction.positionalsatisfaction import (
    PositionalSatisfaction,
    Additive_Borda_Sat,
)

__all__ = [
    "SatisfactionMeasure",
    "GroupSatisfactionMeasure",
    "SatisfactionProfile",
    "SatisfactionMultiProfile",
    "AdditiveSatisfaction",
    "Cost_Sat",
    "Cardinality_Sat",
    "Effort_Sat",
    "Relative_Cost_Sat",
    "Relative_Cardinality_Sat",
    "Relative_Cost_Approx_Normaliser_Sat",
    "Additive_Cardinal_Sat",
    "Additive_Cardinal_Relative_Sat",
    "FunctionalSatisfaction",
    "CC_Sat",
    "Cost_Log_Sat",
    "Cost_Sqrt_Sat",
    "Additive_Cost_Log_Sat",
    "Additive_Cost_Sqrt_Sat",
    "PositionalSatisfaction",
    "Additive_Borda_Sat",
]
