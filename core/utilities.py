import logging
import smtplib
import sys
from os.path import basename
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from core.config import Config


class Emailer:

    @staticmethod
    def send_email(subject, mail_content, mail_content_html=None, attachments=[]):
        logger = logging.getLogger(Config.LOGGER_NAME)

        sender_address = Config.EMAIL_SENDER_ADDRESS
        receiver_address = Config.EMAIL_RECEIVERS
        sender_pass = Config.EMAIL_SENDER_PASS
        smtp_server = Config.EMAIL_SMTP_SERVER
        smtp_port = Config.EMAIL_SMTP_PORT

        # Setup the MIME
        if mail_content_html is None:
            message = MIMEMultipart()
        else:
            message = MIMEMultipart(
                "alternative", None, [MIMEText(mail_content), MIMEText(mail_content_html, 'html')])

        message['From'] = sender_address
        message['To'] = receiver_address
        message['Subject'] = subject

        # The body and the attachments for the mail
        if mail_content_html is None:
            message.attach(MIMEText(mail_content, 'plain', "utf-8"))

        for f in attachments:
            with open(f, "rb") as fil:
                part = MIMEApplication(
                    fil.read(),
                    Name=basename(f)
                )
            # After the file is closed
            part['Content-Disposition'] = 'attachment; filename="%s"' % basename(
                f)
            message.attach(part)

        # Create SMTP session for sending the mail
        session = smtplib.SMTP(smtp_server, smtp_port)
        session.starttls()  # enable security
        # login with mail_id and password
        session.login(sender_address, sender_pass)
        text = message.as_string()
        session.sendmail(sender_address, receiver_address, text)
        session.quit()
        logger.info(f"Email sent to {sender_address}: {subject}")


def setup_logging(log_file, logger_name: str = Config.LOGGER_NAME, log_level=Config.LOG_LEVEL):
    # 1. Create a custom logger
    logger = logging.getLogger(logger_name)
    logger.setLevel(log_level)

    # 2. Define a format for the logs
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # 3. Create a console handler (StreamHandler)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(Config.LOG_LEVEL)
    console_handler.setFormatter(formatter)

    # 4. Create a file handler (FileHandler)
    file_handler = logging.FileHandler(log_file, mode='a')
    file_handler.setLevel(Config.LOG_LEVEL)
    file_handler.setFormatter(formatter)

    # 5. Add the handlers to the logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger
