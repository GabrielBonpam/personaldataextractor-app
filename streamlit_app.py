import streamlit as st
import base64
import requests
import openai
from PIL import Image
import io
import json


# CONFIGURAÇÃO
st.set_page_config(page_title="Leitor de Documentos Inteligentes", layout="wide")
st.title("📄 Extração de Documentos Inteligentes")

# 🔐 API KEY OpenAI
openai.api_key = st.secrets.get("OPENAI_API_KEY") or st.text_input("Informe sua chave da OpenAI", type="password")

# Função: Converte imagem para base64
def image_to_base64(file):
    return base64.b64encode(file.read()).decode("utf-8")

# Função: Chamada ao modelo GPT-4o da OpenAI
def extract_document_fields_with_openai(image_b64: str):
    headers = {
        "Authorization": f"Bearer {openai.api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "gpt-4o",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
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
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_b64}"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 1000
    }

    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)

    if response.status_code == 200:
        content = response.json()
        raw_output = content["choices"][0]["message"]["content"]
        try:
            return json.loads(raw_output)
        except json.JSONDecodeError:
            return {"resposta": raw_output}
    else:
        return {"erro": "Erro na API", "detalhes": response.text}

# UPLOAD DE IMAGENS
uploaded_files = st.file_uploader("📷 Envie imagens de documentos (RG, CNH, Certidão)", type=["png", "jpg", "jpeg"], accept_multiple_files=True)

# PROCESSAMENTO COM ORDEM
if uploaded_files and openai.api_key:
    resultados = []
    total_docs = len(uploaded_files)

    for idx, file in enumerate(uploaded_files, start=1):
        st.markdown(f"### 📄 Documento {idx} de {total_docs}")

        col1, col2 = st.columns([1, 2])
        with col1:
            st.image(file, caption=file.name, width=250)

        with col2:
            with st.spinner(f"🔍 Extraindo dados do documento {idx}..."):
                image_b64 = image_to_base64(file)
                resultado = extract_document_fields_with_openai(image_b64)
                resultados.append(resultado)

                st.success(f"✅ Documento {idx} processado com sucesso!")
                with st.expander("📋 Resultado individual"):
                    st.json(resultado)

    st.subheader("📦 Resultado Consolidado")
    st.json(resultados)



# Botão "Nova extração" no canto inferior direito
st.markdown("""
    <style>
    .fixed-button {
        position: fixed;
        bottom: 30px;
        right: 30px;
        z-index: 9999;
    }
    </style>
    <div class="fixed-button">
        <form action="">
            <input type="submit" value="Nova extração" style="background-color:#4CAF50;color:white;padding:10px 20px;border:none;border-radius:5px;cursor:pointer;">
        </form>
    </div>
""", unsafe_allow_html=True)
