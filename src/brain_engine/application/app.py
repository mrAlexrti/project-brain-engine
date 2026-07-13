"""FastAPI composition and thin server-rendered routes."""

from pathlib import Path
import secrets
from urllib.parse import parse_qs

import yaml

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from brain_engine import __version__
from brain_engine.application.services.project_service import ProjectService
from brain_engine.application.services.brain_service import BrainService
from brain_engine.application.services.context_service import freeze_context, latest_context
from brain_engine.context import build_context
from brain_engine.domain import RequestPackage
from brain_engine.experiment import ExperimentError, ExperimentService
from brain_engine.experiment.evaluation import RUBRIC, lock_evaluation, reveal_treatment
from brain_engine.experiment.metadata import inspect_repository
from brain_engine.initialization import InitializationRequest, initialize_brain
from brain_engine.validation import validate_path


async def _form(request: Request) -> dict[str, str]:
    body = (await request.body()).decode("utf-8")
    values = {key: items[-1] for key, items in parse_qs(body, keep_blank_values=True).items()}
    expected_origin = f"{request.url.scheme}://{request.url.netloc}"
    if request.headers.get("origin") != expected_origin:
        raise HTTPException(403, "State-changing requests require an exact same-origin Origin header.")
    supplied = values.pop("csrf_token", None)
    cookie = request.cookies.get("brain_csrf")
    expected_token = request.app.state.csrf_token
    if (
        not supplied or not cookie
        or not secrets.compare_digest(supplied, cookie)
        or not secrets.compare_digest(supplied, expected_token)
    ):
        raise HTTPException(403, "Invalid CSRF token.")
    return values


def create_app(data_dir: Path | None = None) -> FastAPI:
    package = Path(__file__).parent
    data = (data_dir or Path.home() / ".project-brain-engine").resolve()
    data.mkdir(parents=True, exist_ok=True)
    app = FastAPI(title="Project Brain Engine", docs_url=None, redoc_url=None)
    csrf_token = secrets.token_urlsafe(32)
    templates = Jinja2Templates(
        directory=package / "templates",
        context_processors=[lambda request: {"csrf_token": request.app.state.csrf_token}],
    )
    app.mount("/static", StaticFiles(directory=package / "static"), name="static")
    projects = ProjectService(data)
    app.state.data_dir = data
    app.state.csrf_token = csrf_token

    @app.middleware("http")
    async def csrf_cookie(request: Request, call_next):
        response = await call_next(request)
        response.set_cookie(
            "brain_csrf", csrf_token, httponly=True, samesite="strict", secure=False,
        )
        return response

    @app.get("/", response_class=HTMLResponse)
    async def home(request: Request) -> HTMLResponse:
        experiments = sorted(data.glob("experiments/*/experiment.yaml"), key=lambda p: p.stat().st_mtime, reverse=True)[:10]
        return templates.TemplateResponse(request, "home.html", {"version": __version__, "projects": projects.list_profiles(), "experiments": experiments})

    @app.get("/projects/connect", response_class=HTMLResponse)
    async def connect_form(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(request, "projects/connect.html", {"error": None})

    @app.post("/projects/connect", response_class=HTMLResponse)
    async def connect(request: Request) -> HTMLResponse:
        values = await _form(request)
        try:
            profile = projects.connect(Path(values.get("path", "")))
        except Exception as exc:
            return templates.TemplateResponse(request, "projects/connect.html", {"error": str(exc)}, status_code=400)
        return templates.TemplateResponse(request, "projects/detail.html", {"project": profile})

    def project(project_id: str) -> dict:
        try:
            return projects.get(project_id)
        except ValueError as exc:
            raise HTTPException(404) from exc

    def project_brain(profile: dict) -> Path:
        return data / "brains" / profile["project_id"] / ".brain"

    def onboarding_context(profile: dict, **extra) -> dict:
        brain = project_brain(profile)
        validation = validate_path(brain) if brain.exists() else None
        try:
            frozen, _, _ = latest_context(data, profile["project_id"])
        except (OSError, ValueError, KeyError, IndexError):
            frozen = None
        return {
            "project": profile, "brain_exists": brain.exists(),
            "validation": validation, "items": validation.items if validation else [],
            "error": None, "message": None, "context": None, "task": "", "answers": "",
            "preflight": None, "frozen": frozen, **extra,
        }

    @app.get("/projects/{project_id}/onboarding", response_class=HTMLResponse)
    async def onboarding(request: Request, project_id: str) -> HTMLResponse:
        return templates.TemplateResponse(
            request, "projects/onboarding.html", onboarding_context(project(project_id)),
        )

    @app.post("/projects/{project_id}/brain/init", response_class=HTMLResponse)
    async def brain_init(request: Request, project_id: str) -> HTMLResponse:
        profile = project(project_id)
        values = await _form(request)
        try:
            initialize_brain(InitializationRequest(
                project_brain(profile), values.get("project_name", ""),
                values.get("project_purpose", ""), values.get("primary_technology", ""),
                values.get("language", "en"),
            ))
        except (ValueError, RuntimeError) as exc:
            return templates.TemplateResponse(
                request, "projects/onboarding.html",
                onboarding_context(profile, error=str(exc)), status_code=400,
            )
        return RedirectResponse(f"/projects/{project_id}/onboarding", status_code=303)

    @app.get("/projects/{project_id}/items/new", response_class=HTMLResponse)
    async def item_new(request: Request, project_id: str) -> HTMLResponse:
        project(project_id)
        return templates.TemplateResponse(request, "projects/item_form.html", {
            "item": None, "error": None, "types": list(BrainService.TYPE_DIRECTORIES),
        })

    @app.post("/projects/{project_id}/items/new", response_class=HTMLResponse)
    async def item_create(request: Request, project_id: str) -> HTMLResponse:
        profile = project(project_id)
        values = await _form(request)
        try:
            BrainService().save_item(project_brain(profile), {
                "id": values.get("item_id", ""), "type": values.get("item_type", ""),
                "title": values.get("title", ""),
            }, values.get("content", ""))
        except ValueError as exc:
            return templates.TemplateResponse(request, "projects/item_form.html", {
                "item": None, "error": str(exc), "types": list(BrainService.TYPE_DIRECTORIES),
            }, status_code=400)
        return RedirectResponse(f"/projects/{project_id}/onboarding", status_code=303)

    def find_item(profile: dict, item_id: str):
        items = BrainService().list_items(project_brain(profile))
        matches = [item for item in items if item.id == item_id]
        if len(matches) != 1:
            raise HTTPException(404)
        return matches[0]

    @app.get("/projects/{project_id}/items/{item_id}/edit", response_class=HTMLResponse)
    async def item_edit_form(request: Request, project_id: str, item_id: str) -> HTMLResponse:
        profile = project(project_id)
        return templates.TemplateResponse(request, "projects/item_form.html", {
            "item": find_item(profile, item_id), "error": None,
            "types": list(BrainService.TYPE_DIRECTORIES),
        })

    @app.post("/projects/{project_id}/items/{item_id}/edit", response_class=HTMLResponse)
    async def item_edit(request: Request, project_id: str, item_id: str) -> HTMLResponse:
        profile = project(project_id)
        values = await _form(request)
        try:
            BrainService().update_item(project_brain(profile), item_id, {
                "type": values.get("item_type", ""), "title": values.get("title", ""),
            }, values.get("content", ""))
        except ValueError as exc:
            return templates.TemplateResponse(request, "projects/item_form.html", {
                "item": find_item(profile, item_id), "error": str(exc),
                "types": list(BrainService.TYPE_DIRECTORIES),
            }, status_code=400)
        return RedirectResponse(f"/projects/{project_id}/onboarding", status_code=303)

    @app.post("/projects/{project_id}/items/{item_id}/approve")
    async def item_approve(request: Request, project_id: str, item_id: str):
        profile = project(project_id)
        values = await _form(request)
        BrainService().change_status(
            project_brain(profile), item_id, "approved",
            values.get("confirmed") == "yes",
        )
        return RedirectResponse(f"/projects/{project_id}/onboarding", status_code=303)

    def parse_answers(value: str) -> dict[str, str]:
        answers: dict[str, str] = {}
        for line in value.splitlines():
            if not line.strip():
                continue
            if "=" not in line:
                raise ValueError("Each request answer must use question.id=answer.")
            key, answer = (part.strip() for part in line.split("=", 1))
            if not key or not answer or key in answers:
                raise ValueError("Question answers must be non-empty and unique.")
            answers[key] = answer
        return answers

    @app.post("/projects/{project_id}/context/preview", response_class=HTMLResponse)
    async def context_preview(request: Request, project_id: str) -> HTMLResponse:
        profile = project(project_id)
        values = await _form(request)
        try:
            package_value = build_context(RequestPackage(
                values.get("task", ""), source="application",
                answers=parse_answers(values.get("answers", "")),
            ), project_brain(profile))
            rendered = yaml.safe_dump(package_value.to_dict(), sort_keys=False, allow_unicode=True)
            context = onboarding_context(profile, context=rendered, task=values.get("task", ""), answers=values.get("answers", ""))
        except (ValueError, RuntimeError) as exc:
            context = onboarding_context(profile, error=str(exc), task=values.get("task", ""), answers=values.get("answers", ""))
        return templates.TemplateResponse(request, "projects/onboarding.html", context)

    @app.post("/projects/{project_id}/context/freeze")
    async def context_freeze(request: Request, project_id: str):
        profile = project(project_id)
        values = await _form(request)
        try:
            package_value = build_context(RequestPackage(
                values.get("task", ""), source="application",
                answers=parse_answers(values.get("answers", "")),
            ), project_brain(profile))
            freeze_context(
                data, project_id, values.get("task", ""), package_value.to_dict(),
                new_revision=values.get("new_revision") == "yes",
            )
        except (ValueError, RuntimeError) as exc:
            return templates.TemplateResponse(
                request, "projects/onboarding.html",
                onboarding_context(
                    profile, error=str(exc), task=values.get("task", ""),
                    answers=values.get("answers", ""),
                ), status_code=400,
            )
        return RedirectResponse(f"/projects/{project_id}/onboarding", status_code=303)

    @app.post("/projects/{project_id}/preflight", response_class=HTMLResponse)
    async def preflight(request: Request, project_id: str) -> HTMLResponse:
        profile = project(project_id)
        await _form(request)
        brain = project_brain(profile)
        validation = validate_path(brain)
        current = inspect_repository(Path(profile["repository_path"]))
        try:
            frozen_metadata, _, _ = latest_context(data, project_id)
        except (OSError, ValueError, KeyError, IndexError):
            frozen_metadata = None
        approved_count = sum(item.status == "approved" for item in validation.items)
        checks = {
            "repository_clean": current["clean"], "brain_valid": validation.success,
            "approved_items": approved_count,
            "context_frozen": frozen_metadata is not None,
            "context_revision": frozen_metadata["revision"] if frozen_metadata else None,
            "ready": bool(
                current["clean"] and validation.success and approved_count and frozen_metadata
            ),
        }
        return templates.TemplateResponse(
            request, "projects/onboarding.html", onboarding_context(profile, preflight=checks),
        )

    @app.get("/experiments/{experiment_id}", response_class=HTMLResponse)
    async def experiment_status(request: Request, experiment_id: str) -> HTMLResponse:
        if not experiment_id or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for char in experiment_id):
            raise HTTPException(404)
        root = (data / "experiments" / experiment_id).resolve()
        try:
            root.relative_to((data / "experiments").resolve())
        except ValueError as exc:
            raise HTTPException(404) from exc
        state_file = root / "experiment.yaml"
        if not state_file.is_file():
            raise HTTPException(404)
        state, consistent = ExperimentService().status(root)
        return templates.TemplateResponse(request, "experiments/status.html", {"state": state, "consistent": consistent})

    @app.get("/create-experiment", response_class=HTMLResponse)
    async def new_experiment(
        request: Request, project_id: str | None = None,
    ) -> HTMLResponse:
        selected = project(project_id) if project_id else None
        frozen = latest_context(data, project_id)[0] if project_id else None
        return templates.TemplateResponse(request, "experiments/new.html", {
            "projects": projects.list_profiles(), "selected": selected,
            "frozen": frozen, "error": None,
        })

    @app.post("/create-experiment", response_class=HTMLResponse)
    async def create_experiment(request: Request) -> HTMLResponse:
        values = await _form(request)
        experiment_id = values.get("experiment_id", "")
        if not experiment_id or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for char in experiment_id):
            return templates.TemplateResponse(request, "experiments/new.html", {"projects": projects.list_profiles(), "error": "Experiment ID may contain letters, digits, hyphens, and underscores."}, status_code=400)
        output = data / "experiments" / experiment_id
        controls = {key: values.get(key, "") for key in ("agent_product", "agent_version", "model", "reasoning_setting", "permission_policy", "network_policy", "time_limit")}
        try:
            selected_id = values.get("project_id")
            if selected_id:
                profile = project(selected_id)
                frozen_metadata, task, context_path = latest_context(data, selected_id)
                repository = Path(profile["repository_path"])
                brain_path = project_brain(profile)
            else:
                frozen_metadata = None
                context_path = None
                task = values["task"]
                repository = Path(values["repository"])
                brain_path = Path(values["brain_path"])
            ExperimentService().initialize(repository, output, task, values["ground_truth"], brain_path, privacy=values.get("privacy", "private"), controls=controls, allow_existing_brain=values.get("allow_existing_brain") == "yes", frozen_context_path=context_path, frozen_context_revision=frozen_metadata["revision"] if frozen_metadata else 1)
        except Exception as exc:
            return templates.TemplateResponse(request, "experiments/new.html", {
                "projects": projects.list_profiles(), "selected": None,
                "frozen": None, "error": str(exc),
            }, status_code=400)
        return RedirectResponse(f"/experiments/{experiment_id}", status_code=303)

    def experiment_root(experiment_id: str) -> Path:
        if not experiment_id or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for char in experiment_id):
            raise HTTPException(404)
        root = (data / "experiments" / experiment_id).resolve()
        try:
            root.relative_to((data / "experiments").resolve())
        except ValueError as exc:
            raise HTTPException(404) from exc
        return root

    @app.get("/experiments/{experiment_id}/runs", response_class=HTMLResponse)
    async def runs(request: Request, experiment_id: str) -> HTMLResponse:
        root = experiment_root(experiment_id)
        state, _ = ExperimentService().status(root)
        return templates.TemplateResponse(request, "experiments/runs.html", {"state": state, "error": None})

    @app.post("/experiments/{experiment_id}/runs/{result_name}/{action}")
    async def run_action(request: Request, experiment_id: str, result_name: str, action: str):
        root = experiment_root(experiment_id)
        if result_name not in {"result-1", "result-2"}:
            raise HTTPException(404)
        values = await _form(request)
        service = ExperimentService()
        try:
            if action == "start":
                service.start_run(root, result_name)
            elif action == "finish":
                service.finish_run(root, result_name, {"final_report": values.get("final_report", ""), "permission_prompts": int(values.get("permission_prompts", "0")), "clarification_questions": int(values.get("clarification_questions", "0")), "corrective_iterations": int(values.get("corrective_iterations", "0")), "protocol_deviations": values.get("protocol_deviations", ""), "operator_notes": values.get("operator_notes", "")})
            elif action == "capture":
                service.capture(root, result_name)
            else:
                raise HTTPException(404)
        except (ExperimentError, ValueError) as exc:
            state, _ = service.status(root)
            return templates.TemplateResponse(request, "experiments/runs.html", {"state": state, "error": str(exc)}, status_code=400)
        return RedirectResponse(f"/experiments/{experiment_id}/runs", status_code=303)

    @app.get("/experiments/{experiment_id}/evaluation", response_class=HTMLResponse)
    async def evaluation(request: Request, experiment_id: str) -> HTMLResponse:
        root = experiment_root(experiment_id)
        state, _ = ExperimentService().status(root)
        return templates.TemplateResponse(request, "evaluation/index.html", {"state": state, "rubric": RUBRIC, "error": None, "mapping": None})

    @app.post("/experiments/{experiment_id}/evaluation/lock", response_class=HTMLResponse)
    async def evaluation_lock(request: Request, experiment_id: str) -> HTMLResponse:
        root = experiment_root(experiment_id)
        values = await _form(request)
        try:
            results = {}
            for result_name in ("result-1", "result-2"):
                results[result_name] = {"categories": {name: int(values.get(f"{result_name}-{name}", "-1")) for name in RUBRIC}, "evidence": {name: values.get(f"{result_name}-{name}-evidence", "") for name in RUBRIC}, "unsupported_assumptions": values.get(f"{result_name}-assumptions", ""), "critical_failure_cap": int(values[f"{result_name}-cap"]) if values.get(f"{result_name}-cap") else None}
            lock_evaluation(root, results)
        except ValueError as exc:
            state, _ = ExperimentService().status(root)
            return templates.TemplateResponse(request, "evaluation/index.html", {"state": state, "rubric": RUBRIC, "error": str(exc), "mapping": None}, status_code=400)
        return RedirectResponse(f"/experiments/{experiment_id}/evaluation", status_code=303)

    @app.post("/experiments/{experiment_id}/evaluation/reveal", response_class=HTMLResponse)
    async def evaluation_reveal(request: Request, experiment_id: str) -> HTMLResponse:
        await _form(request)
        root = experiment_root(experiment_id)
        try:
            mapping = reveal_treatment(root)
        except ValueError as exc:
            state, _ = ExperimentService().status(root)
            return templates.TemplateResponse(request, "evaluation/index.html", {"state": state, "rubric": RUBRIC, "error": str(exc), "mapping": None}, status_code=400)
        state, _ = ExperimentService().status(root)
        return templates.TemplateResponse(request, "evaluation/index.html", {"state": state, "rubric": RUBRIC, "error": None, "mapping": mapping})

    @app.post("/experiments/{experiment_id}/finalize")
    async def finalize(request: Request, experiment_id: str):
        await _form(request)
        root = experiment_root(experiment_id)
        ExperimentService().finalize(root)
        return RedirectResponse(f"/experiments/{experiment_id}", status_code=303)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    return app
