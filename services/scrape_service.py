import json
import logging
import os
import threading
import time
from urllib.parse import urlparse

import pandas as pd
from jobspy import scrape_jobs

from services.filters import DISCARD_TERMS, FOCUS_TITLES

logger = logging.getLogger(__name__)

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
SEEN_IDS_FILE = os.path.join(OUTPUT_DIR, "seen_ids.json")
COOLDOWN_FILE = os.path.join(OUTPUT_DIR, "last_run.txt")

COOLDOWN_SECONDS = 60
RESULTS_WANTED = 20
MAX_FETCH_ATTEMPTS = 3

_scrape_lock = threading.Lock()


class ScrapeFailed(Exception):
    """Erro ao rodar o scrape ou salvar o resultado."""


class CooldownActive(Exception):
    """Scrape chamado antes do cooldown mínimo entre execuções."""


def _is_valid_proxy(proxy):
    parsed = urlparse(proxy)
    return parsed.scheme in ("http", "https", "socks4", "socks5") and bool(parsed.hostname)


def _get_proxies():
    """Proxy opcional para rotacionar IP, ex: PROXIES="http://user:pass@ip1:port,http://user:pass@ip2:port" """
    proxies_env = os.environ.get("PROXIES")
    if not proxies_env:
        return None

    candidates = [p.strip() for p in proxies_env.split(",") if p.strip()]
    valid_proxies = [p for p in candidates if _is_valid_proxy(p)]

    invalid_proxies = set(candidates) - set(valid_proxies)
    if invalid_proxies:
        logger.warning("Proxies inválidos ignorados: %s", ", ".join(invalid_proxies))

    return valid_proxies or None


def _check_cooldown():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if os.path.exists(COOLDOWN_FILE):
        with open(COOLDOWN_FILE, "r") as f:
            last_run = float(f.read().strip() or 0)

        elapsed = time.time() - last_run
        if elapsed < COOLDOWN_SECONDS:
            raise CooldownActive(
                f"Aguarde mais {COOLDOWN_SECONDS - elapsed:.0f}s antes de rodar o scrape novamente."
            )

    with open(COOLDOWN_FILE, "w") as f:
        f.write(str(time.time()))


def _load_seen_ids():
    if not os.path.exists(SEEN_IDS_FILE):
        return set()

    with open(SEEN_IDS_FILE, "r") as f:
        return set(json.load(f))


def _save_seen_ids(seen_ids):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(SEEN_IDS_FILE, "w") as f:
        json.dump(list(seen_ids), f)


def _apply_title_filter(jobs, focus_titles, discard_terms):
    titles = jobs["title"].str.lower()

    focus_mask = titles.apply(
        lambda title: any(term.lower() in title for term in focus_titles)
    )
    discard_mask = titles.apply(
        lambda title: any(term.lower() in title for term in discard_terms)
    )

    return jobs[focus_mask & ~discard_mask]


def _fetch_new_jobs(site_name, search_term, location, seen_ids, focus_titles=None, discard_terms=None):
    titles_to_focus = focus_titles if focus_titles else FOCUS_TITLES
    terms_to_discard = discard_terms if discard_terms else DISCARD_TERMS

    collected = None
    offset = 0
    attempts = 0

    logger.info("Fetch iniciado: site=%s search_term=%s location=%s", site_name, search_term, location)

    while (collected is None or len(collected) < RESULTS_WANTED) and attempts < MAX_FETCH_ATTEMPTS:
        logger.info(
            "Buscando lote %d/%d (offset=%d)", attempts + 1, MAX_FETCH_ATTEMPTS, offset
        )
        batch = scrape_jobs(
            site_name=site_name,
            search_term=search_term,
            location=location,
            results_wanted=RESULTS_WANTED,
            hours_old=72,
            offset=offset,
            linkedin_fetch_description=True,
            proxies=_get_proxies(),
        )
        attempts += 1
        offset += RESULTS_WANTED

        if batch is None or batch.empty:
            logger.info("Lote %d veio vazio, encerrando fetch.", attempts)
            break

        batch = _apply_title_filter(batch, titles_to_focus, terms_to_discard)
        batch = batch[~batch["id"].isin(seen_ids)]
        batch = batch.drop_duplicates(subset="id")

        collected = batch if collected is None else _concat_unique(collected, batch)

        logger.info(
            "Lote %d processado: %d vaga(s) nova(s) até agora (meta=%d).",
            attempts,
            len(collected),
            RESULTS_WANTED,
        )

        if len(collected) < RESULTS_WANTED and attempts < MAX_FETCH_ATTEMPTS:
            logger.info("Indo para o próximo lote para tentar completar a meta.")

    if collected is None:
        collected = batch.iloc[0:0] if batch is not None else _empty_jobs_frame()

    seen_ids.update(collected["id"].tolist())
    _save_seen_ids(seen_ids)

    result = collected.head(RESULTS_WANTED)
    logger.info("Fetch finalizado: %d vaga(s) nova(s) retornada(s).", len(result))

    return result


def _concat_unique(existing, new_batch):
    combined = pd.concat([existing, new_batch], ignore_index=True)
    return combined.drop_duplicates(subset="id")


def _empty_jobs_frame():
    return pd.DataFrame()


def scrape_linkedin_jobs(site_name, search_term, location, focus_titles=None, discard_terms=None):
    """Busca vagas no LinkedIn e salva as vagas novas (ainda não vistas em
    execuções anteriores, e aprovadas no filtro de título) em um CSV com
    timestamp. Tenta completar RESULTS_WANTED vagas novas buscando lotes
    extras quando muitas vierem repetidas.

    focus_titles/discard_terms substituem os padrões de filters.py quando informados.

    Retorna a lista de vagas novas (uma lista de dicts), vazia se não houver
    vagas novas. Também salva o resultado em um CSV com timestamp.
    """
    with _scrape_lock:
        _check_cooldown()
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        output_file = os.path.join(OUTPUT_DIR, f"vagas_{time.strftime('%Y%m%d_%H%M%S')}.csv")
        seen_ids = _load_seen_ids()

        new_jobs = _fetch_new_jobs(site_name, search_term, location, seen_ids, focus_titles, discard_terms)

        if new_jobs.empty:
            logger.warning("Nenhuma vaga nova encontrada (após filtro e deduplicação).")
            open(output_file, "w").close()
            return []

        if len(new_jobs) < RESULTS_WANTED:
            logger.warning(
                f"Consegui {len(new_jobs)} de {RESULTS_WANTED} vagas novas "
                "mesmo tentando completar com lotes extras."
            )

        logger.info(f"{len(new_jobs)} vaga(s) nova(s) no total.")

        try:
            new_jobs.to_csv(output_file, index=False)
        except OSError as e:
            logger.exception(f"Erro ao salvar {output_file}")
            raise ScrapeFailed(f"Erro ao salvar {output_file}: {e}") from e

        return json.loads(new_jobs.to_json(orient="records"))
