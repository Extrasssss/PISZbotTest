import logging
import os
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.email_service.email_config import EMAIL_CONFIG

logger = logging.getLogger(__name__)


def send_email_with_attachment(
    subject: str, body: str, attachment_path: str, to_email: str = None
) -> bool:
    """Отправляет email с вложением"""
    try:
        if to_email is None:
            to_email = EMAIL_CONFIG["email_to"]

        # Создаем сообщение
        msg = MIMEMultipart()
        msg["From"] = EMAIL_CONFIG["email_from"]
        msg["To"] = to_email
        msg["Subject"] = subject

        # Добавляем текст сообщения
        msg.attach(MIMEText(body, "plain"))

        # Добавляем вложение с правильным MIME-типом
        if attachment_path and os.path.exists(attachment_path):
            # Получаем имя файла с расширением
            filename = os.path.basename(attachment_path)

            # Читаем файл
            with open(attachment_path, "rb") as file:
                file_data = file.read()

            # Создаем MIME часть для Excel файла
            part = MIMEApplication(file_data, Name=filename)

            # Добавляем заголовки для вложения
            part["Content-Disposition"] = f'attachment; filename="{filename}"'

            # Устанавливаем правильный MIME-тип для Excel
            part.add_header(
                "Content-Type",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

            msg.attach(part)

        # Создаем SMTP сессию
        server = smtplib.SMTP(
            EMAIL_CONFIG["smtp_server"], EMAIL_CONFIG["smtp_port"])
        server.starttls()  # Включаем шифрование
        server.login(EMAIL_CONFIG["email_from"],
                     EMAIL_CONFIG["email_password"])

        # Отправляем email
        text = msg.as_string()
        server.sendmail(EMAIL_CONFIG["email_from"], to_email, text)
        server.quit()

        logger.info(f"✅ Email отправлен на {to_email} с вложением {filename}")
        return True

    except Exception as e:
        logger.error(f"❌ Ошибка отправки email: {e}")
        return False
