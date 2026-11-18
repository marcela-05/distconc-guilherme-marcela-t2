import uuid

import pandas as pd
import requests
import streamlit as st
from supabase import create_client


st.set_page_config(page_title="Livraria Virtual", page_icon="📚", layout="wide")

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

# Endereços das rotas do API Gateway.
API_CONSULTAR_LIVRO = st.secrets.get("API_CONSULTAR_LIVRO", "")
API_REGISTRAR_INTERESSE = st.secrets.get("API_REGISTRAR_INTERESSE", "")
API_CADASTRAR_LIVRO = st.secrets.get("API_CADASTRAR_LIVRO", "")
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def buscar_livros():
    return supabase.table("livros").select("*").order("titulo").execute().data


def buscar_interesses():
    return supabase.table("interesses").select("*").execute().data


def buscar_interesses_email(email):
    return (
        supabase.table("interesses")
        .select("id_livro,status")
        .eq("email", email)
        .execute()
        .data
    )


def chamar_lambda(url, dados):
    if not url:
        return {"ok": False, "mensagem": "A rota do API Gateway ainda não foi configurada."}

    try:
        resposta = requests.post(url, json=dados, timeout=15)
        conteudo = resposta.json()

        # Algumas integrações devolvem o body da Lambda como uma string JSON.
        codigo_lambda = conteudo.get("statusCode", resposta.status_code) if isinstance(conteudo, dict) else resposta.status_code
        if isinstance(conteudo, dict) and "body" in conteudo:
            corpo = conteudo["body"]
            if isinstance(corpo, str):
                import json
                corpo = json.loads(corpo)
            conteudo = corpo

        if not isinstance(conteudo, dict):
            return {"ok": False, "mensagem": "A API devolveu uma resposta inesperada."}

        mensagem = conteudo.get("mensagem", "Operação concluída.")
        return {"ok": resposta.ok and 200 <= int(codigo_lambda) < 300,
                "mensagem": mensagem, "dados": conteudo}

    except (requests.RequestException, ValueError) as erro:
        return {"ok": False, "mensagem": f"Não foi possível acessar a API: {erro}"}


def consultar_livro(id_livro, email):
    # Lambda ConsultarLivro
    return chamar_lambda(API_CONSULTAR_LIVRO, {"id_livro": id_livro, "email": email})


def registrar_interesse(id_livro, email):
    # Lambda RegistrarInteresse
    return chamar_lambda(API_REGISTRAR_INTERESSE, {"id_livro": id_livro, "email": email})


def receber_exemplares(id_livro, quantidade):
    # Lambda CadastrarLivro
    return chamar_lambda(
        API_CADASTRAR_LIVRO,
        {"id_livro": id_livro, "quantidade_adicionada": quantidade},
    )


def cadastrar_novo_livro(titulo, autor, quantidade):
    # Cadastro inicial direto pelo servidor Streamlit, protegido pela senha administrativa.
    # A Lambda CadastrarLivro atual só adiciona exemplares de títulos existentes.
    supabase.table("livros").insert(
        {
            "id_livro": str(uuid.uuid4()),
            "titulo": titulo,
            "autor": autor,
            "quantidade": quantidade,
        }
    ).execute()
    return {"ok": True, "mensagem": "Livro cadastrado com sucesso."}


def mostrar_resultado(resultado):
    if resultado["ok"]:
        st.success(resultado["mensagem"])
    else:
        st.error(resultado["mensagem"])


st.markdown(
    """
    <style>
    .stApp { background-color: #FAF8F3; }
    h1, h2, h3 { color: #49372B; }
    div.stButton > button { background-color: #75543D; color: white; border-radius: 8px; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.sidebar.title("Livraria Virtual")
st.sidebar.caption("Encontre sua próxima leitura")
pagina = st.sidebar.radio(
    "Navegação", ["Consultar livros", "Meus interesses", "Área do funcionário"]
)

if pagina == "Consultar livros":
    st.title("Consultar livros")
    st.write("Pesquise o catálogo e informe seu interesse em um livro.")
    busca = st.text_input("Pesquisar por título ou autor")

    try:
        livros = buscar_livros()
    except Exception:
        st.error("Não foi possível carregar os livros do Supabase.")
        st.stop()

    filtrados = [
        livro for livro in livros
        if busca.lower() in livro["titulo"].lower()
        or busca.lower() in livro["autor"].lower()
    ]

    if not filtrados:
        st.info("Nenhum livro encontrado.")

    for livro in filtrados:
        with st.container(border=True):
            col1, col2 = st.columns([3, 2])
            with col1:
                st.subheader(livro["titulo"])
                st.write(f"Autor: {livro['autor']}")
                if livro["quantidade"] > 0:
                    st.success(f"Disponível: {livro['quantidade']} unidade(s)")
                else:
                    st.warning("Esgotado no momento")

            with col2:
                email = st.text_input("Seu e-mail", key=f"email_{livro['id_livro']}")
                if st.button("Tenho interesse", key=f"botao_{livro['id_livro']}"):
                    email = email.strip().lower()
                    if "@" not in email or "." not in email.split("@")[-1]:
                        st.error("Informe um e-mail válido.")
                    elif livro["quantidade"] > 0:
                        resultado = consultar_livro(livro["id_livro"], email)
                        mostrar_resultado(resultado)
                        if resultado["ok"]:
                            st.info("O envio do aviso por e-mail ainda depende da integração com o SNS.")
                    else:
                        mostrar_resultado(registrar_interesse(livro["id_livro"], email))

elif pagina == "Meus interesses":
    st.title("Meus interesses")
    st.write("Confira as solicitações registradas para seu e-mail.")
    st.caption("Consulta demonstrativa: para publicar a aplicação, será necessário verificar a identidade do cliente.")
    email = st.text_input("Informe seu e-mail")

    if st.button("Consultar interesses"):
        email = email.strip().lower()
        if "@" not in email or "." not in email.split("@")[-1]:
            st.error("Informe um e-mail válido.")
        else:
            try:
                interesses = buscar_interesses_email(email)
                nomes = {livro["id_livro"]: livro["titulo"] for livro in buscar_livros()}
                if not interesses:
                    st.info("Nenhum interesse encontrado para este e-mail.")
                for interesse in interesses:
                    with st.container(border=True):
                        st.subheader(nomes.get(interesse["id_livro"], "Livro não encontrado"))
                        if interesse["status"] == "avisado":
                            st.success("Aviso solicitado")
                        else:
                            st.warning("Aguardando reposição")
            except Exception:
                st.error("Não foi possível consultar os interesses.")

elif pagina == "Área do funcionário":
    st.title("Área do funcionário")
    if not ADMIN_PASSWORD:
        st.warning("Configure ADMIN_PASSWORD nos secrets do Streamlit para liberar esta área.")
        st.stop()

    if not st.session_state.get("funcionario_autenticado", False):
        with st.form("acesso_funcionario"):
            senha = st.text_input("Senha do funcionário", type="password")
            entrar = st.form_submit_button("Entrar")
            if entrar:
                if senha == ADMIN_PASSWORD:
                    st.session_state["funcionario_autenticado"] = True
                    st.rerun()
                else:
                    st.error("Senha incorreta.")
        st.stop()

    if st.button("Sair da área do funcionário"):
        st.session_state["funcionario_autenticado"] = False
        st.rerun()

    try:
        livros = buscar_livros()
        interesses = buscar_interesses()
    except Exception:
        st.error("Não foi possível carregar os dados administrativos.")
        st.stop()

    col1, col2, col3 = st.columns(3)
    col1.metric("Livros cadastrados", len(livros))
    col2.metric("Unidades em estoque", sum(livro["quantidade"] for livro in livros))
    col3.metric("Interesses registrados", len(interesses))
    st.divider()

    aba1, aba2, aba3 = st.tabs(["Estoque", "Cadastrar livro", "Interessados"])

    with aba1:
        st.subheader("Controle de estoque")
        if livros:
            st.dataframe(
                pd.DataFrame(livros)[["titulo", "autor", "quantidade"]],
                use_container_width=True,
                hide_index=True,
            )
            livro_selecionado = st.selectbox(
                "Selecione um livro", livros, format_func=lambda item: item["titulo"]
            )
            quantidade = st.number_input(
                "Quantidade de exemplares recebidos", min_value=1, step=1, value=1
            )
            if st.button("Adicionar ao estoque"):
                mostrar_resultado(receber_exemplares(livro_selecionado["id_livro"], int(quantidade)))
        else:
            st.info("Nenhum livro cadastrado.")

    with aba2:
        st.subheader("Cadastrar novo livro")
        with st.form("cadastro_livro"):
            titulo = st.text_input("Título")
            autor = st.text_input("Autor")
            quantidade = st.number_input("Quantidade inicial", min_value=0, step=1, value=0)
            cadastrar = st.form_submit_button("Cadastrar livro")
            if cadastrar:
                if not titulo.strip() or not autor.strip():
                    st.error("Preencha o título e o autor.")
                else:
                    try:
                        mostrar_resultado(
                            cadastrar_novo_livro(titulo.strip(), autor.strip(), int(quantidade))
                        )
                    except Exception:
                        st.error("Não foi possível cadastrar o livro.")

    with aba3:
        st.subheader("Clientes interessados")
        if interesses:
            nomes = {livro["id_livro"]: livro["titulo"] for livro in livros}
            dados = [
                {
                    "Livro": nomes.get(interesse["id_livro"], "Livro não encontrado"),
                    "E-mail": interesse["email"],
                    "Status": interesse["status"],
                    "Data": interesse["criado_em"],
                }
                for interesse in interesses
            ]
            st.dataframe(pd.DataFrame(dados), use_container_width=True, hide_index=True)
        else:
            st.info("Ainda não existem interessados cadastrados.")
