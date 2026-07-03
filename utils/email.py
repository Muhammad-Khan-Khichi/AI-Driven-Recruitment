import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import settings


def send_reset_password_email(email: str, reset_link: str) -> bool:
    """
    Send password reset email via SMTP
    
    Args:
        email: Recipient email address
        reset_link: Full URL with reset token
    
    Returns:
        True if sent successfully, False otherwise
    """
    sender_email = settings.EMAIL_FROM
    smtp_host = settings.SMTP_HOST
    smtp_user = settings.SMTP_USER
    smtp_pass = settings.SMTP_PASS
    smtp_port = settings.SMTP_PORT
    
    # Check if email is configured
    if not all([sender_email, smtp_host, smtp_user, smtp_pass]):
        print("⚠️ Email not configured. Printing to console instead.")
        print(f"\n{'='*60}")
        print(f"📧 PASSWORD RESET LINK")
        print(f"{'='*60}")
        print(f"To: {email}")
        print(f"Link: {reset_link}")
        print(f"{'='*60}\n")
        return False
    
    # Create email
    message = MIMEMultipart("alternative")
    message["Subject"] = "🔐 Reset Your Password - Job Searcher AI"
    message["From"] = sender_email
    message["To"] = email
    
    # HTML email body
    html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 30px; text-align: center; border-radius: 10px;">
          <h1 style="color: white; margin: 0;">🔐 Password Reset</h1>
        </div>
        
        <div style="padding: 30px; background: #f9f9f9; border-radius: 10px; margin-top: 20px;">
          <h2 style="color: #333; margin-top: 0;">Hi there!</h2>
          
          <p style="color: #555; font-size: 16px; line-height: 1.6;">
            We received a request to reset your password for your 
            <strong>Job Searcher AI</strong> account.
          </p>
          
          <p style="color: #555; font-size: 16px; line-height: 1.6;">
            Click the button below to reset your password:
          </p>
          
          <div style="text-align: center; margin: 30px 0;">
            <a href="{reset_link}" 
               style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                      color: white;
                      padding: 15px 40px;
                      text-decoration: none;
                      border-radius: 8px;
                      font-weight: bold;
                      display: inline-block;
                      font-size: 16px;">
              🔓 Reset Password
            </a>
          </div>
          
          <p style="color: #555; font-size: 14px; line-height: 1.6;">
            Or copy and paste this link into your browser:
          </p>
          
          <p style="background: #fff; padding: 15px; border-radius: 5px; 
                    word-break: break-all; color: #667eea; font-size: 14px;
                    border: 1px solid #ddd;">
            {reset_link}
          </p>
          
          <p style="color: #999; font-size: 14px; margin-top: 30px;">
            ⏰ This link expires in <strong>1 hour</strong>.
          </p>
          
          <p style="color: #999; font-size: 14px;">
            If you didn't request this, you can safely ignore this email. 
            Your password will remain unchanged.
          </p>
          
          <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
          
          <p style="color: #999; font-size: 12px; text-align: center; margin: 0;">
            © 2026 Job Searcher AI. All rights reserved.
          </p>
        </div>
      </body>
    </html>
    """
    
    # Plain text version (fallback)
    text = f"""
    Reset Your Password - Job Searcher AI
    
    Hi there!
    
    We received a request to reset your password.
    
    Click this link to reset your password:
    {reset_link}
    
    This link expires in 1 hour.
    
    If you didn't request this, you can safely ignore this email.
    
    © 2026 Job Searcher AI
    """
    
    # Attach both versions
    part1 = MIMEText(text, "plain")
    part2 = MIMEText(html, "html")
    message.attach(part1)
    message.attach(part2)
    
    # Send email
    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(sender_email, email, message.as_string())
        print(f"✅ Reset email sent to {email}")
        return True
    except Exception as e:
        print(f"❌ Error sending email: {e}")
        # Fallback: print to console
        print(f"\n{'='*60}")
        print(f"📧 PASSWORD RESET LINK (FALLBACK)")
        print(f"{'='*60}")
        print(f"To: {email}")
        print(f"Link: {reset_link}")
        print(f"{'='*60}\n")
        return False


def send_welcome_email(email: str, full_name: str) -> bool:
    """Send welcome email to new users"""
    sender_email = settings.EMAIL_FROM
    smtp_host = settings.SMTP_HOST
    smtp_user = settings.SMTP_USER
    smtp_pass = settings.SMTP_PASS
    smtp_port = settings.SMTP_PORT
    
    if not all([sender_email, smtp_host, smtp_user, smtp_pass]):
        return False
    
    message = MIMEMultipart("alternative")
    message["Subject"] = "🎉 Welcome to Job Searcher AI"
    message["From"] = sender_email
    message["To"] = email
    
    html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 30px; text-align: center;">
          <h1 style="color: white; margin: 0;">🎉 Welcome!</h1>
        </div>
        <div style="padding: 30px; background: #f9f9f9;">
          <h2>Hi {full_name}!</h2>
          <p>Thanks for signing up for Job Searcher AI.</p>
          <p>Start searching for jobs, generate cover letters, and track your applications!</p>
        </div>
      </body>
    </html>
    """
    
    text = f"Hi {full_name}! Welcome to Job Searcher AI."
    
    part1 = MIMEText(text, "plain")
    part2 = MIMEText(html, "html")
    message.attach(part1)
    message.attach(part2)
    
    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(sender_email, email, message.as_string())
        return True
    except Exception as e:
        print(f"Error sending welcome email: {e}")
        return False