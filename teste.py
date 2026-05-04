
# teste.py
from app import cadastrar_cliente, iniciar_conversa, salvar_mensagem, buscar_produtos

# Testa cadastro de cliente
cliente = cadastrar_cliente("João", "joao3@email.com", "senha2234")
print("Cliente:", cliente)

# Testa iniciar conversa
conversa = iniciar_conversa(cliente["id"])
print("Conversa:", conversa)

# Testa salvar mensagem
mensagem = salvar_mensagem(conversa["id"], "cliente", "minha parede está mofando")
print("Mensagem:", mensagem)

# Testa busca de produtos
produtos = buscar_produtos(["mofo", "parede", "umidade"])
print("Produtos:", produtos)