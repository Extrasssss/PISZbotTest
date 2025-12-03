import logging
import os
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import Config
logger = logging.getLogger(__name__)


def send_email_with_attachment(
    subject: str, body: str, attachment_path: str, to_email: str = None
) -> bool:
    """Отправляет email с вложением"""
    try:
        # 🛠️ ИСПРАВЛЕНИЕ: Используем EMAIL_CONFIG вместо прямых атрибутов
        if to_email is None:
            to_email = Config.EMAIL_CONFIG["email_to"]

        # Создаем сообщение
        msg = MIMEMultipart()
        msg["From"] = Config.EMAIL_CONFIG["email_from"]
        msg["To"] = to_email
        msg["Subject"] = subject

        # Добавляем текст сообщения
        msg.attach(MIMEText(body, "plain"))

        # Добавляем вложение с правильным MIME-типом
        if attachment_path and os.path.exists(attachment_path):
            filename = os.path.basename(attachment_path)

            with open(attachment_path, "rb") as file:
                file_data = file.read()

            part = MIMEApplication(file_data, Name=filename)
            part["Content-Disposition"] = f'attachment; filename="{filename}"'
            part.add_header(
                "Content-Type",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            msg.attach(part)

        # 🛠️ ИСПРАВЛЕНИЕ: Используем EMAIL_CONFIG для SMTP настроек
        server = smtplib.SMTP(
            Config.EMAIL_CONFIG["smtp_server"],
            Config.EMAIL_CONFIG["smtp_port"]
        )
        server.starttls()
        server.login(
            Config.EMAIL_CONFIG["email_from"],
            Config.EMAIL_CONFIG["email_password"]
        )

        # Отправляем email
        text = msg.as_string()
        server.sendmail(Config.EMAIL_CONFIG["email_from"], to_email, text)
        server.quit()

        logger.info(f"✅ Email отправлен на {to_email} с вложением {filename}")
        return True

    except Exception as e:
        logger.error(f"❌ Ошибка отправки email: {e}")
        return False