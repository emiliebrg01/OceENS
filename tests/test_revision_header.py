"""Chaque réponse nomme le commit dont l'image a été construite.

Le déploiement attend un 200 portant le commit qu'il vient de déployer : sans
cet en-tête, un 200 de l'image précédente, encore servie pendant le démarrage
de la nouvelle, le ferait passer à tort.
"""

import asyncio

from oceens import main


def get(app, path):
    """Une requête GET sur `app` : son statut et ses en-têtes."""
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": [(b"host", b"oceens.example")],
        "client": ("testclient", 50000),
        "server": ("oceens.example", 80),
    }
    sent = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    asyncio.run(app(scope, receive, send))
    start = sent[0]
    headers = {k.decode().lower(): v.decode() for k, v in start["headers"]}
    return start["status"], headers


def test_every_answer_names_the_revision(monkeypatch):
    monkeypatch.setattr(main, "REVISION", "abc123")
    app = main.create_app()

    page_status, page_headers = get(app, "/static/css/theme.css")
    redirect_status, redirect_headers = get(app, "/une-page-qui-n-existe-pas")

    assert page_status == 200
    assert page_headers["x-revision"] == "abc123"
    assert redirect_status == 303
    assert redirect_headers["x-revision"] == "abc123"
