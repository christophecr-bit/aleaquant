"""Versioned documentary prerequisites; local files are never publication proof.

Version 1.0 · 2026-10-10 · AleaQuant. No remote writes or editorial generation.
Related links are intentionally outside the prerequisite DAG.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path, PurePosixPath
import re
from urllib.parse import urlsplit
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

SCHEMA = "aleaquant-content-dependencies-1.0"
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "configs/content-dependencies.json"


class DependencyError(ValueError):
    """A subject cannot be imported or published with these prerequisites."""


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def empty_registry():
    return {"schema": SCHEMA, "version": "1.0", "production_origin": "https://aleaquant.org",
            "nodes": [], "managed_pages": [], "observations": [], "publications": []}


def _requirements(values, version="1.0", versions=None):
    versions = versions or {}
    return [{"id": item, "version": versions.get(item, version)} if isinstance(item, str)
            else deepcopy(item) for item in values]


def notion_node(record, version="1.0", versions=None,
                target_path="comprendre/glossaire/index.html"):
    """Materialize root NOTIONS records; use this SHA in the entry HTML markers."""
    node = {"id": record["id"], "kind": "notion", "version": version,
            "content": {"label": record["label"], "definition": record["definition"]},
            "target": {"path": target_path, "anchor": record["id"]},
            "requires": _requirements(record.get("requires", []), version, versions),
            "related": list(record.get("related", [])), "state": "local"}
    node["content_sha256"] = digest({key: value for key, value in node.items() if key != "state"})
    return node


def page_node(node_id, target_path, content_sha256, requires, version="1.0",
              versions=None, kind="page"):
    """Page SHA is the exact HTML asset SHA; article SHA is the approved draft SHA."""
    return {"id": node_id, "kind": kind, "version": version,
            "content_sha256": content_sha256,
            "target": {"path": target_path, "anchor": None},
            "requires": _requirements(requires, version, versions), "related": [], "state": "local"}


def article_node(article, requires, version="1.0", target_path=None, versions=None):
    """Register only a reviewed export; no approval is granted by this helper."""
    if target_path is None:
        raise DependencyError("Le chemin cible de l’article doit être déclaré explicitement")
    return page_node("article:" + article["article_id"], target_path,
                     article["draft_sha256"], requires, version, versions, "article")


def update_nodes(registry, nodes, managed_pages=None):
    """Preserve previous observations; changed content starts local, never published."""
    result = deepcopy(registry)
    keyed = {(n["id"], n["version"]): n for n in result["nodes"]}
    for node in deepcopy(nodes):
        key = (node["id"], node["version"])
        old = keyed.get(key)
        if old and old["content_sha256"] != node["content_sha256"] and any(
                proof["node_id"] == key[0] and proof["node_version"] == key[1]
                for proof in result["publications"]):
            raise DependencyError("Version déjà publiée immuable : créer une nouvelle version")
        if old and old["content_sha256"] == node["content_sha256"]:
            node["state"] = old["state"]
        keyed[key] = node
    result["nodes"] = list(keyed.values())
    if managed_pages is not None:
        result["managed_pages"] = _requirements(managed_pages)
    return result


def _object(value, required, optional=()):
    if not isinstance(value, dict) or set(value) - set(required) - set(optional) or set(required) - set(value):
        raise DependencyError("Structure documentaire absente ou champs inconnus")


def _text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise DependencyError(f"{label} absent ou invalide")


def _sha(value):
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise DependencyError("SHA-256 documentaire invalide")


def _ref(value):
    _object(value, ("id", "version"))
    for field in ("id", "version"):
        _text(value[field], field)
    return value["id"], value["version"]


def _relative(value):
    _text(value, "Chemin")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "\\" in value or str(path) != value:
        raise DependencyError("Chemin documentaire doit être relatif et sans traversée")


def _date(value):
    _text(value, "Date de contrôle")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise DependencyError("Date de contrôle invalide") from error
    if parsed.tzinfo is None or parsed > datetime.now(timezone.utc):
        raise DependencyError("Date de contrôle sans fuseau ou dans le futur")


def validate_registry(registry):
    """Validate structure and DAG, without treating missing references as published."""
    _object(registry, ("schema", "version", "production_origin", "nodes", "managed_pages", "observations", "publications"))
    if registry["schema"] != SCHEMA or registry["version"] != "1.0":
        raise DependencyError("Version de registre documentaire non supportée")
    origin = urlsplit(registry["production_origin"])
    if (origin.scheme != "https" or not origin.hostname or origin.username or origin.password
            or origin.path not in ("", "/") or origin.query or origin.fragment
            or origin.port or origin.hostname in ("localhost", "127.0.0.1", "::1")
            or registry["production_origin"].endswith("/")):
        raise DependencyError("Origine HTTPS de production invalide")
    for field in ("nodes", "managed_pages", "observations", "publications"):
        if not isinstance(registry[field], list):
            raise DependencyError(f"{field} doit être une liste")
    keyed = {}
    for node in registry["nodes"]:
        _object(node, ("id", "kind", "version", "content_sha256", "target", "requires", "related", "state"), ("content",))
        key = _ref({field: node[field] for field in ("id", "version")})
        if key in keyed or node["kind"] not in ("notion", "article", "page") or node["state"] not in ("draft", "local", "published"):
            raise DependencyError("Nœud documentaire dupliqué ou type/état inconnu")
        _sha(node["content_sha256"])
        _object(node["target"], ("path", "anchor"))
        _relative(node["target"]["path"])
        if node["target"]["anchor"] is not None:
            _text(node["target"]["anchor"], "Ancre")
        if not isinstance(node["requires"], list) or not isinstance(node["related"], list):
            raise DependencyError("requires/related doivent être des listes")
        refs = [_ref(value) for value in node["requires"]]
        if len(refs) != len(set(refs)):
            raise DependencyError("Prérequis dupliqué")
        for related in node["related"]:
            _text(related, "Lien voisin")
        if node["kind"] == "notion":
            _object(node.get("content"), ("label", "definition"))
            for value in node["content"].values():
                _text(value, "Définition")
            if node["target"]["anchor"] is None:
                raise DependencyError("Ancre de notion absente")
            payload = {k: v for k, v in node.items() if k not in ("state", "content_sha256")}
            if node["content_sha256"] != digest(payload):
                raise DependencyError("Définition ou dépendances modifiées sans nouveau SHA")
        elif "content" in node:
            raise DependencyError("Content réservé aux définitions de notions")
        keyed[key] = node
    managed = [_ref(value) for value in registry["managed_pages"]]
    if len(managed) != len(set(managed)) or any(key not in keyed or keyed[key]["kind"] != "page" for key in managed):
        raise DependencyError("Pages gérées absentes ou dupliquées")
    observations = {}
    for observation in registry["observations"]:
        _object(observation, ("id", "environment", "anonymous", "url", "http_status", "checked_at", "deployment_id", "asset_sha256", "response_path"))
        _text(observation["id"], "Identifiant d’observation")
        if observation["id"] in observations:
            raise DependencyError("Observation dupliquée")
        if type(observation["anonymous"]) is not bool or type(observation["http_status"]) is not int:
            raise DependencyError("Statut HTTP ou anonymat invalide")
        for field in ("environment", "url", "deployment_id"):
            _text(observation[field], field)
        _date(observation["checked_at"])
        _sha(observation["asset_sha256"])
        _relative(observation["response_path"])
        observations[observation["id"]] = observation
    publications = set()
    for publication in registry["publications"]:
        _object(publication, ("node_id", "node_version", "content_sha256", "observation_id"))
        key = (publication["node_id"], publication["node_version"], publication["content_sha256"], publication["observation_id"])
        if key in publications or (key[0], key[1]) not in keyed or key[3] not in observations:
            raise DependencyError("Publication dupliquée ou observation/nœud absents")
        _sha(publication["content_sha256"])
        publications.add(key)
    # A related backlink does not participate in this traversal.
    done, active = set(), set()
    def visit(key):
        if key in active:
            raise DependencyError(f"Cycle de prérequis : {key[0]}@{key[1]}")
        if key in done or key not in keyed:
            return
        active.add(key)
        for dependency in keyed[key]["requires"]:
            visit(_ref(dependency))
        active.remove(key)
        done.add(key)
    for key in keyed:
        visit(key)
    if any(keyed[_ref(reference)]["kind"] != "notion" for node in keyed.values()
           for reference in node["requires"] if _ref(reference) in keyed):
        raise DependencyError("Un prérequis obligatoire doit référencer une notion")
    return registry


class _EntryParser(HTMLParser):
    def __init__(self, anchor):
        super().__init__(convert_charrefs=True)
        self.anchor = anchor
        self.depth = 0
        self.matches = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        void = tag in ("area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr")
        if self.current is not None and not void:
            self.depth += 1
        if attributes.get("id") == self.anchor:
            self.current = {"attrs": attributes, "text": []}
            self.matches.append(self.current)
            self.depth = 1

    def handle_endtag(self, tag):
        if self.current is not None:
            self.depth -= 1
            if self.depth <= 0:
                self.current = None

    def handle_data(self, data):
        if self.current is not None:
            self.current["text"].append(data)


def _safe_read(base_dir, relative):
    _relative(relative)
    base = Path(base_dir).resolve()
    path = (base / relative).resolve()
    if base not in path.parents or not path.is_file():
        raise DependencyError("Réponse HTTP conservée absente ou hors du dépôt")
    return path.read_bytes()


def verify_observation(registry, node, observation, base_dir=ROOT):
    """Validate retained public HTTP evidence, never a dry-run or local asset list."""
    if (observation["environment"] != "production" or observation["anonymous"] is not True
            or observation["http_status"] != 200):
        raise DependencyError("Cible non vérifiée publiquement en production (recette/draft ne suffisent pas)")
    expected_url = registry["production_origin"] + "/" + node["target"]["path"]
    canonical_url = expected_url.removesuffix("index.html") if expected_url.endswith("/index.html") else expected_url
    if observation["url"] not in (expected_url, canonical_url):
        raise DependencyError("URL de preuve différente de la cible déclarée")
    body = _safe_read(base_dir, observation["response_path"])
    if sha256(body).hexdigest() != observation["asset_sha256"]:
        raise DependencyError("SHA de réponse HTTP différent de la preuve")
    if node["kind"] == "page" and node["content_sha256"] != observation["asset_sha256"]:
        raise DependencyError("Version de page différente de la réponse publiée")
    if node["kind"] == "notion":
        _verify_definition(node, body)
    return {"node_id": node["id"], "version": node["version"],
            "checked_at": observation["checked_at"], "deployment_id": observation["deployment_id"],
            "asset_sha256": observation["asset_sha256"], "url": observation["url"]}


def _verify_definition(node, body):
    parser = _EntryParser(node["target"]["anchor"])
    try:
        parser.feed(body.decode("utf-8"))
    except UnicodeDecodeError as error:
        raise DependencyError("Réponse documentaire non UTF-8") from error
    if len(parser.matches) != 1:
        raise DependencyError("Ancre de définition absente ou dupliquée")
    entry = parser.matches[0]
    attributes = entry["attrs"]
    if any(attributes.get(attr) != node[field] for attr, field in (
            ("data-notion-id", "id"), ("data-notion-version", "version"), ("data-notion-sha256", "content_sha256"))):
        raise DependencyError("Version/SHA de notion absents ou différents")
    visible = " ".join(" ".join(entry["text"]).split())
    if any(" ".join(value.split()) not in visible for value in node["content"].values()):
        raise DependencyError("Définition différente du contenu versionné")


def _published(registry, node, base_dir):
    if node["state"] != "published":
        raise DependencyError(f"Notion {node['id']}@{node['version']} seulement {node['state']}")
    observations = {value["id"]: value for value in registry["observations"]}
    proofs = [value for value in registry["publications"]
              if value["node_id"] == node["id"] and value["node_version"] == node["version"]
              and value["content_sha256"] == node["content_sha256"]]
    proofs.sort(key=lambda proof: datetime.fromisoformat(
        observations[proof["observation_id"]]["checked_at"].replace("Z", "+00:00")), reverse=True)
    errors = []
    for proof in proofs:
        try:
            return verify_observation(registry, node, observations[proof["observation_id"]], base_dir)
        except DependencyError as error:
            errors.append(str(error))
    raise DependencyError("; ".join(errors) if errors else "Preuve de publication exacte absente")


def publication_report(registry, node_id, version, content_sha256=None, base_dir=ROOT):
    """Prerequisites, including their transitive roots, must already be public."""
    validate_registry(registry)
    keyed = {(n["id"], n["version"]): n for n in registry["nodes"]}
    subject = (node_id, version)
    blockers, proofs, visited = [], [], set()
    node = keyed.get(subject)
    if node is None:
        blockers.append({"id": node_id, "version": version, "reason": "Sujet/version non enregistré"})
    elif content_sha256 is not None and content_sha256 != node["content_sha256"]:
        blockers.append({"id": node_id, "version": version, "reason": "SHA du sujet différent du registre"})
    def visit(key, chain):
        if key in visited:
            return
        visited.add(key)
        dependency = keyed.get(key)
        if dependency is None:
            blockers.append({"id": key[0], "version": key[1], "via": chain, "reason": "Prérequis/version absent"})
            return
        try:
            proofs.append(_published(registry, dependency, base_dir))
        except DependencyError as error:
            blockers.append({"id": key[0], "version": key[1], "via": chain, "reason": str(error)})
        for child in dependency["requires"]:
            visit(_ref(child), chain + [key[0]])
    if node:
        for requirement in node["requires"]:
            visit(_ref(requirement), [node_id])
    return {"schema": "aleaquant-content-dependency-report-1.0", "subject": node_id,
            "version": version, "status": "blocked" if blockers else "ready",
            "blockers": blockers, "published_prerequisites": proofs,
            "scope": "Documentary prerequisites only; editorial human approval remains mandatory"}


def require_publication(registry, node_id, version, content_sha256=None, base_dir=ROOT):
    report = publication_report(registry, node_id, version, content_sha256, base_dir)
    if report["status"] != "ready":
        raise DependencyError("Dépendances documentaires bloquantes : " + "; ".join(
            f"{value['id']}@{value['version']} — {value['reason']}" for value in report["blockers"]))
    return report


def plan_batch(registry, subjects):
    """Order required definitions first; a plan never creates publication proof."""
    validate_registry(registry)
    keyed = {(n["id"], n["version"]): n for n in registry["nodes"]}
    result, visited = [], set()
    def visit(key):
        if key in visited:
            return
        node = keyed.get(key)
        if node is None:
            raise DependencyError(f"Prérequis/version absent : {key[0]}@{key[1]}")
        for requirement in node["requires"]:
            visit(_ref(requirement))
        visited.add(key)
        result.append({"id": key[0], "version": key[1], "kind": node["kind"],
                       "state": node["state"], "action": "verify_or_publish_definition" if node["kind"] == "notion" else "gate_after_prerequisite_publication"})
    for subject in subjects:
        visit(_ref(subject))
    return {"schema": "aleaquant-content-publication-plan-1.0", "order": result,
            "grants_publication": False}


def attach_publications(registry, observation, references, base_dir=ROOT):
    """Attach observed evidence only after all exact targets pass validation."""
    result = deepcopy(registry)
    if any(value["id"] == observation["id"] and value != observation for value in result["observations"]):
        raise DependencyError("Identifiant d’observation déjà utilisé pour une autre preuve")
    if observation not in result["observations"]:
        result["observations"].append(deepcopy(observation))
    validate_registry(result)
    keyed = {(n["id"], n["version"]): n for n in result["nodes"]}
    requested = {_ref(reference) for reference in references}
    # Definitions in the same public response may bootstrap together. A root in
    # another document must already carry its own public evidence.
    for key in requested:
        if key not in keyed:
            raise DependencyError("Publication d’une notion non enregistrée")
        for reference in keyed[key]["requires"]:
            dependency = _ref(reference)
            if dependency not in requested:
                if dependency not in keyed:
                    raise DependencyError("Racine de définition non enregistrée")
                require_publication(result, dependency[0], dependency[1], base_dir=base_dir)
                _published(result, keyed[dependency], base_dir)
    for reference in references:
        key = _ref(reference)
        if key not in keyed:
            raise DependencyError("Publication d’une notion non enregistrée")
        node = keyed[key]
        verify_observation(result, node, observation, base_dir)
        proof = {"node_id": key[0], "node_version": key[1], "content_sha256": node["content_sha256"], "observation_id": observation["id"]}
        if proof not in result["publications"]:
            result["publications"].append(proof)
        node["state"] = "published"
    validate_registry(result)
    return result


def load_registry(path=DEFAULT_REGISTRY):
    try:
        registry = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise DependencyError(f"Registre documentaire absent ou illisible : {path}") from error
    return validate_registry(registry)


def require_article(article, registry_path=DEFAULT_REGISTRY, base_dir=ROOT):
    """Import gate binds the exact human-reviewed draft to its explicit inventory."""
    registry = load_registry(registry_path)
    _reviewed_article_sha(article)
    node_id = "article:" + article["article_id"]
    nodes = [node for node in registry["nodes"] if node["id"] == node_id
             and node["kind"] == "article" and node["content_sha256"] == article["draft_sha256"]]
    if len(nodes) != 1:
        raise DependencyError("Article/SHA exact non enregistré dans le registre documentaire")
    return require_publication(registry, node_id, nodes[0]["version"], article["draft_sha256"], base_dir)


def _reviewed_article_sha(article):
    decision = article.get("human_decision", {})
    if (article.get("status") != "HUMAN_APPROVED" or decision.get("approved") is not True
            or not isinstance(decision.get("reviewer"), str) or not decision["reviewer"].strip()
            or digest(article.get("draft")) != article.get("draft_sha256")
            or decision.get("draft_sha256") != article.get("draft_sha256")):
        raise DependencyError("Article différent du brouillon approuvé")


def deployment_report(registry, assets_dir, base_dir=ROOT):
    """Gate explicit managed pages and every editorial article present in the lot."""
    validate_registry(registry)
    assets = Path(assets_dir)
    keyed = {(n["id"], n["version"]): n for n in registry["nodes"]}
    reports = []
    notion_targets = {}
    for node in registry["nodes"]:
        path = assets / node["target"]["path"]
        if node["kind"] == "notion" and path.is_file():
            notion_targets.setdefault((node["id"], node["target"]["path"]), []).append(node)
    for (node_id, target_path), versions in notion_targets.items():
        body = (assets / target_path).read_bytes()
        matches, errors = [], []
        for node in versions:
            try:
                _verify_definition(node, body)
                matches.append(node)
            except DependencyError as error:
                errors.append(str(error))
        if len(matches) != 1:
            reports.append({"subject": node_id, "status": "blocked",
                            "blockers": [{"id": node_id, "reason": "; ".join(errors) or "Version de définition ambiguë"}]})
    def subject_report(node, content_sha):
        result = publication_report(registry, node["id"], node["version"], content_sha, base_dir)
        for proof in result["published_prerequisites"]:
            dependency = keyed[(proof["node_id"], proof["version"])]
            local_path = assets / dependency["target"]["path"]
            if local_path.is_file():
                try:
                    # The page may gain independent definitions. The required
                    # existing definition must retain its own exact version,
                    # semantic SHA and text; the whole asset need not be frozen.
                    _verify_definition(dependency, local_path.read_bytes())
                except DependencyError as error:
                    result["blockers"].append({"id": dependency["id"], "version": dependency["version"],
                                               "reason": "Le lot retirerait ou modifierait une définition requise déjà publiée : " + str(error)})
        if result["blockers"]:
            result["status"] = "blocked"
        return result
    for reference in registry["managed_pages"]:
        node = keyed[_ref(reference)]
        path = assets / node["target"]["path"]
        if path.is_file():
            reports.append(subject_report(node, sha256(path.read_bytes()).hexdigest()))
    journal_path = assets / "articles.json"
    if journal_path.exists():
        journal = json.loads(journal_path.read_text(encoding="utf-8"))
        for article in journal.get("articles", []):
            node_id = "article:" + article["article_id"]
            try:
                _reviewed_article_sha(article)
            except DependencyError as error:
                reports.append({"subject": node_id, "status": "blocked", "blockers": [{"id": node_id, "reason": str(error)}]})
                continue
            nodes = [n for n in registry["nodes"] if n["id"] == node_id and n["kind"] == "article"
                     and n["content_sha256"] == article.get("draft_sha256")]
            if len(nodes) != 1:
                reports.append({"subject": node_id, "status": "blocked", "blockers": [{"id": node_id, "reason": "Article/SHA exact non enregistré"}]})
            else:
                reports.append(subject_report(nodes[0], article["draft_sha256"]))
    return {"schema": "aleaquant-content-deployment-gate-1.0",
            "status": "blocked" if any(report["status"] == "blocked" for report in reports) else "ready",
            "subjects": reports, "assets_directory": str(assets)}


def _anonymous_fetch(url):
    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None
    # Fresh opener: no cookie jar, login session or authentication handler.
    opener = build_opener(NoRedirect)
    request = Request(url, headers={"Accept-Encoding": "identity", "User-Agent": "AleaQuant-documentary-live-gate/1.0"})
    with opener.open(request, timeout=10) as response:
        return response.status, response.geturl(), response.read(5_000_001)


def verify_live_prerequisites(registry, report, fetch=None):
    """Before real deployment, reconfirm exact public assets once per distinct URL.

    Local reports and imports do not call this function. It never modifies the
    registry and never treats a live response as a new version's publication.
    """
    validate_registry(registry)
    if report["status"] != "ready":
        raise DependencyError("Lot déjà bloqué : aucun accès réseau nécessaire")
    expected = {}
    subjects = report.get("subjects", [report])
    for subject in subjects:
        for proof in subject.get("published_prerequisites", []):
            url = proof["url"]
            parsed = urlsplit(url)
            if (f"{parsed.scheme}://{parsed.netloc}" != registry["production_origin"]
                    or parsed.query or parsed.fragment or parsed.username or parsed.password):
                raise DependencyError("Origine publique différente de la production déclarée")
            _sha(proof["asset_sha256"])
            if url in expected and expected[url] != proof["asset_sha256"]:
                raise DependencyError("Versions requises incompatibles sur une même URL publique")
            expected[url] = proof["asset_sha256"]
    fetch = fetch or _anonymous_fetch
    checks = []
    for url, expected_sha in sorted(expected.items()):
        try:
            status, final_url, body = fetch(url)
        except (HTTPError, URLError, OSError, TimeoutError) as error:
            if isinstance(error, HTTPError):
                error.close()
            raise DependencyError(f"Cible publique inaccessible : {url}") from error
        if status != 200 or final_url != url:
            raise DependencyError(f"Cible publique non anonyme ou redirigée : {url}")
        if not isinstance(body, bytes) or len(body) > 5_000_000 or sha256(body).hexdigest() != expected_sha:
            raise DependencyError(f"SHA public modifié depuis la preuve : {url}")
        checks.append({"url": url, "asset_sha256": expected_sha, "http_status": 200})
    return {"status": "ready", "checked_public_assets": checks,
            "checked_at": datetime.now(timezone.utc).isoformat()}
