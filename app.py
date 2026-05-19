"""
app.py — Camada de API REST (FastAPI)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Expõe os recursos do atendente.py via HTTP.

Endpoints:
  POST /clientes                  → cadastrar cliente
  POST /conversas                 → iniciar conversa
  DELETE /conversas/{id}          → encerrar conversa
  POST /conversas/{id}/mensagens  → enviar mensagem (chat principal)
  GET  /clientes/{id}/historico   → buscar histórico
  POST /produtos                  → cadastrar produto
  GET  /produtos/buscar           → buscar produtos por palavras-chave

Parâmetros de chat:
  modo        → tecnico | resumido | professor | detalhado | suporte_tecnico
  tipo_prompt → simples | estruturado | especializado

Dual-AI:
  Gemini 1.5 Flash → vendas, recomendações, catálogo
  Groq Llama 3.3   → suporte técnico, comparações, análises
"""

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, EmailStr
from typing import Optional

from atendente import (
    # Enums
    ModoIA,
    TipoPrompt,
    # Chat
    chat,
    # CRUD
    cadastrar_cliente,
    iniciar_conversa,
    encerrar_conversa,
    salvar_mensagem,
    cadastrar_produto,
    # Buscas
    buscar_produtos,
    buscar_historico,
    extrair_palavras_chave,
)

# ══════════════════════════════════════════════════════════════════
# APP
# ══════════════════════════════════════════════════════════════════

app = FastAPI(
    title="Atendente Virtual — Dual AI",
    description=(
        "API de atendimento com Gemini (vendas) + Groq (suporte técnico). "
        "Suporta 5 modos de IA e 3 tipos de prompt com proteções de segurança."
    ),
    version="2.0.0",
)


# ══════════════════════════════════════════════════════════════════
# SCHEMAS
# ══════════════════════════════════════════════════════════════════

class ClienteCreate(BaseModel):
    nome: str
    email: EmailStr
    senha_hash: str


class ConversaCreate(BaseModel):
    cliente_id: int


class MensagemCreate(BaseModel):
    mensagem: str
    modo: ModoIA = ModoIA.DETALHADO
    tipo_prompt: TipoPrompt = TipoPrompt.ESTRUTURADO


class ProdutoCreate(BaseModel):
    nome: str
    descricao: str
    categoria: str
    preco: float
    quantidade_estoque: int


# ══════════════════════════════════════════════════════════════════
# CLIENTES
# ══════════════════════════════════════════════════════════════════

@app.post("/clientes", summary="Cadastrar novo cliente")
def criar_cliente(body: ClienteCreate):
    """
    Cadastra um novo cliente no banco de dados.
    """
    try:
        cliente = cadastrar_cliente(body.nome, body.email, body.senha_hash)
        return {"sucesso": True, "cliente": cliente}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/clientes/{cliente_id}/historico", summary="Histórico de mensagens do cliente")
def historico_cliente(cliente_id: int):
    """
    Retorna todas as mensagens de todas as conversas de um cliente.
    """
    try:
        historico = buscar_historico(cliente_id)
        return {"sucesso": True, "historico": historico}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ══════════════════════════════════════════════════════════════════
# CONVERSAS
# ══════════════════════════════════════════════════════════════════

@app.post("/conversas", summary="Iniciar nova conversa")
def nova_conversa(body: ConversaCreate):
    """
    Abre uma nova conversa para um cliente.
    """
    try:
        conversa = iniciar_conversa(body.cliente_id)
        return {"sucesso": True, "conversa": conversa}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/conversas/{conversa_id}", summary="Encerrar conversa")
def fechar_conversa(conversa_id: int):
    """
    Registra o encerramento de uma conversa.
    """
    try:
        conversa = encerrar_conversa(conversa_id)
        if not conversa:
            raise HTTPException(status_code=404, detail="Conversa não encontrada.")
        return {"sucesso": True, "conversa": conversa}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ══════════════════════════════════════════════════════════════════
# CHAT — endpoint principal
# ══════════════════════════════════════════════════════════════════

@app.post("/conversas/{conversa_id}/mensagens", summary="Enviar mensagem ao atendente")
def enviar_mensagem(conversa_id: int, body: MensagemCreate):
    """
    Envia uma mensagem e recebe a resposta da IA.

    **Modos disponíveis:**
    - `tecnico` — terminologia precisa, specs e unidades
    - `resumido` — máximo 2-3 frases, direto ao ponto
    - `professor` — explica como para leigos, usa analogias
    - `detalhado` — análise completa com prós, contras e recomendação
    - `suporte_tecnico` — diagnóstico e solução passo a passo (sempre usa Groq)

    **Tipos de prompt:**
    - `simples` — estrutura mínima, resposta direta
    - `estruturado` — persona Sofia + regras + catálogo
    - `especializado` — chain-of-thought + few-shot + restrições rígidas

    **Roteamento dual-AI:**
    - Gemini → perguntas de vendas, recomendações, catálogo
    - Groq → suporte técnico, comparações, análises técnicas
    """
    try:
        resultado = chat(
            conversa_id=conversa_id,
            mensagem_usuario=body.mensagem,
            modo=body.modo,
            tipo_prompt=body.tipo_prompt,
        )
        return {"sucesso": True, **resultado}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════════
# PRODUTOS
# ══════════════════════════════════════════════════════════════════

@app.post("/produtos", summary="Cadastrar produto")
def criar_produto(body: ProdutoCreate):
    """
    Cadastra um novo produto no catálogo.
    """
    try:
        produto = cadastrar_produto(
            body.nome,
            body.descricao,
            body.categoria,
            body.preco,
            body.quantidade_estoque,
        )
        return {"sucesso": True, "produto": produto}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/produtos/buscar", summary="Buscar produtos por palavras-chave")
def buscar(q: str = Query(..., description="Termos de busca separados por espaço")):
    """
    Busca produtos ativos no banco por palavras-chave.
    Ignora stop words automaticamente.
    """
    try:
        palavras = extrair_palavras_chave(q)
        if not palavras:
            return {"sucesso": True, "produtos": [], "aviso": "Nenhuma palavra-chave relevante encontrada."}
        produtos = buscar_produtos(palavras)
        return {"sucesso": True, "total": len(produtos), "produtos": produtos}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))