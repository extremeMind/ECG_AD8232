import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_mail(recipient, subject, body):
    sender_email = ""  # Replace with your email address
    sender_password = ""  # Replace with your email password

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP_SSL('smtp.google.email', 465)  # Use SMTP_SSL for port 465
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, recipient, text)
        server.quit()
        print("Email sent successfully")
    except smtplib.SMTPAuthenticationError as e:
        print(f"Authentication error: {e.smtp_code} - {e.smtp_error.decode()}")
    except Exception as e:
        print(f"Error occurred while sending email: {e}")