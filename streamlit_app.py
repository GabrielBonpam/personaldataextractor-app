import streamlit as st
import base64
import requests
import openai
from PIL import Image
import json
import pandas as pd
import re
import pytesseract


# --- Configuração de Página ---
st.set_page_config(page_title="Leitor de Documentos Inteligentes", layout="wide")

# Carrega chave da OpenAI dos secrets ou input
openai.api_key = st.secrets.get("OPENAI_API_KEY") or st.text_input("Informe sua chave da OpenAI", type="password")

# Inicializa controle de navegação
if "page" not in st.session_state:
    st.session_state.page = "home"

# Função: Home Page
def show_home():
    st.title("📄 Extração de Documentos Inteligentes com IA e OCR")
    st.write("Este aplicativo permite extrair dados estruturados de documentos brasileiros (RG, CNH e/ou Certidão de Nascimento).")
    st.write("### Aplicações possíveis:")
    st.markdown(
        "- Automação de cadastro de clientes em sistemas CRM\n"
        "- Validação e conferência de documentos em processos bancários\n"
        "- Digitalização e indexação de arquivos de RH\n"
        "- Triagem automática de documentos em centrais de atendimento"
    )
    st.markdown("""
    <style>
    .stButton>button {
        background-color: #4CAF50 !important;
        color: white !important;
        padding: 10px 20px !important;
        border: none !important;
        border-radius: 5px !important;
        cursor: pointer !important;
    }
    </style>
    """, unsafe_allow_html=True)
    st.markdown("<div style='text-align:center; margin-top:20px;'>", unsafe_allow_html=True)
    if st.button("Iniciar Demonstração"):
            st.session_state.page = "app"
    st.markdown("</div>", unsafe_allow_html=True)

# Função: Converter imagem para base64
def image_to_base64(file):
    return base64.b64encode(file.read()).decode("utf-8")

# Função: Fallback OCR caso API falhe
def ocr_fallback(file) -> str:
    img = Image.open(file)
    text = pytesseract.image_to_string(img, lang='por')
    return text


def extract_document_fields_with_openai(image_b64: str, file) -> dict:
    headers = {
        "Authorization": f"Bearer {openai.api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gpt-4o",
        "messages": [
            {"role": "user", "content": [
                {"type": "text", "text": (
                            "Você é um extrator de documentos brasileiros. "
                            "A imagem pode ser um RG, CNH ou Certidão de Nascimento. Classifique o tipo de documento (RG, CNH ou Certidão de Nascimento) e depois extraia os dados relevantes. "
                            "Extraia os seguintes campos, se disponíveis:\n\n"
                            "- Tipo de Documento\n"
                            "- Nome\n"
                            "- Data de Nascimento\n"
                            "- Número do documento (RG ou CNH)\n"
                            "- CPF (se presente)\n"
                            "- Órgão emissor (RG) ou Categoria (CNH)\n"
                            "- Nome da mãe (Certidão)\n\n"
                            "- Nome do pai (Certidão)\n\n"
                            "Responda SOMENTE com um objeto JSON válido e nada mais. Não inclua explicações. Envolva o conteúdo com três crases seguidas de json no início e três crases no fim, assim:\n```json\n{{ JSON aqui }}\n```"
                        )},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
            ]}
        ],
        "max_tokens": 1000
    }
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
    except Exception:
        # API falhou, executa OCR
        text = ocr_fallback(file)
        return {"Erro": "Fallback OCR", "Texto OCR": text}

    raw = response.json()["choices"][0]["message"]["content"]
    match = re.search(r"\{[\s\S]*\}", raw)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    # Se parsing falhar, fallback OCR
    text = ocr_fallback(file)
    return {"Erro": "JSON inválido, usado OCR", "Texto OCR": text}

# Função: Demo de extração
def show_app():

    st.header("📄 Envio de documentos para extração de dados")
    files = st.file_uploader(
        "📷 Envie imagens (RG, CNH ou Certidão de Nascimento)", type=["png","jpg","jpeg"], accept_multiple_files=True)
    if files and openai.api_key:
        results = []
        for idx, file in enumerate(files, start=1):
            st.subheader(f"Documento {idx} de {len(files)}")
            col1, col2 = st.columns([1,2])
            with col1:
                st.image(file, width=250)
            with col2:
                b64 = image_to_base64(file)
                with st.spinner("📄📷 Analisando e extraindo dados dos documentos enviados..."):
                    out = extract_document_fields_with_openai(b64, file)
                    results.append(out)
                    st.success("Processado com sucesso.")
                    with st.expander("📋 Resultado individual", expanded=False):
                        st.json(out)
        st.write("---")
        st.subheader("Resultado Consolidado")
        st.json(results)

        parsed_results = []
        for res in results:
            if "Tipo de Documento" in res:
                parsed_results.append(res)
            elif "resposta" in res:
                raw = res["resposta"]
                m = re.search(r"\{[\s\S]*\}", raw)
                if m:
                    try:
                        parsed = json.loads(m.group())
                        parsed_results.append(parsed)
                    except json.JSONDecodeError:
                        pass

        doc_type_counts = {}
        for pr in parsed_results:
            dtype = pr.get("Tipo de Documento")
            if dtype:
                doc_type_counts[dtype] = doc_type_counts.get(dtype, 0) + 1


         # Dashboard de extrações
        st.write("---")
        st.header("📊 Dashboard de Extrações")

        # Contagem de documentos por tipo
        #doc_type_counts = {}
        # for res in results:
        #     doc_type = res.get("Tipo de Documento")
        #     if doc_type:
        #         doc_type_counts[doc_type] = doc_type_counts.get(doc_type, 0) + 1

        st.subheader("📋 Documentos por Tipo")
        if doc_type_counts:
            cols = st.columns(len(doc_type_counts))
            for idx, (dtype, count) in enumerate(doc_type_counts.items()):
                cols[idx].metric(dtype, count)

            # Gráfico de barras das contagens por tipo
            df_types = pd.DataFrame.from_dict(
                doc_type_counts, orient='index', columns=['Quantidade']
            )
            df_types.index.name = 'Tipo de Documento'
            st.subheader("📈 Visualização da Contagem por Tipo")
            st.bar_chart(df_types)
        else:
            st.info("Nenhum tipo de documento identificado para visualização.")

        st.markdown("**Obrigado por usar o Extrator de Documentos Inteligentes!**")

        

# --- Navegação Principal com container ---
page_container = st.container()
if st.session_state.page == "home":
    with page_container:
        show_home()
else:
    with page_container:
        show_app()










# # Função: Chamada ao modelo GPT-4o da OpenAI
# def extract_document_fields_with_openai(image_b64: str):
#     headers = {
#         "Authorization": f"Bearer {openai.api_key}",
#         "Content-Type": "application/json"
#     }
#     payload = {
#         "model": "gpt-4o",
#         "messages": [
#             {"role": "user", "content": [
#                 {"type": "text", "text": (
#                             "Você é um extrator de documentos brasileiros. "
#                             "A imagem pode ser um RG, CNH ou Certidão de Nascimento. Classifique o tipo de documento (RG, CNH ou Certidão de Nascimento) e depois extraia os dados relevantes. "
#                             "Extraia os seguintes campos, se disponíveis:\n\n"
#                             "- Tipo de Documento\n"
#                             "- Nome\n"
#                             "- Data de Nascimento\n"
#                             "- Número do documento (RG ou CNH)\n"
#                             "- CPF (se presente)\n"
#                             "- Órgão emissor (RG) ou Categoria (CNH)\n"
#                             "- Nome da mãe (Certidão)\n\n"
#                             "- Nome do pai (Certidão)\n\n"
#                             "Responda SOMENTE com um objeto JSON válido e nada mais. Não inclua explicações. Envolva o conteúdo com três crases seguidas de json no início e três crases no fim, assim:\n```json\n{{ JSON aqui }}\n```"
#                         )},
#                 {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
#             ]}
#         ],
#         "max_tokens": 1000
#     }
#     response = requests.post(
#         "https://api.openai.com/v1/chat/completions",
#         headers=headers,
#         json=payload
#     )
#     if response.ok:
#         raw = response.json()["choices"][0]["message"]["content"]
#         try:
#             return json.loads(raw)
#         except json.JSONDecodeError:
#             return {"resposta": raw}
#     return {"erro": response.text}