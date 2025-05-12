import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart, MIMEBase
from email import encoders
from typing import Optional
import logging
from email.utils import formatdate, make_msgid

from app.core.config import settings

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def send_verification_email(email_to: str, verification_token: str) -> None:
    """
    Send email verification link to user's email address.
    """
    subject = "Verify your email for Not So Epic Films"
    
    # Create the verification link
    verification_link = f"{settings.SERVER_HOST}/api/v1/auth/verify-email?token={verification_token}"
    
    # Create the plain text and HTML versions of your message
    text_content = f"""
    Hi there,

    Thank you for signing up for Not So Epic Films! Please verify your email address by visiting the link below:
    {verification_link}

    This link will expire in {settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS} hours.

    If you did not create an account, please ignore this email.
    """
    
    # Create the email content
    html_content = f"""
    <html>
        <body>
            <h2>Verify your email for Not So Epic Films</h2>
            <p>Thank you for signing up! Please verify your email address by clicking the link below:</p>
            <p><a href="{verification_link}">Verify Email Address</a></p>
            <p>This link will expire in {settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS} hours.</p>
            <p>If you did not create an account, please ignore this email.</p>
        </body>
    </html>
    """
    
    # Create message container - use 'alternative' for plain text/HTML
    message = MIMEMultipart('alternative')
    message["From"] = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>"
    message["To"] = email_to
    message["Subject"] = subject
    # Add Date header
    message['Date'] = formatdate(localtime=True)
    # Add Message-ID header
    message['Message-ID'] = make_msgid()
    
    # Record the MIME types of both parts - text/plain and text/html.
    part1 = MIMEText(text_content, "plain")
    part2 = MIMEText(html_content, "html")
    
    # Attach parts into message container.
    # According to RFC 2046, the last part of a multipart message, in this case
    # the HTML message, is best and preferred.
    message.attach(part1)
    message.attach(part2)
    
    try:
        # Log SMTP settings (without password)
        # logger.info(f"Attempting to connect to SMTP_SSL server: {settings.SMTP_HOST}:{settings.SMTP_PORT}")
        # logger.info(f"Using email: {settings.SMTP_USER}")
        
        # Create SMTP session using SMTP_SSL for implicit TLS
        server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT)
        # server.set_debuglevel(1)  # Enable debug output
        
        # Login
        # logger.info("Attempting to login...")
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        
        # Send email
        logger.info(f"Sending email to: {email_to}")
        server.send_message(message)
        
        # Close connection
        server.quit()
        logger.info("Email sent successfully!")
        
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP Authentication failed: {str(e)}")
        raise Exception(f"SMTP Authentication failed: {str(e)}")
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error occurred: {str(e)}")
        raise Exception(f"SMTP error occurred: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to send verification email: {str(e)}")
        raise Exception(f"Failed to send verification email: {str(e)}") 