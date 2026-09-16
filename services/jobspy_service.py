import logging

from services.scrape_service import CooldownActive, ScrapeFailed, scrape_linkedin_jobs

logger = logging.getLogger(__name__)


def _is_string_list(value, allow_empty=True):
    if not isinstance(value, list) or not all(isinstance(s, str) for s in value):
        return False

    if any(not s.strip() for s in value):
        return False

    if not allow_empty and not value:
        return False

    return True


def validate_jobspy_payload(data):
    site_name = data.get("site_name")
    search_term = data.get("search_term")
    location = data.get("location")
    focus_titles = data.get("focus_titles")
    discard_terms = data.get("discard_terms")

    errors = []

    if not _is_string_list(site_name, allow_empty=False):
        errors.append("site_name deve ser um array de strings não vazio (e sem strings vazias)")

    if not isinstance(search_term, str) or not search_term.strip():
        errors.append("search_term deve ser uma string não vazia")

    if not isinstance(location, str) or not location.strip():
        errors.append("location deve ser uma string não vazia")

    if not _is_string_list(focus_titles, allow_empty=False):
        errors.append(
            "focus_titles deve ser um array de strings não vazio (e sem strings vazias) "
            "— vazio faria toda vaga ser descartada pelo filtro"
        )

    if not _is_string_list(discard_terms, allow_empty=True):
        errors.append("discard_terms deve ser um array de strings (sem strings vazias)")

    return errors


def handle_jobspy_request(data):
    errors = validate_jobspy_payload(data)
    if errors:
        return {"errors": errors}, 400

    site_name = data.get("site_name")
    search_term = data.get("search_term")
    location = data.get("location")
    focus_titles = data.get("focus_titles")
    discard_terms = data.get("discard_terms")

    try:
        jobs = scrape_linkedin_jobs(site_name, search_term, location, focus_titles, discard_terms)
    except CooldownActive as e:
        return {"errors": [str(e)]}, 429
    except ScrapeFailed as e:
        return {"errors": [str(e)]}, 500
    except Exception:
        logger.exception("Erro inesperado ao rodar o scrape")
        return {"errors": ["Erro inesperado ao rodar o scrape"]}, 500

    return {"jobs": jobs, "total": len(jobs)}, 200



