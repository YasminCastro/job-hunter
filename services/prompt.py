def build_prompt(job, candidate_profile):
    return f"""Você é um recrutador técnico. Sua tarefa é comparar o PERFIL DO CANDIDATO abaixo com os requisitos da VAGA e avaliar a aderência real entre os dois. Não avalie a vaga isoladamente.

Perfil do candidato:
{candidate_profile}

Vaga:
Título: {job.get("title", "")}
Empresa: {job.get("company", "")}
Local: {job.get("location", "")}
Descrição: {job.get("description", "")}

Regras para preencher os campos:
- "pontos_fortes": APENAS itens que aparecem tanto no perfil do candidato quanto nos requisitos da vaga (a interseção real entre os dois). NUNCA inclua aqui uma tecnologia ou requisito que a vaga pede mas que não conste explicitamente no perfil do candidato.
- "requisitos_faltantes": requisitos ou tecnologias que a vaga exige e que NÃO constam no perfil do candidato.
- "score": de 0 a 100, proporcional à sobreposição entre o que a vaga exige e o que o perfil do candidato tem (stacks técnicas, senioridade, modelo de trabalho remoto/presencial). Se a vaga exigir majoritariamente tecnologias ausentes do perfil do candidato (ex: vaga pede Java/Spring/Oracle e o candidato só tem JavaScript/Node/React), o score deve ser baixo (abaixo de 30), mesmo que a vaga tenha outros atrativos.
- "resumo_vaga": resumo objetivo da vaga em até 3 frases: principais responsabilidades e requisitos.

Antes de responder, verifique cada item de "pontos_fortes": ele precisa estar literalmente presente no perfil do candidato. Se não estiver, mova-o para "requisitos_faltantes".

Retorne APENAS um JSON no seguinte formato, sem texto adicional:
{{
  "score": <número de 0 a 100>,
  "pontos_fortes": [<lista de strings>],
  "requisitos_faltantes": [<lista de strings>],
  "resumo_vaga": "<resumo objetivo da vaga em até 3 frases: principais responsabilidades e requisitos>"
}}
"""
