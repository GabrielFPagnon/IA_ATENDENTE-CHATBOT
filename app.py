import psycopg2
from psycopg2.extras import RealDictCursor
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# ── CONEXÃO ───────────────────────────────────────────

def get_connection():
    return psycopg2.connect(
        host="localhost",
        port=5432,
        database="",
        user="postgres",
        password=""
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

# Proteção contra Prompt Injection (MUDANÇA)
prompt = ChatPromptTemplate.from_messages([
    ("system", """Você é o melhor assistente de vendas da nossa loja.
    
    DIRETRIZES:
    1. Recomende APENAS produtos listados no [CONTEXTO DE PRODUTOS].
    2. Nunca invente preços, estoques ou produtos.
    3. Seja conciso e direto.
    
    [CONTEXTO DE PRODUTOS]
    {contexto_produtos}
    """),
    MessagesPlaceholder(variable_name="historico"),
    ("human", "{mensagem_usuario}")
])

chain = prompt | llm

atendente = RunnableWithMessageHistory(
    chain,
    get_session_history,
    input_messages_key="mensagem_usuario",
    history_messages_key="historico"
)

# ── FUNÇÃO PRINCIPAL DE CHAT ────────────────────────── (MUDANÇA)

def extrair_palavras_chave(mensagem: str) -> list:
    palavras_ignoradas = {"eu", "quero", "um", "uma", "o", "a", "de", "para"}
    return [p for p in mensagem.lower().split() if p not in palavras_ignoradas]

def chat(conversa_id: int, mensagem_usuario: str):
    """
    Envia mensagem para o atendente, injetando dados reais do Postgres no prompt.
    """
    salvar_mensagem(conversa_id, "cliente", mensagem_usuario)

    # Busca no Postgres
    palavras = extrair_palavras_chave(mensagem_usuario)
    produtos_encontrados = buscar_produtos(palavras) if palavras else []
    
    # Formata o prompt
    if produtos_encontrados:
        texto_contexto = "\n".join([
            f"- {p['nome']} | Categoria: {p['categoria']} | Preço: R${p['preco']} | Estoque: {p['quantidade_estoque']}"
            for p in produtos_encontrados
        ])
    else:
        texto_contexto = "Nenhum produto relevante encontrado no banco para esta mensagem."

    # Chama o modelo
    config = {"configurable": {"session_id": str(conversa_id)}}
    
    resposta = atendente.invoke(
        {
            "mensagem_usuario": mensagem_usuario,
            "contexto_produtos": texto_contexto # Injetando o Postgres no Prompt!
        },
        config=config
    )

    texto_resposta = resposta.content
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