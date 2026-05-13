import psycopg2
from psycopg2.extras import RealDictCursor
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

# ── CONEXÃO ───────────────────────────────────────────

def get_connection():
    return psycopg2.connect(
        host="localhost",
        port=5432,
        database="chatbot",
        user="postgres",
        password="postgres"
    )

# ── MODELO LANGCHAIN ──────────────────────────────────

llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    google_api_key="",
    temperature=0.7
)

# Histórico por sessão (conversa_id → histórico)
store = {}

def get_session_history(session_id: str) -> InMemoryChatMessageHistory:
    if session_id not in store:
        store[session_id] = InMemoryChatMessageHistory()
    return store[session_id]

# Chain com memória
atendente = RunnableWithMessageHistory(llm, get_session_history)

# ── FUNÇÃO PRINCIPAL DE CHAT ──────────────────────────

def chat(conversa_id: int, mensagem_usuario: str, system_prompt: str = None):
    """
    Envia mensagem para o atendente e salva no banco.
    Retorna a resposta do modelo.
    """
    # Salva mensagem do usuário no banco
    salvar_mensagem(conversa_id, "cliente", mensagem_usuario)

    # Monta config da sessão
    config = {"configurable": {"session_id": str(conversa_id)}}

    # Injeta system prompt na primeira mensagem da sessão
    historico = get_session_history(str(conversa_id))
    if not historico.messages and system_prompt:
        historico.add_message(SystemMessage(content=system_prompt))

    # Chama o modelo
    resposta = atendente.invoke(
        [HumanMessage(content=mensagem_usuario)],
        config=config
    )

    texto_resposta = resposta.content

    # Salva resposta do atendente no banco
    salvar_mensagem(conversa_id, "atendente", texto_resposta)

    return texto_resposta

# ── INSERÇÕES (sem mudança) ────────────────────────────

def cadastrar_cliente(nome, email, senha_hash):
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "INSERT INTO clientes (nome, email, senha) VALUES (%s, %s, %s) RETURNING *",
                (nome, email, senha_hash)
            )
            return cur.fetchone()

def iniciar_conversa(cliente_id):
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "INSERT INTO conversas (cliente_id) VALUES (%s) RETURNING *",
                (cliente_id,)
            )
            return cur.fetchone()

def encerrar_conversa(conversa_id):
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "UPDATE conversas SET encerrada_em = CURRENT_TIMESTAMP WHERE id = %s RETURNING *",
                (conversa_id,)
            )
            return cur.fetchone()

def salvar_mensagem(conversa_id, remetente, conteudo):
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "INSERT INTO mensagens (conversa_id, remetente, conteudo) VALUES (%s, %s, %s) RETURNING *",
                (conversa_id, remetente, conteudo)
            )
            return cur.fetchone()

def registrar_recomendacao(conversa_id, produto_id, mensagem_id):
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "INSERT INTO recomendacoes (conversa_id, produto_id, mensagem_id) VALUES (%s, %s, %s) RETURNING *",
                (conversa_id, produto_id, mensagem_id)
            )
            return cur.fetchone()

def cadastrar_produto(nome, descricao, categoria, preco, quantidade_estoque):
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "INSERT INTO produtos (nome, descricao, categoria, preco, quantidade_estoque) VALUES (%s, %s, %s, %s, %s) RETURNING *",
                (nome, descricao, categoria, preco, quantidade_estoque)
            )
            return cur.fetchone()
        
# ── BUSCAS ──────────────────────────────────────────

def buscar_produtos(palavras_chave):
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            filtros = " OR ".join(
                [f"descricao ILIKE %s OR categoria ILIKE %s" for _ in palavras_chave]
            )
            valores = [val for p in palavras_chave for val in (f"%{p}%", f"%{p}%")]
            cur.execute(
                f"SELECT * FROM produtos WHERE ({filtros}) AND quantidade_estoque > 0 AND ativo = TRUE",
                valores
            )
            return cur.fetchall()

def buscar_historico(cliente_id):
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT m.remetente, m.conteudo, m.enviada_em
                FROM mensagens m
                JOIN conversas c ON c.id = m.conversa_id
                WHERE c.cliente_id = %s
                ORDER BY m.enviada_em ASC
            """, (cliente_id,))
            return cur.fetchall()