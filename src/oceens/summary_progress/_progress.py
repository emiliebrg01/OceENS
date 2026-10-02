"""Avancement des synthèses d'un sondage, lu dans la file `summaries`.

La table `summaries` est la file d'attente du daemon : `http_status` à 0 reste
à traiter, 200 est fait, toute autre valeur est un échec que le daemon ne
retente jamais. Ce module est le seul à connaître cette convention pour
l'affichage : les dashboards et le template lisent `SurveyProgress`.
"""

from dataclasses import dataclass

from sqlmodel import Session, case, func, select

from oceens.models import Summary

_PENDING = 0
_DONE = 200

# Hypothèse B du Design Document (EPF-MDE/OceENS#121) : durée typique d'un job,
# mesurée le 25 septembre 2026.
_SECONDS_PER_JOB = 20


@dataclass(frozen=True)
class SurveyProgress:
    """Où en sont les synthèses d'un sondage.

    `done + errors + pending == total`. `finished` : au moins un job, et aucun
    en attente. `estimated_seconds_left` vaut 0 une fois le sondage terminé.
    """

    done: int
    total: int
    errors: int
    estimated_seconds_left: int
    finished: bool


def progress(
    session: Session, survey_id: int, seconds_per_job: int = _SECONDS_PER_JOB
) -> SurveyProgress:
    """Avancement des synthèses de `survey_id` et temps restant estimé.

    L'estimation compte tous les jobs en attente de la file, de tous les
    sondages : le daemon les prend sans ordre, donc le dernier job de ce
    sondage peut passer après tous les autres. Ni horloge, ni appel au modèle.
    """
    if seconds_per_job <= 0:
        raise ValueError(f"seconds_per_job doit être positif, reçu {seconds_per_job}")

    total, done, pending = session.exec(
        select(
            func.count(Summary.summary_id),
            func.coalesce(func.sum(case((Summary.http_status == _DONE, 1), else_=0)), 0),
            func.coalesce(func.sum(case((Summary.http_status == _PENDING, 1), else_=0)), 0),
        ).where(Summary.survey_id == survey_id)
    ).one()

    if pending == 0:
        estimated_seconds_left = 0
    else:
        queue_pending = session.exec(
            select(func.count(Summary.summary_id)).where(Summary.http_status == _PENDING)
        ).one()
        estimated_seconds_left = queue_pending * seconds_per_job

    return SurveyProgress(
        done=done,
        total=total,
        errors=total - done - pending,
        estimated_seconds_left=estimated_seconds_left,
        finished=total > 0 and pending == 0,
    )
