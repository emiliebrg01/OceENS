"""Avancement des synthèses d'un sondage et temps restant estimé (EPF-MDE/OceENS#149).

Les dashboards demandent `progress(session, survey_id)` au lieu de compter
eux-mêmes dans la file `summaries`.
"""

from oceens.summary_progress._progress import SurveyProgress, progress

__all__ = ["SurveyProgress", "progress"]
