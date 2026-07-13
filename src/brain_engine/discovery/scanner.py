"""Bounded deterministic inspection of repository content at an exact Git SHA.

Confidence is mechanical: explicit manifest fields or commands are high; two or more
consistent markers are medium; filename/directory-only inference is low.
"""

import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import tomllib
from typing import Any

from brain_engine.discovery.models import (
    Conflict, Evidence, Finding, Proposal, Question, ScanLimits, ScanResult,
)
from brain_engine.experiment.git import GitService

SCANNER_VERSION = "1.0"
EXCLUDED_PARTS = {
    ".git", ".venv", "node_modules", "vendor", "dist", "build", "coverage",
    ".brain", "experiments", "__pycache__", ".tox", ".mypy_cache", ".pytest_cache",
}
DOC_NAMES = {"readme", "contributing", "architecture", "docs", "overview"}
SAFE_NAMES = {
    "pyproject.toml", "package.json", "cargo.toml", "go.mod", "pom.xml",
    "dockerfile", "compose.yml", "compose.yaml", "docker-compose.yml",
    "docker-compose.yaml", "requirements.txt", "requirements-dev.txt",
    "build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts",
    "pytest.ini", "tox.ini", "jest.config.js", "vitest.config.js", "makefile",
}
SAFE_SUFFIXES = {".sln", ".csproj"}
ENTRY_NAMES = {"main.py", "app.py", "manage.py", "server.py", "index.js", "index.ts", "main.go", "main.rs", "program.cs"}
ENV_TEMPLATE = re.compile(r"(^|/)(\.env(?:\.[^/]+)?\.(?:example|sample|template)|\.env\.example|env\.example)$", re.I)
SECRETISH_PATH = re.compile(r"(?:^|/)(?:\.env$|.*(?:secret|credential|private[-_]?key).*)", re.I)


def _stable(prefix: str, *values: Any) -> str:
    serialized = "\0".join(str(value) for value in values).encode("utf-8")
    return f"{prefix}-{hashlib.sha256(serialized).hexdigest()[:16]}"


def _normal(value: str) -> str:
    return " ".join(value.split()).strip()


class RepositoryScanner:
    def __init__(self, limits: ScanLimits | None = None, git: GitService | None = None) -> None:
        self.limits = limits or ScanLimits()
        self.git = git or GitService()

    def scan(self, repository: Path) -> ScanResult:
        root = self.git.repository_root(repository.resolve())
        sha = self.git.head(root)
        branch = self.git.run(root, "symbolic-ref", "--short", "-q", "HEAD", check=False).stdout.strip()
        result = ScanResult(str(root), sha, branch or "detached", not bool(branch), self.limits)
        entries = self.git.run(root, "ls-tree", "-r", "-z", "--long", sha).stdout.split("\0")
        if len(entries) - 1 > self.limits.max_tree_entries:
            entries = entries[:self.limits.max_tree_entries]
            result.warnings.append(
                f"Tree entry limit reached ({self.limits.max_tree_entries}); analysis is partial."
            )
        candidates: list[tuple[str, int]] = []
        top_directories: set[str] = set()
        excluded_roots: set[str] = set()
        for entry in entries:
            if not entry:
                continue
            metadata, path = entry.split("\t", 1)
            mode, kind, _object_id, size_value = metadata.split()
            if kind != "blob" or mode == "120000":
                result.skipped.append({"path": path, "reason": "symbolic link or non-file"})
                continue
            parts = PurePosixPath(path).parts
            if len(parts) > 1 and parts[0].casefold() not in EXCLUDED_PARTS:
                top_directories.add(parts[0])
            if any(part.casefold() in EXCLUDED_PARTS for part in parts):
                excluded_roots.add(next(part for part in parts if part.casefold() in EXCLUDED_PARTS))
                continue
            if len(parts) > self.limits.max_depth:
                continue
            size = int(size_value) if size_value != "-" else self.limits.max_file_bytes + 1
            if self._interesting(path):
                candidates.append((path, size))
        candidates.sort(key=lambda item: item[0].casefold())
        if len(candidates) > self.limits.max_files:
            result.warnings.append(f"File limit reached ({self.limits.max_files}); analysis is partial.")
            for path, _ in candidates[self.limits.max_files:]:
                result.skipped.append({"path": path, "reason": "file limit"})
            candidates = candidates[:self.limits.max_files]
        file_values: dict[str, bytes] = {}
        for path, size in candidates:
            if size > self.limits.max_file_bytes:
                result.skipped.append({"path": path, "reason": "individual file size limit"})
                result.warnings.append("One or more relevant files exceeded the individual size limit.")
                continue
            if result.scanned_bytes + size > self.limits.max_total_bytes:
                result.skipped.append({"path": path, "reason": "total scan budget"})
                result.warnings.append(f"Total scan budget reached ({self.limits.max_total_bytes} bytes); analysis is partial.")
                continue
            completed = subprocess.run(
                ["git", "cat-file", "blob", f"{sha}:{path}"], cwd=root,
                capture_output=True, timeout=60, shell=False,
            )
            if completed.returncode:
                result.skipped.append({"path": path, "reason": "Git object could not be read"})
                continue
            content = completed.stdout
            if b"\0" in content:
                result.skipped.append({"path": path, "reason": "binary file"})
                continue
            try:
                content.decode("utf-8")
            except UnicodeDecodeError:
                result.skipped.append({"path": path, "reason": "non-UTF-8 or binary file"})
                continue
            file_values[path] = content
            result.scanned_files += 1
            result.scanned_bytes += len(content)
        self._analyze(file_values, result)
        if top_directories:
            evidence_id = _stable("evidence", sha, ".", "top-level directory structure", "structure", SCANNER_VERSION)
            result.evidence.append(Evidence(
                evidence_id, sha, ".", "top-level directory structure", "structure",
                SCANNER_VERSION, excerpt=", ".join(sorted(top_directories)),
            ))
            self._finding(
                result, "top_level_directories", sorted(top_directories), "low", [evidence_id],
                "Directory names are structural markers only.",
            )
        result.skipped.extend(
            {"path": root_name, "reason": "excluded area"}
            for root_name in sorted(excluded_roots)
        )
        self._finish(result)
        return result

    @staticmethod
    def _interesting(path: str) -> bool:
        pure = PurePosixPath(path)
        name = pure.name.casefold()
        stem = pure.stem.casefold()
        generated = ".generated." in name or ".min." in name or any(
            part.casefold() in {"generated", "gen"} for part in pure.parts
        )
        if generated:
            return False
        return bool(
            len(pure.parts) == 1 or name in SAFE_NAMES or pure.suffix.casefold() in SAFE_SUFFIXES
            or stem in DOC_NAMES or name in ENTRY_NAMES or ENV_TEMPLATE.search(path)
            or (name.startswith("requirements") and name.endswith(".txt"))
            or (path.casefold().startswith("docs/") and pure.suffix.casefold() in {".md", ".rst", ".txt"})
            or path.startswith((".github/workflows/", ".gitlab-ci", "migrations/", "schema/", "schemas/", "tests/", "test/"))
        )

    def _evidence(self, result: ScanResult, path: str, locator: str, content: bytes, *, excerpt: str | None = None, detector: str = "manifest") -> str:
        evidence_id = _stable("evidence", result.repository_sha, path, locator, detector, SCANNER_VERSION)
        if excerpt is not None:
            excerpt = excerpt.encode("utf-8")[:self.limits.max_excerpt_bytes].decode("utf-8", "ignore")
        result.evidence.append(Evidence(
            evidence_id, result.repository_sha, path, locator, detector, SCANNER_VERSION,
            hashlib.sha256(content).hexdigest(), excerpt,
        ))
        return evidence_id

    def _finding(self, result: ScanResult, kind: str, value: Any, confidence: str, refs: list[str], explanation: str) -> None:
        normalized = _normal(value) if isinstance(value, str) else value
        result.findings.append(Finding(
            _stable("finding", kind, json.dumps(normalized, ensure_ascii=False, sort_keys=True)),
            kind, normalized, confidence, tuple(sorted(set(refs))), explanation,
        ))

    def _analyze(self, files: dict[str, bytes], result: ScanResult) -> None:
        languages: dict[str, list[str]] = {}
        project_names: list[tuple[str, str]] = []
        purposes: list[tuple[str, str]] = []
        commands: list[tuple[str, str]] = []
        packages: list[tuple[str, str]] = []
        frameworks: list[tuple[str, str]] = []
        for path, content in files.items():
            text = content.decode("utf-8")
            name = PurePosixPath(path).name.casefold()
            if ENV_TEMPLATE.search(path):
                names = sorted(set(re.findall(r"(?m)^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=", text)))
                ref = self._evidence(result, path, "variable names", content, detector="environment-template")
                self._finding(result, "environment_variables", names, "high", [ref], "Variable names are explicit in an environment template; values were neither retained nor reported.")
                continue
            if SECRETISH_PATH.search(path):
                result.skipped.append({"path": path, "reason": "potential secret file"})
                continue
            if name == "pyproject.toml":
                try:
                    doc = tomllib.loads(text)
                except tomllib.TOMLDecodeError:
                    result.warnings.append(f"Could not parse {path} as TOML.")
                    continue
                project = doc.get("project", {})
                if isinstance(project, dict) and project.get("name"):
                    ref = self._evidence(result, path, "project.name", content)
                    project_names.append((str(project["name"]), ref))
                ref = self._evidence(result, path, "manifest type", content)
                languages.setdefault("Python", []).append(ref)
                for dep in [*project.get("dependencies", []), *doc.get("build-system", {}).get("requires", [])]:
                    dep_name = re.split(r"[<>=!~\[ ;]", str(dep), maxsplit=1)[0].casefold()
                    for marker, framework in (("django", "Django"), ("fastapi", "FastAPI"), ("flask", "Flask"), ("pytest", "pytest")):
                        if dep_name == marker:
                            frameworks.append((framework, ref))
                scripts = project.get("scripts", {}) if isinstance(project, dict) else {}
                if isinstance(scripts, dict):
                    for script, target in sorted(scripts.items()):
                        command_ref = self._evidence(result, path, f"project.scripts.{script}", content)
                        commands.append((f"{script} = {target}", command_ref))
                tools = doc.get("tool", {})
                if isinstance(tools, dict):
                    for tool, command in (("pytest", "python -m pytest"), ("ruff", "python -m ruff check ."), ("mypy", "python -m mypy .")):
                        if tool in tools:
                            command_ref = self._evidence(result, path, f"tool.{tool}", content)
                            commands.append((command, command_ref))
            elif name == "package.json":
                try:
                    doc = json.loads(text)
                except json.JSONDecodeError:
                    result.warnings.append(f"Could not parse {path} as JSON.")
                    continue
                if isinstance(doc.get("name"), str):
                    project_names.append((doc["name"], self._evidence(result, path, "name", content)))
                ref = self._evidence(result, path, "manifest type", content)
                languages.setdefault("JavaScript/TypeScript", []).append(ref)
                scripts = doc.get("scripts", {})
                if isinstance(scripts, dict):
                    for script, command in sorted(scripts.items()):
                        command_ref = self._evidence(result, path, f"scripts.{script}", content)
                        commands.append((f"npm run {script}: {command}", command_ref))
                if isinstance(doc.get("main"), str):
                    entry_ref = self._evidence(result, path, "main", content)
                    self._finding(result, "application_entry_point", doc["main"], "high", [entry_ref], "The application entry point is explicitly declared in package.json.")
                dependencies = {**(doc.get("dependencies") or {}), **(doc.get("devDependencies") or {})}
                for marker, framework in (("react", "React"), ("next", "Next.js"), ("vue", "Vue"), ("express", "Express"), ("jest", "Jest"), ("vitest", "Vitest")):
                    if marker in dependencies:
                        frameworks.append((framework, ref))
            elif name in {"cargo.toml", "go.mod", "pom.xml"} or name.endswith((".sln", ".csproj")):
                language = {"cargo.toml": "Rust", "go.mod": "Go", "pom.xml": "Java/JVM"}.get(name, ".NET")
                ref = self._evidence(result, path, "manifest type", content)
                languages.setdefault(language, []).append(ref)
                if name == "cargo.toml":
                    try:
                        cargo = tomllib.loads(text)
                    except tomllib.TOMLDecodeError:
                        cargo = {}
                    package = cargo.get("package", {})
                    if isinstance(package, dict) and package.get("name"):
                        project_names.append((str(package["name"]), self._evidence(result, path, "package.name", content)))
                elif name == "go.mod":
                    module = re.search(r"(?m)^module\s+([^\s]+)", text)
                    if module:
                        project_names.append((module.group(1), self._evidence(result, path, "module", content)))
                    commands.append(("go test ./...", ref))
                elif name == "pom.xml":
                    artifact = re.search(r"<artifactId>\s*([^<]+)\s*</artifactId>", text)
                    if artifact:
                        project_names.append((artifact.group(1), self._evidence(result, path, "project/artifactId", content)))
                    commands.append(("mvn test", ref))
                elif name.endswith((".sln", ".csproj")):
                    commands.append(("dotnet test", ref))
            elif "requirements" in name and name.endswith(".txt"):
                ref = self._evidence(result, path, "dependency declarations", content)
                languages.setdefault("Python", []).append(ref)
                for line in text.splitlines():
                    dep_name = re.split(r"[<>=!~\[ ;]", line.strip(), maxsplit=1)[0].casefold()
                    for marker, framework in (("django", "Django"), ("fastapi", "FastAPI"), ("flask", "Flask"), ("pytest", "pytest")):
                        if dep_name == marker:
                            frameworks.append((framework, ref))
            elif name in {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "uv.lock", "cargo.lock"}:
                manager = {"package-lock.json": "npm", "yarn.lock": "yarn", "pnpm-lock.yaml": "pnpm", "poetry.lock": "Poetry", "uv.lock": "uv", "cargo.lock": "Cargo"}[name]
                packages.append((manager, self._evidence(result, path, "lockfile", content, detector="lockfile")))
            elif PurePosixPath(path).stem.casefold() in DOC_NAMES or name.startswith("readme"):
                lines = [line.strip() for line in text.splitlines() if line.strip()]
                heading = next((line.lstrip("# ").strip() for line in lines if line.startswith("#")), None)
                if heading:
                    ref = self._evidence(result, path, "first heading", content, excerpt=heading, detector="documentation")
                    project_names.append((heading, ref))
                paragraph = next((line for line in lines if not line.startswith(("#", "[", "!", "```")) and len(line) >= 20), None)
                if paragraph:
                    ref = self._evidence(result, path, "first descriptive paragraph", content, excerpt=paragraph, detector="documentation")
                    purposes.append((paragraph, ref))
                for token, language in (("python", "Python"), ("node.js", "JavaScript/TypeScript"), ("typescript", "JavaScript/TypeScript"), ("rust", "Rust"), ("golang", "Go")):
                    if re.search(rf"\b{re.escape(token)}\b", text, re.I):
                        ref = self._evidence(result, path, f"documentation mentions {token}", content, detector="documentation")
                        languages.setdefault(language, []).append(ref)
            elif name in {"build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts"}:
                ref = self._evidence(result, path, "Gradle build declaration", content)
                languages.setdefault("Java/JVM", []).append(ref)
                commands.append(("gradle test", ref))
            elif name in {"pytest.ini", "tox.ini", "jest.config.js", "vitest.config.js"}:
                framework = "pytest" if name in {"pytest.ini", "tox.ini"} else ("Jest" if name.startswith("jest") else "Vitest")
                ref = self._evidence(result, path, "test configuration", content)
                self._finding(result, "test_framework", framework, "high", [ref], "An explicit test-framework configuration file is present.")
            if name in ENTRY_NAMES:
                ref = self._evidence(result, path, "entry-point filename", content, detector="structure")
                self._finding(result, "application_entry_point", path, "low", [ref], "The filename is a common application entry-point marker; execution was not attempted.")
            if path.startswith(("migrations/", "schema/", "schemas/")):
                ref = self._evidence(result, path, "directory marker", content, detector="structure")
                self._finding(result, "database_schema_marker", str(PurePosixPath(path).parent), "low", [ref], "A conventional migration or schema directory is present.")
            if path.startswith(("tests/", "test/")):
                ref = self._evidence(result, path, "test directory marker", content, detector="structure")
                self._finding(result, "test_structure", str(PurePosixPath(path).parent), "low", [ref], "A conventional test directory is present.")
            if path.startswith((".github/workflows/", ".gitlab-ci")):
                ref = self._evidence(result, path, "CI configuration path", content, detector="structure")
                self._finding(result, "ci_configuration", path, "low", [ref], "The path is a conventional CI configuration marker.")
            if name.startswith(("dockerfile", "compose", "docker-compose")):
                ref = self._evidence(result, path, "deployment file", content, detector="structure")
                self._finding(result, "deployment_marker", path, "low", [ref], "The filename is a conventional container deployment marker.")
        dependency_text = "\n".join(
            content.decode("utf-8").casefold()
            for path, content in files.items()
            if PurePosixPath(path).name.casefold() in {"pyproject.toml", "package.json", "cargo.toml", "go.mod", "pom.xml", "build.gradle", "build.gradle.kts"}
            or "requirements" in PurePosixPath(path).name.casefold()
        )
        for marker, kind, value in (
            ("postgres", "database", "PostgreSQL"), ("mysql", "database", "MySQL"),
            ("sqlite", "database", "SQLite"), ("mongodb", "database", "MongoDB"),
            ("redis", "external_service", "Redis"), ("boto3", "external_service", "AWS SDK"),
        ):
            if marker in dependency_text:
                refs = [
                    item.evidence_id for item in result.evidence
                    if item.detector_name == "manifest" and item.source_path in files
                ]
                self._finding(result, kind, value, "high", refs, "The service is directly declared in dependency or build metadata.")
        for value, ref in project_names:
            confidence = "high" if any(e.source_locator in {"project.name", "name"} and e.evidence_id == ref for e in result.evidence) else "medium"
            self._finding(result, "project_name", value, confidence, [ref], "The project name is declared in a manifest." if confidence == "high" else "The project name is taken from the primary documentation heading.")
        for value, ref in purposes[:1]:
            self._finding(result, "project_purpose", value, "high", [ref], "The project purpose is directly documented in repository text.")
        for language, refs in sorted(languages.items()):
            confidence = "high" if any(e.detector_name == "manifest" and e.evidence_id in refs for e in result.evidence) else ("medium" if len(refs) >= 2 else "low")
            explanation = {"high": "An explicit language ecosystem manifest is present.", "medium": "Multiple consistent repository markers identify this language.", "low": "Only a documentation or structural marker identifies this language."}[confidence]
            self._finding(result, "language", language, confidence, refs, explanation)
        for manager, ref in packages:
            self._finding(result, "package_manager", manager, "high", [ref], "An explicit package-manager lockfile is present.")
        for framework, ref in sorted(set(frameworks)):
            self._finding(result, "framework", framework, "high", [ref], "The framework or test framework is explicitly declared as a dependency.")
        for command, ref in commands:
            self._finding(result, "command", command, "high", [ref], "The command is explicitly declared in a manifest; it was not executed.")

    def _finish(self, result: ScanResult) -> None:
        unique: dict[str, Finding] = {}
        for finding in result.findings:
            prior = unique.get(finding.finding_id)
            if prior:
                refs = tuple(sorted(set(prior.evidence_refs + finding.evidence_refs)))
                unique[finding.finding_id] = Finding(
                    finding.finding_id, finding.kind, finding.normalized_value,
                    prior.confidence if prior.confidence == "high" else finding.confidence,
                    refs, prior.explanation,
                )
            else:
                unique[finding.finding_id] = finding
        result.findings = sorted(unique.values(), key=lambda item: (item.kind, str(item.normalized_value)))
        result.evidence.sort(key=lambda item: item.evidence_id)
        for kind in ("project_name", "package_manager"):
            findings = [item for item in result.findings if item.kind == kind]
            values = {str(item.normalized_value).casefold() for item in findings}
            if len(values) > 1:
                sides = tuple({"value": item.normalized_value, "evidence_refs": list(item.evidence_refs)} for item in findings)
                result.conflicts.append(Conflict(
                    _stable("conflict", kind, *sorted(values)), kind, sides,
                    f"Repository sources provide incompatible {kind.replace('_', ' ')} conclusions; no side was selected.",
                ))
        language_findings = [item for item in result.findings if item.kind == "language"]
        manifest_languages = {
            str(item.normalized_value) for item in language_findings
            if any(
                evidence.detector_name == "manifest" and evidence.evidence_id in item.evidence_refs
                for evidence in result.evidence
            )
        }
        documented_languages = {
            str(item.normalized_value) for item in language_findings
            if any(
                evidence.detector_name == "documentation" and evidence.evidence_id in item.evidence_refs
                for evidence in result.evidence
            )
        }
        if manifest_languages and documented_languages - manifest_languages:
            sides = tuple(
                {"value": item.normalized_value, "evidence_refs": list(item.evidence_refs)}
                for item in language_findings
            )
            result.conflicts.append(Conflict(
                _stable("conflict", "language", *sorted(manifest_languages | documented_languages)),
                "language", sides,
                "Documentation and explicit manifests indicate incompatible language conclusions; no side was selected.",
            ))
        for finding in result.findings:
            if finding.kind in {"project_name", "project_purpose", "language", "framework", "package_manager", "command"}:
                title = finding.kind.replace("_", " ").title()
                result.proposals.append(Proposal(
                    _stable("proposal", finding.finding_id), "knowledge", title,
                    str(finding.normalized_value), finding.evidence_refs,
                ))
        if not any(item.kind == "project_purpose" for item in result.findings):
            refs = tuple(item.evidence_id for item in result.evidence if item.detector_name == "documentation")
            result.questions.append(Question(
                "question-discovery-project-purpose", "What is this project's purpose?",
                "No direct project-purpose statement was found in the bounded committed files.", refs,
            ))
        if len({item.normalized_value for item in result.findings if item.kind == "language"}) != 1:
            choices = tuple(sorted(str(item.normalized_value) for item in result.findings if item.kind == "language"))
            refs = tuple(ref for item in result.findings if item.kind == "language" for ref in item.evidence_refs)
            result.questions.append(Question(
                "question-discovery-primary-language", "What is the primary project language?",
                "Evidence does not identify exactly one primary language.", tuple(sorted(set(refs))), choices,
            ))
        result.proposals.sort(key=lambda item: item.proposal_id)
        result.questions.sort(key=lambda item: item.question_id)
        result.conflicts.sort(key=lambda item: item.conflict_id)
        result.skipped.sort(key=lambda item: (item["path"], item["reason"]))
        result.warnings = sorted(set(result.warnings))
