
import streamlit as st
import pandas as pd
from supabase import create_client

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)


st.set_page_config(
    page_title="Sebo Virtual",
    page_icon="📚",
    layout="wide"
)

if "livros" not in st.session_state:
    st.session_state.livros = [
        {"id": 1, "titulo": "Dom Casmurro", "autor": "Machado de Assis", "preco": 25.00, "estoque": 2},
        {"id": 2, "titulo": "O Pequeno Príncipe", "autor": "Antoine de Saint-Exupéry", "preco": 20.00, "estoque": 0},
        {"id": 3, "titulo": "1984", "autor": "George Orwell", "preco": 30.00, "estoque": 3},
        {"id": 4, "titulo": "Capitães da Areia", "autor": "Jorge Amado", "preco": 22.00, "estoque": 0}
    ]

if "interesses" not in st.session_state:
    st.session_state.interesses = []

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

    livros = st.session_state.livros

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
                st.write(f"Preço: R$ {livro['preco']:.2f}")

                if livro["estoque"] > 0:
                    st.success(f"Disponível: {livro['estoque']} unidade(s)")
                else:
                    st.warning("Esgotado no momento")

            with col2:
                email = st.text_input(
                    "Seu e-mail",
                    key=f"email_{livro['id']}"
                )

                if st.button("Tenho interesse", key=f"interesse_{livro['id']}"):
                    if "@" not in email or "." not in email:
                        st.error("Informe um e-mail válido.")
                    else:
                        existente = any(
                            i["email"] == email and i["livro_id"] == livro["id"]
                            for i in st.session_state.interesses
                        )

                        if existente:
                            st.info("Você já demonstrou interesse neste livro.")
                        else:
                            status = "Disponível" if livro["estoque"] > 0 else "Aguardando"

                            st.session_state.interesses.append({
                                "livro_id": livro["id"],
                                "titulo": livro["titulo"],
                                "email": email,
                                "status": status
                            })

                            if status == "Disponível":
                                st.success("Livro disponível! Você receberá um aviso.")
                            else:
                                st.success("Interesse registrado! Avisaremos quando chegar.")

elif pagina == "Meus interesses":

    st.title("Meus interesses")
    st.write("Acompanhe os livros que você está esperando.")

    email = st.text_input("Informe seu e-mail")

    if st.button("Consultar interesses"):
        interesses = [
            i for i in st.session_state.interesses
            if i["email"].lower() == email.lower()
        ]

        if interesses:
            for interesse in interesses:
                with st.container(border=True):
                    st.subheader(interesse["titulo"])

                    if interesse["status"] == "Disponível":
                        st.success("Livro disponível")
                    else:
                        st.warning("Aguardando reposição")
        else:
            st.info("Nenhum interesse encontrado para este e-mail.")

elif pagina == "Área do funcionário":

    st.title("Painel administrativo")

    livros = st.session_state.livros

    col1, col2, col3 = st.columns(3)

    col1.metric("Livros cadastrados", len(livros))
    col2.metric("Unidades em estoque", sum(l["estoque"] for l in livros))
    col3.metric("Clientes interessados", len(st.session_state.interesses))

    st.divider()

    aba1, aba2, aba3 = st.tabs([
        "Estoque",
        "Cadastrar livro",
        "Interessados"
    ])

    with aba1:
        st.subheader("Controle de estoque")

        df = pd.DataFrame(livros)
        st.dataframe(
            df[["titulo", "autor", "preco", "estoque"]],
            use_container_width=True,
            hide_index=True
        )

        livro_selecionado = st.selectbox(
            "Selecione um livro",
            livros,
            format_func=lambda l: l["titulo"]
        )

        quantidade = st.number_input(
            "Nova quantidade em estoque",
            min_value=0,
            step=1,
            value=livro_selecionado["estoque"]
        )

        if st.button("Atualizar estoque"):
            livro_selecionado["estoque"] = quantidade

            if quantidade > 0:
                for interesse in st.session_state.interesses:
                    if interesse["livro_id"] == livro_selecionado["id"]:
                        interesse["status"] = "Disponível"

            st.success("Estoque atualizado!")
            st.rerun()

    with aba2:
        st.subheader("Cadastrar novo livro")

        with st.form("cadastro_livro"):
            titulo = st.text_input("Título")
            autor = st.text_input("Autor")
            preco = st.number_input("Preço", min_value=0.0, step=1.0)
            estoque = st.number_input("Quantidade", min_value=0, step=1)

            cadastrar = st.form_submit_button("Cadastrar livro")

            if cadastrar:
                if titulo and autor:
                    novo_id = max([l["id"] for l in livros], default=0) + 1

                    st.session_state.livros.append({
                        "id": novo_id,
                        "titulo": titulo,
                        "autor": autor,
                        "preco": preco,
                        "estoque": estoque
                    })

                    st.success("Livro cadastrado!")
                    st.rerun()
                else:
                    st.error("Preencha o título e o autor.")

    with aba3:
        st.subheader("Clientes interessados")

        if st.session_state.interesses:
            df = pd.DataFrame(st.session_state.interesses)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("Ainda não existem interessados cadastrados.")
