import json
import logging
import os
import threading
import time

import requests

from services.prompt import build_prompt

logger = logging.getLogger(__name__)

_ollama_lock = threading.Lock()

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")
OLLAMA_TIMEOUT = int(os.environ.get("OLLAMA_TIMEOUT", "120"))

EMPTY_ANALYSIS = {
    "score": 0,
    "pontos_fortes": [],
    "requisitos_faltantes": [],
    "resumo_vaga": "Erro ao processar resposta da IA",
}


class OllamaTimeout(Exception):
    """Ollama não respondeu dentro do timeout configurado."""


class OllamaRequestFailed(Exception):
    """Erro ao chamar a API do Ollama."""


def _call_ollama(prompt, job_id):
    logger.info("Vaga %s: aguardando lock do Ollama (outra análise pode estar em andamento)", job_id)

    with _ollama_lock:
        logger.info(
            "Vaga %s: lock obtido, enviando prompt para %s modelo=%s (timeout=%ss)",
            job_id, OLLAMA_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT,
        )
        start = time.monotonic()

        try:
            response = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "format": "json",
                    "stream": False,
                },
                timeout=OLLAMA_TIMEOUT,
            )
            response.raise_for_status()
        except requests.exceptions.Timeout as e:
            logger.error(
                "Vaga %s: timeout (%ss) ao chamar Ollama após %.1fs de espera",
                job_id, OLLAMA_TIMEOUT, time.monotonic() - start,
            )
            raise OllamaTimeout(f"Ollama não respondeu em {OLLAMA_TIMEOUT}s") from e
        except requests.exceptions.HTTPError as e:
            body = e.response.text if e.response is not None else ""
            logger.error("Vaga %s: erro HTTP do Ollama (%s): %s", job_id, OLLAMA_URL, body)
            raise OllamaRequestFailed(f"Erro ao chamar Ollama: {e} - {body}") from e
        except requests.exceptions.RequestException as e:
            logger.exception("Vaga %s: erro ao chamar Ollama (%s)", job_id, OLLAMA_URL)
            raise OllamaRequestFailed(f"Erro ao chamar Ollama: {e}") from e

        elapsed = time.monotonic() - start
        logger.info("Vaga %s: resposta do Ollama recebida em %.1fs", job_id, elapsed)

    return response.json().get("response", "")


def _analyze_job(job, candidate_profile):
    job_id = job.get("id")
    prompt = build_prompt(job, candidate_profile)

    raw_text = _call_ollama(prompt, job_id)

    try:
        analysis = json.loads(raw_text)
    except (ValueError, TypeError):
        logger.error("Resposta da IA não é JSON válido para a vaga %s: %r", job_id, raw_text)
        analysis = EMPTY_ANALYSIS

    logger.info("Vaga %s: análise concluída, score=%s", job_id, analysis.get("score", 0))

    return {
        "jobId": job_id,
        "title": job.get("title") or "Título não informado",
        "company": job.get("company") or "Empresa não informada",
        "location": job.get("location") or "",
        "url": job.get("job_url") or "",
        "score": analysis.get("score", 0),
        "pontos_fortes": analysis.get("pontos_fortes", []),
        "requisitos_faltantes": analysis.get("requisitos_faltantes", []),
        "resumo_vaga": analysis.get("resumo_vaga", ""),
    }


def handle_analyze_request(data):
    job = data.get("job")
    candidate_profile = data.get("candidate_profile")

    logger.info("Request recebida em /analyze para a vaga %s", (job or {}).get("id") if isinstance(job, dict) else None)

    errors = []
    if not isinstance(job, dict) or not job:
        errors.append("job deve ser um objeto com os campos da vaga")
    if not isinstance(candidate_profile, str) or not candidate_profile.strip():
        errors.append("candidate_profile deve ser uma string não vazia")

    if errors:
        logger.warning("Request inválida em /analyze: %s", errors)
        return {"errors": errors}, 400

    try:
        result = _analyze_job(job, candidate_profile)
    except OllamaTimeout as e:
        return {"errors": [str(e)]}, 504
    except OllamaRequestFailed as e:
        return {"errors": [str(e)]}, 502
    except Exception:
        logger.exception("Erro inesperado em /analyze")
        return {"errors": ["Erro inesperado ao analisar a vaga"]}, 500

    return result, 200
