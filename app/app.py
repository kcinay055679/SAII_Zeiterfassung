import os
import socket
import tempfile
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request

from store import (ACTIONS, LABELS, LOCAL_TZ, MAX_NAME, MAX_NOTE, ON_BREAK,
                   OUT, WORKING, InvalidInput, InvalidTransition, Store,
                   UnknownPerson)

NAME_COOKIE = "zeiterfassung_name"
STATUS_LABELS = {OUT: "AUSGESTEMPELT", WORKING: "EINGESTEMPELT", ON_BREAK: "IN PAUSE"}


def create_app(data_dir: str | os.PathLike | None = None) -> Flask:
    app = Flask(__name__)
    data_dir = Path(data_dir or os.getenv("DATA_DIR", "/data"))
    store = Store(data_dir / "zeiterfassung.db")
    store.init()
    pod = socket.gethostname()
    version = os.getenv("APP_VERSION", "dev")

    @app.after_request
    def security_headers(response):
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; style-src 'self'; script-src 'self'; form-action 'self'; "
            "frame-ancestors 'none'; base-uri 'none'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    def wants_json() -> bool:
        return request.is_json

    def payload():
        return (request.get_json(silent=True) or {}) if wants_json() else request.form

    def remember(response, name: str):
        response.set_cookie(NAME_COOKIE, name, max_age=60 * 60 * 24 * 365,
                            httponly=True, samesite="Lax")
        return response

    def render_index(error: str | None = None, status: int = 200):
        name = store.find_person(request.cookies.get(NAME_COOKIE, "")) or ""
        return render_template(
            "index.html",
            name=name,
            me=store.status_of(name) if name else None,
            people=store.people(),
            actions=ACTIONS,
            labels=LABELS,
            status_labels=STATUS_LABELS,
            board=store.board(),
            stamps=store.recent(),
            error=error,
            pod=pod,
            version=version,
            max_name=MAX_NAME,
            max_note=MAX_NOTE,
        ), status

    @app.get("/")
    def index():
        return render_index()

    @app.post("/person")
    def person():
        try:
            name, created = store.add_person(payload().get("name", ""))
        except InvalidInput as err:
            if wants_json():
                return jsonify(error=str(err)), 400
            return render_index(str(err), 400)
        if wants_json():
            return jsonify(name=name, created=created), 201 if created else 200
        return remember(redirect("/", code=303), name)

    @app.get("/people")
    def people():
        return jsonify(store.people())

    @app.post("/stamp")
    def stamp():
        data = payload()
        try:
            stamp = store.record(data.get("name", ""), data.get("action", ""),
                                 data.get("note", ""), pod=pod)
        except InvalidInput as err:
            if wants_json():
                return jsonify(error=str(err)), 400
            return render_index(str(err), 400)
        except UnknownPerson as err:
            if wants_json():
                return jsonify(error=str(err)), 404
            return render_index(str(err), 404)
        except InvalidTransition as err:
            if wants_json():
                return jsonify(error=str(err), status=err.status,
                               allowed=list(err.allowed)), 409
            return render_index(str(err), 409)

        if wants_json():
            return jsonify(stamp.as_dict()), 201
        return remember(redirect("/", code=303), stamp.person)

    @app.get("/events")
    def events():
        return jsonify([s.as_dict() for s in store.recent()])

    @app.get("/board")
    def board():
        return jsonify([
            {"person": p.person, "status": p.status, "worked_seconds": p.worked_seconds}
            for p in store.board()
        ])

    @app.get("/health")
    def health():
        # A bare 200 would stay green with a read-only or vanished /data, so the
        # probe writes to the volume and touches the database.
        try:
            # Unique name per call: readiness and liveness fire at the same moment.
            with tempfile.NamedTemporaryFile(dir=data_dir, prefix=".health-") as probe:
                probe.write(b"ok")
                probe.flush()
            store.ping()
        except Exception as err:
            app.logger.warning("health check failed: %s", err)
            return jsonify(status="unhealthy", error=str(err), pod=pod), 503
        return jsonify(status="healthy", pod=pod, version=version)

    @app.template_filter("duration")
    def duration(seconds: int) -> str:
        hours, rest = divmod(int(seconds), 3600)
        return f"{hours}:{rest // 60:02d}"

    @app.template_filter("local")
    def local(ts) -> str:
        return ts.astimezone(LOCAL_TZ).strftime("%d.%m. %H:%M:%S")

    return app


if __name__ == "__main__":
    create_app(os.getenv("DATA_DIR", "./data")).run(port=8080, debug=True)
