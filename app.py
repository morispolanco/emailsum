import streamlit as st
import imaplib
import email
from email.header import decode_header
import requests
from datetime import datetime, timedelta
import ssl

# Configuración de la clave API de Together
TOGETHER_API_KEY = st.secrets["TOGETHER_API_KEY"]

def get_emails(email_address, password, date, imap_server):
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    try:
        # Intenta conectar con SSL
        mail = imaplib.IMAP4_SSL(imap_server, port=993, ssl_context=context)
    except:
        try:
            # Si falla, intenta sin SSL
            mail = imaplib.IMAP4(imap_server, port=143)
            mail.starttls(ssl_context=context)
        except Exception as e:
            return None, f"Error de conexión: {str(e)}"

    try:
        mail.login(email_address, password)
    except imaplib.IMAP4.error as e:
        return None, f"Error de autenticación: {str(e)}"

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
    return emails, None

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

    # Campos de entrada para email, contraseña y servidor IMAP
    email_address = st.text_input("Dirección de correo electrónico", key="email")
    password = st.text_input("Contraseña", type="password", key="password")
    imap_server = st.text_input("Servidor IMAP", value="imap.gmail.com", key="imap_server")

    # Selector de fecha
    date = st.date_input("Selecciona la fecha para sintetizar los correos:", datetime.now() - timedelta(days=1))

    if st.button("Sintetizar Correos"):
        if not email_address or not password:
            st.error("Por favor, introduce tu email y contraseña.")
        else:
            with st.spinner("Obteniendo y sintetizando correos..."):
                emails, error = get_emails(email_address, password, date, imap_server)
                if error:
                    st.error(error)
                    st.info("Si estás usando Gmail, asegúrate de que:")
                    st.info("1. Has habilitado el acceso IMAP en tu cuenta de Gmail.")
                    st.info("2. Has permitido el acceso de aplicaciones menos seguras o estás usando una contraseña de aplicación.")
                    st.info("3. No estás usando autenticación de dos factores sin una contraseña de aplicación.")
                else:
                    synthesis = synthesize_emails(emails)
                    st.subheader(f"Síntesis de correos para {date:%d/%m/%Y}")
                    st.write(synthesis)

if __name__ == "__main__":
    main()
