
import streamlit as st
import pandas as pd
from supabase import create_client

st.set_page_config(
    page_title="Sebo Virtual",
    page_icon="📚",
    layout="wide"
)

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def buscar_livros():
    resposta = supabase.table("livros").select("*").order("titulo").execute()
    return resposta.data


def buscar_interesses():
    resposta = supabase.table("interesses").select("*").execute()
    return resposta.data


def buscar_interesses_email(email):
    resposta = (
        supabase.table("interesses")
        .select("*")
        .eq("email", email)
        .execute()
    )
    return resposta.data


st.markdown("""
<style>
.stApp {
    background-color: #FAF8F3;
}
h1, h2, h3 {
    color: #49372B;
}
div.stButton > button {
    background-color: #75543D;
    color: white;
    border-radius: 8px;
}
</style>
""", unsafe_allow_html=True)


st.sidebar.title("📚 Sebo Virtual")
st.sidebar.caption("Sua próxima leitura está aqui!")

pagina = st.sidebar.radio(
    "Navegação",
    ["Consultar livros", "Meus interesses", "Área do funcionário"]
)


if pagina == "Consultar livros":

    st.title("Encontre seu próximo livro")
    st.write("Pesquise nosso catálogo e demonstre interesse.")

    busca = st.text_input("Pesquisar livro ou autor")

    livros = buscar_livros()

    filtrados = [
        livro for livro in livros
        if busca.lower() in livro["titulo"].lower()
        or busca.lower() in livro["autor"].lower()
    ]

    if not filtrados:
        st.info("Nenhum livro encontrado.")

    for livro in filtrados:
        with st.container(border=True):
            col1, col2 = st.columns([3, 1])

            with col1:
                st.subheader(livro["titulo"])
                st.write(f"Autor: {livro['autor']}")

                if livro["quantidade"] > 0:
                    st.success(
                        f"Disponível: {livro['quantidade']} unidade(s)"
                    )
                else:
                    st.warning("Esgotado no momento")

            with col2:
                email = st.text_input(
                    "Seu e-mail",
                    key=f"email_{livro['id_livro']}"
                )

                if st.button(
                    "Tenho interesse",
                    key=f"interesse_{livro['id_livro']}"
                ):
                    email = email.strip().lower()

                    if "@" not in email or "." not in email:
                        st.error("Informe um e-mail válido.")
                    else:
                        existente = (
                            supabase.table("interesses")
                            .select("id_interesse")
                            .eq("email", email)
                            .eq("id_livro", livro["id_livro"])
                            .execute()
                        )

                        if existente.data:
                            st.info(
                                "Você já demonstrou interesse neste livro."
                            )
                        else:
                            status = (
                                "Disponível"
                                if livro["quantidade"] > 0
                                else "Aguardando"
                            )

                            supabase.table("interesses").insert({
                                "id_livro": livro["id_livro"],
                                "email": email,
                                "status": status
                            }).execute()

                            st.success("Interesse registrado!")
                            st.rerun()


elif pagina == "Meus interesses":

    st.title("Meus interesses")
    st.write("Acompanhe os livros que você está esperando.")

    email = st.text_input("Informe seu e-mail")

    if st.button("Consultar interesses"):

        email = email.strip().lower()
        interesses = buscar_interesses_email(email)
        livros = buscar_livros()

        livros_dict = {
            livro["id_livro"]: livro["titulo"]
            for livro in livros
        }

        if interesses:
            for interesse in interesses:
                with st.container(border=True):

                    titulo = livros_dict.get(
                        interesse["id_livro"],
                        "Livro não encontrado"
                    )

                    st.subheader(titulo)

                    if interesse["status"] == "Disponível":
                        st.success("Livro disponível")
                    else:
                        st.warning("Aguardando reposição")
        else:
            st.info(
                "Nenhum interesse encontrado para este e-mail."
            )


elif pagina == "Área do funcionário":

    st.title("Painel administrativo")

    livros = buscar_livros()
    interesses = buscar_interesses()

    col1, col2, col3 = st.columns(3)

    col1.metric("Livros cadastrados", len(livros))
    col2.metric(
        "Unidades em estoque",
        sum(livro["quantidade"] for livro in livros)
    )
    col3.metric("Clientes interessados", len(interesses))

    st.divider()

    aba1, aba2, aba3 = st.tabs([
        "Estoque",
        "Cadastrar livro",
        "Interessados"
    ])

    with aba1:

        st.subheader("Controle de estoque")

        if livros:

            df = pd.DataFrame(livros)

            st.dataframe(
                df[["titulo", "autor", "quantidade"]],
                use_container_width=True,
                hide_index=True
            )

            livro_selecionado = st.selectbox(
                "Selecione um livro",
                livros,
                format_func=lambda livro: livro["titulo"]
            )

            quantidade = st.number_input(
                "Nova quantidade em estoque",
                min_value=0,
                step=1,
                value=livro_selecionado["quantidade"]
            )

            if st.button("Atualizar estoque"):

                supabase.table("livros").update({
                    "quantidade": quantidade
                }).eq(
                    "id_livro",
                    livro_selecionado["id_livro"]
                ).execute()

                novo_status = (
                    "Disponível" if quantidade > 0 else "Aguardando"
                )

                supabase.table("interesses").update({
                    "status": novo_status
                }).eq(
                    "id_livro",
                    livro_selecionado["id_livro"]
                ).execute()

                st.success("Estoque atualizado!")
                st.rerun()

        else:
            st.info("Nenhum livro cadastrado.")


    with aba2:

        st.subheader("Cadastrar novo livro")

        with st.form("cadastro_livro"):

            titulo = st.text_input("Título")
            autor = st.text_input("Autor")
            quantidade = st.number_input(
                "Quantidade",
                min_value=0,
                step=1
            )

            cadastrar = st.form_submit_button("Cadastrar livro")

            if cadastrar:

                if titulo and autor:

                    supabase.table("livros").insert({
                        "titulo": titulo,
                        "autor": autor,
                        "quantidade": quantidade
                    }).execute()

                    st.success("Livro cadastrado!")
                    st.rerun()

                else:
                    st.error("Preencha o título e o autor.")


    with aba3:

        st.subheader("Clientes interessados")

        if interesses:

            livros_dict = {
                livro["id_livro"]: livro["titulo"]
                for livro in livros
            }

            dados = []

            for interesse in interesses:
                dados.append({
                    "Livro": livros_dict.get(
                        interesse["id_livro"],
                        "Livro não encontrado"
                    ),
                    "E-mail": interesse["email"],
                    "Status": interesse["status"],
                    "Data": interesse["criado_em"]
                })

            df = pd.DataFrame(dados)

            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True
            )

        else:
            st.info("Ainda não existem interessados cadastrados.")
