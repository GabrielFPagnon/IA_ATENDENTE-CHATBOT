import psycopg2
from psycopg2.extras import RealDictCursor
from google import genai

# Conexão com o banco
def get_connection():
    return psycopg2.connect(
        host="localhost",
        port=5432,
        database="chatbot",
        user="postgres",
        password="postgres"
    )

# Cliente Gemini
client = genai.Client(api_key="")

# ── INSERÇÕES ──────────────────────────────────────────

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