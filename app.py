import streamlit as st
import imaplib
import email
from email.header import decode_header
import requests
from datetime import datetime, timedelta

# Configuración de las claves API y credenciales
TOGETHER_API_KEY = st.secrets["TOGETHER_API_KEY"]
EMAIL = st.secrets["EMAIL"]
PASSWORD = st.secrets["EMAIL_PASSWORD"]
IMAP_SERVER = "imap.gmail.com"  # Cambia esto si usas otro proveedor de correo

def get_emails(date):
    # Conectar al servidor IMAP
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL, PASSWORD)
    mail.select("inbox")

    # Buscar correos electrónicos de la fecha especificada
    search_criteria = f'(ON "{date:%d-%b-%Y}")'
    _, message_numbers = mail.search(None, search_criteria)

    emails = []
    for num in message_numbers[0].split():
        _, msg_data = mail.fetch(num, "(RFC822)")
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                email_body = response_part[1]
                email_message = email.message_from_bytes(email_body)
                subject, encoding = decode_header(email_message["Subject"])[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding or "utf-8")
                sender = email_message["From"]
                emails.append(f"From: {sender}\nSubject: {subject}\n\n")

    mail.close()
    mail.logout()
    return emails

def synthesize_emails(emails):
    if not emails:
        return "No se encontraron correos electrónicos para la fecha especificada."

    prompt = "Sintetiza los siguientes correos electrónicos de manera concisa:\n\n" + "\n".join(emails)
    
    headers = {
        "Authorization": f"Bearer {TOGETHER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "togethercomputer/llama-2-70b-chat",
        "prompt": prompt,
        "max_tokens": 500,
        "temperature": 0.7
    }
    
    response = requests.post("https://api.together.xyz/inference", headers=headers, json=data)
    
    if response.status_code == 200:
        return response.json()['output']['choices'][0]['text'].strip()
    else:
        return f"Error al sintetizar los correos: {response.status_code} - {response.text}"

def main():
    st.title("Síntesis Diaria de Correos Electrónicos")

    # Selector de fecha
    date = st.date_input("Selecciona la fecha para sintetizar los correos:", datetime.now() - timedelta(days=1))

    if st.button("Sintetizar Correos"):
        with st.spinner("Obteniendo y sintetizando correos..."):
            emails = get_emails(date)
            synthesis = synthesize_emails(emails)
            st.subheader(f"Síntesis de correos para {date:%d/%m/%Y}")
            st.write(synthesis)

if __name__ == "__main__":
    main()
