import smtplib
import logging
import time
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional, Dict, Any, List, Tuple
from api.config import (
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM,
)

logger = logging.getLogger(__name__)


# ── Configuration & Validation ─────────────────────────────────
class EmailConfig:
    """Validated SMTP configuration container."""
    
    def __init__(self):
        self.host = SMTP_HOST
        self.port = SMTP_PORT or 587
        self.user = SMTP_USER
        self.password = SMTP_PASSWORD
        self.from_email = SMTP_FROM or "noreply@hireai.app"
        self._validate()

    def _validate(self) -> None:
        """Validate essential SMTP settings."""
        missing = []
        if not self.host:
            missing.append("SMTP_HOST")
        if not self.user:
            missing.append("SMTP_USER")
        if not self.password:
            missing.append("SMTP_PASSWORD")
        
        if missing:
            logger.warning(f"⚠️  Missing SMTP config: {', '.join(missing)}. Emails will fall back to console.")

    @property
    def is_configured(self) -> bool:
        return bool(self.host and self.user and self.password)


# ── Brand System (HireAI - New Design) ─────────────────────────
BRAND: Dict[str, str] = {
    # New color palette - Indigo + Teal (modern & trustworthy)
    "primary":      "#6366F1",      # Indigo
    "primary_dk":   "#4F46E5",
    "accent":       "#14B8A6",      # Teal
    "accent_dk":    "#0F766E",
    
    # Backgrounds
    "dark":         "#0F172A",      # Slate 900
    "surface":      "#1E2937",      # Slate 800
    "surface_light":"#334155",      # Slate 700
    
    # Text
    "text":         "#F8FAFC",      # Slate 50
    "text_muted":   "#94A3B8",      # Slate 400
    "text_light":   "#CBD5E1",      # Slate 300
    
    # Borders & accents
    "border":       "#475569",      # Slate 600
    "warning":      "#F59E0B",
    "success":      "#10B981",
    "error":        "#EF4444",
}


# ── Core Email Service ─────────────────────────────────────────
class EmailService:
    """Production-ready email service for HireAI with modern design."""
    
    def __init__(self, config: Optional[EmailConfig] = None):
        self.config = config or EmailConfig()
        self.max_retries = 3
        self.retry_delay = 1.5

    # ── HTML Template Engine (NEW DESIGN) ──────────────────────
    def email_wrapper(
        self,
        content: str,
        preheader: str = "",
        title: str = "HireAI",
        custom_styles: str = "",
    ) -> str:
        """Build a full HTML email with the new HireAI brand shell."""
        year = datetime.now().year
        
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="x-apple-disable-message-reformatting">
    <meta name="color-scheme" content="dark">
    <meta name="supported-color-schemes" content="dark">
    <title>{title}</title>
    <style>
        body, table, td, a {{ -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; }}
        table, td {{ mso-table-lspace: 0pt; mso-table-rspace: 0pt; }}
        img {{ -ms-interpolation-mode: bicubic; }}
        body {{ margin: 0; padding: 0; }}
        a[x-apple-data-detectors] {{ color: inherit !important; text-decoration: none !important; }}
        
        @media only screen and (max-width: 600px) {{
            .container {{ width: 100% !important; padding: 16px !important; }}
            .btn {{ width: 100% !important; box-sizing: border-box !important; }}
            .two-col {{ width: 100% !important; }}
        }}
        
        {custom_styles}
    </style>
</head>
<body style="margin:0; padding:0; background:{BRAND['dark']}; font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;">
    
    <!-- Preheader -->
    <span style="display:none; visibility:hidden; opacity:0; color:{BRAND['dark']}; font-size:1px; line-height:1px; max-height:0; max-width:0; overflow:hidden;">
        {preheader}
    </span>
    
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{BRAND['dark']};">
        <tr>
            <td align="center" style="padding:48px 20px;">
                
                <!-- Main Container -->
                <table role="presentation" class="container" width="600" cellpadding="0" cellspacing="0" border="0" 
                       style="max-width:600px; background:{BRAND['surface']}; border-radius:20px; overflow:hidden; box-shadow:0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1);">
                    
                    <!-- Header -->
                    <tr>
                        <td style="padding:32px 40px 28px; background:{BRAND['surface']}; border-bottom:1px solid {BRAND['border']};">
                            <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%">
                                <tr>
                                    <td>
                                        <!-- Logo -->
                                        <table role="presentation" cellpadding="0" cellspacing="0" border="0">
                                            <tr>
                                                <td style="vertical-align:middle;">
                                                    <div style="display:inline-block; width:42px; height:42px; background:linear-gradient(135deg, {BRAND['primary']}, {BRAND['accent']}); border-radius:12px; text-align:center; line-height:42px; font-weight:800; color:white; font-size:20px; box-shadow:0 4px 6px -1px rgb(0 0 0 / 0.1);">
                                                        H
                                                    </div>
                                                </td>
                                                <td style="padding-left:14px; vertical-align:middle;">
                                                    <span style="font-size:26px; font-weight:800; color:{BRAND['text']}; letter-spacing:-1px;">Hire</span>
                                                    <span style="font-size:26px; font-weight:800; color:{BRAND['primary']};">AI</span>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                    <!-- Body Content -->
                    <tr>
                        <td style="padding:44px 40px 48px; color:{BRAND['text']};">
                            {content}
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="padding:28px 40px; background:{BRAND['dark']}; border-top:1px solid {BRAND['border']}; text-align:center;">
                            <p style="margin:0 0 10px; color:{BRAND['text_muted']}; font-size:13px; line-height:1.4;">
                                © {year} HireAI · Your AI-powered career companion
                            </p>
                            
                            <p style="margin:0 0 14px; color:{BRAND['text_muted']}; font-size:12px;">
                                <a href="https://hireai.app" style="color:{BRAND['primary']}; text-decoration:none; font-weight:500;">hireai.app</a>
                                &nbsp;·&nbsp;
                                <a href="mailto:support@hireai.app" style="color:{BRAND['primary']}; text-decoration:none; font-weight:500;">Support</a>
                            </p>
                            
                            <p style="margin:0; color:{BRAND['text_muted']}; font-size:11px;">
                                <a href="https://hireai.app/unsubscribe" style="color:{BRAND['text_muted']}; text-decoration:none;">Unsubscribe</a>
                            </p>
                        </td>
                    </tr>
                    
                </table>
                
            </td>
        </tr>
    </table>
</body>
</html>"""

    def _button(
        self, 
        label: str, 
        href: str, 
        color: Optional[str] = None,
        size: str = "normal",
        variant: str = "primary"
    ) -> str:
        """Render a beautiful CTA button."""
        if variant == "primary":
            bg = color or BRAND['primary']
            shadow = f"0 10px 15px -3px {bg}33, 0 4px 6px -4px {bg}33"
        else:
            bg = BRAND['surface_light']
            shadow = "none"
        
        padding = "16px 36px" if size == "large" else "13px 28px"
        font_size = "16px" if size == "large" else "15px"
        
        return f"""
        <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:28px 0;">
            <tr>
                <td align="center" bgcolor="{bg}" style="border-radius:12px; box-shadow:{shadow};">
                    <a href="{href}" target="_blank"
                       class="btn"
                       style="display:inline-block; padding:{padding}; color:#ffffff;
                              text-decoration:none; font-weight:700; font-size:{font_size};
                              border-radius:12px; background:{bg};">
                        {label}
                    </a>
                </td>
            </tr>
        </table>"""

    # ── SMTP Transport ─────────────────────────────────────────
    def _send_via_smtp(self, to_email: str, message: MIMEMultipart) -> bool:
        if not self.config.is_configured:
            return False

        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                with smtplib.SMTP(self.config.host, self.config.port, timeout=15) as server:
                    server.starttls()
                    server.login(self.config.user, self.config.password)
                    server.sendmail(self.config.from_email, to_email, message.as_string())
                
                logger.info(f"✅ Email sent successfully to {to_email}")
                return True
                
            except smtplib.SMTPException as e:
                last_exception = e
                logger.warning(f"⚠️ SMTP attempt {attempt + 1}/{self.max_retries} failed: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
            except Exception as e:
                last_exception = e
                logger.error(f"❌ Unexpected error sending to {to_email}: {e}")
                break

        logger.error(f"❌ Failed to send email to {to_email} after {self.max_retries} attempts")
        return False

    def _print_fallback(self, subject: str, to: str, body: str) -> None:
        print("\n" + "━" * 65)
        print(f"📧  {subject}")
        print("━" * 65)
        print(f"To:      {to}")
        print(f"From:    {self.config.from_email}")
        print(f"Body:\n{body}")
        print("━" * 65 + "\n")

    # ── Generic Email Sender ───────────────────────────────────
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        preheader: str = "",
        attachments: Optional[List[Tuple[str, bytes, str]]] = None,
    ) -> bool:
        if not text_content:
            text_content = html_content.replace("<", " ").replace(">", " ").strip()

        html_body = self.email_wrapper(html_content, preheader=preheader)
        
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.config.from_email
        msg["To"] = to_email
        
        msg.attach(MIMEText(text_content, "plain"))
        msg.attach(MIMEText(html_body, "html"))
        
        if attachments:
            for filename, content, mimetype in attachments:
                part = MIMEBase(*mimetype.split("/", 1))
                part.set_payload(content)
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f"attachment; filename={filename}")
                msg.attach(part)

        success = self._send_via_smtp(to_email, msg)
        
        if not success:
            self._print_fallback(subject, to_email, text_content)
        
        return success

    # ── Email Templates (Updated Design) ───────────────────────
    def send_reset_password_email(self, email: str, reset_link: str) -> bool:
        content = f"""
            <div style="text-align:center; margin-bottom:8px;">
                <div style="display:inline-block; width:64px; height:64px; background:linear-gradient(135deg, {BRAND['primary']}, {BRAND['accent']}); border-radius:50%; line-height:64px; font-size:28px; margin-bottom:16px;">
                    🔐
                </div>
            </div>
            
            <h1 style="margin:0 0 12px; font-size:26px; font-weight:800; color:{BRAND['text']}; text-align:center; letter-spacing:-0.5px;">
                Reset your password
            </h1>
            
            <p style="margin:0 0 28px; color:{BRAND['text_muted']}; font-size:15px; text-align:center; line-height:1.5;">
                We received a request to reset your password.<br>
                Click the button below to create a new one.
            </p>
            
            {self._button("Reset Password", reset_link, size="large")}
            
            <div style="margin:32px 0 24px; padding:20px; background:{BRAND['dark']}; border-radius:12px; border:1px solid {BRAND['border']};">
                <p style="margin:0 0 6px; color:{BRAND['text_muted']}; font-size:12px; text-transform:uppercase; letter-spacing:0.5px;">
                    Or copy this link
                </p>
                <p style="margin:0; color:{BRAND['primary']}; font-size:13px; word-break:break-all; font-family:monospace;">
                    {reset_link}
                </p>
            </div>
            
            <p style="margin:0; color:{BRAND['text_muted']}; font-size:13px; text-align:center; line-height:1.5;">
                This link expires in <strong style="color:{BRAND['text']};">1 hour</strong>.<br>
                Didn't request this? You can safely ignore this email.
            </p>
        """
        
        text_body = f"""Reset Your HireAI Password

Hi there! Click this link to reset your password:
{reset_link}

This link expires in 1 hour.

Didn't request this? You can safely ignore this email.

© {datetime.now().year} HireAI"""

        return self.send_email(
            email,
            "Reset your HireAI password",
            content,
            text_body,
            preheader="Reset your HireAI password"
        )

    def send_welcome_email(self, email: str, full_name: str) -> bool:
        first_name = (full_name or "there").split()[0]
        
        content = f"""
            <div style="text-align:center;">
                <div style="display:inline-block; width:72px; height:72px; background:linear-gradient(135deg, {BRAND['primary']}, {BRAND['accent']}); border-radius:50%; line-height:72px; font-size:32px; margin-bottom:20px;">
                    🎉
                </div>
            </div>
            
            <h1 style="margin:0 0 8px; font-size:28px; font-weight:800; color:{BRAND['text']}; text-align:center; letter-spacing:-0.6px;">
                Welcome to HireAI
            </h1>
            
            <p style="margin:0 0 32px; color:{BRAND['text_muted']}; font-size:15px; text-align:center;">
                Hi {first_name}, we're excited to have you here.
            </p>
            
            <div style="background:{BRAND['dark']}; border-radius:16px; padding:28px; margin:24px 0;">
                <p style="margin:0 0 20px; color:{BRAND['text_light']}; font-size:15px; font-weight:600; text-align:center;">
                    Here's what you can do right now:
                </p>
                
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                    <tr>
                        <td style="padding:12px 0; border-bottom:1px solid {BRAND['border']};">
                            <span style="font-size:15px; color:{BRAND['text']};">🔍</span>
                            <span style="margin-left:10px; color:{BRAND['text']}; font-weight:600;">Smart Job Search</span>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding:12px 0; border-bottom:1px solid {BRAND['border']};">
                            <span style="font-size:15px; color:{BRAND['text']};">✍️</span>
                            <span style="margin-left:10px; color:{BRAND['text']}; font-weight:600;">AI Resume &amp; Cover Letters</span>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding:12px 0;">
                            <span style="font-size:15px; color:{BRAND['text']};">🎯</span>
                            <span style="margin-left:10px; color:{BRAND['text']}; font-weight:600;">Interview Preparation</span>
                        </td>
                    </tr>
                </table>
            </div>
            
            {self._button("Go to Dashboard", "https://hireai.app/dashboard", size="large")}
        """
        
        text_body = f"""Welcome to HireAI, {first_name}!

We're excited to have you on board.

Get started: https://hireai.app/dashboard

© {datetime.now().year} HireAI"""

        return self.send_email(
            email,
            "Welcome to HireAI!",
            content,
            text_body,
            preheader=f"Welcome to HireAI, {first_name}!"
        )

    def send_verification_email(self, email: str, full_name: str, verify_link: str) -> bool:
        first_name = (full_name or "there").split()[0]
        
        content = f"""
            <div style="text-align:center; margin-bottom:12px;">
                <div style="display:inline-block; width:64px; height:64px; background:linear-gradient(135deg, {BRAND['primary']}, {BRAND['accent']}); border-radius:50%; line-height:64px; font-size:28px;">
                    ✉️
                </div>
            </div>
            
            <h1 style="margin:0 0 10px; font-size:26px; font-weight:800; color:{BRAND['text']}; text-align:center;">
                Verify your email
            </h1>
            
            <p style="margin:0 0 24px; color:{BRAND['text_muted']}; font-size:15px; text-align:center; line-height:1.5;">
                Hi {first_name}, please confirm your email address to secure your account.
            </p>
            
            {self._button("Verify Email Address", verify_link, size="large")}
            
            <p style="margin:24px 0 0; color:{BRAND['text_muted']}; font-size:13px; text-align:center;">
                This link expires in <strong style="color:{BRAND['text']};">24 hours</strong>.
            </p>
        """
        
        text_body = f"""Verify your HireAI email

Hi {first_name}, please verify your email:
{verify_link}

This link expires in 24 hours.

© {datetime.now().year} HireAI"""

        return self.send_email(
            email,
            "Verify your HireAI email",
            content,
            text_body,
            preheader=f"Verify your HireAI email, {first_name}"
        )

    def send_interview_reminder(
        self, 
        email: str, 
        full_name: str, 
        company: str, 
        role: str,
        interview_time: str, 
        hours_until: int
    ) -> bool:
        first_name = (full_name or "there").split()[0]
        urgency_color = BRAND['primary'] if hours_until > 6 else BRAND['warning']
        
        content = f"""
            <h1 style="margin:0 0 8px; font-size:26px; font-weight:800; color:{BRAND['text']}; text-align:center;">
                Interview reminder
            </h1>
            
            <p style="margin:0 0 24px; color:{BRAND['text_muted']}; font-size:15px; text-align:center;">
                Hi {first_name}, you have an upcoming interview.
            </p>
            
            <div style="margin:28px 0; padding:24px; background:{BRAND['dark']}; border-radius:16px; border-left:5px solid {urgency_color};">
                <p style="margin:0 0 4px; color:{BRAND['text_muted']}; font-size:12px; text-transform:uppercase; letter-spacing:1px;">
                    {company}
                </p>
                <p style="margin:0 0 12px; color:{BRAND['text']}; font-size:21px; font-weight:700; line-height:1.2;">
                    {role}
                </p>
                <p style="margin:0; color:{urgency_color}; font-size:15px; font-weight:600;">
                    ⏰ {interview_time} &nbsp;·&nbsp; in {hours_until} hours
                </p>
            </div>
            
            <p style="margin:0 0 20px; color:{BRAND['text_light']}; font-size:15px; text-align:center; line-height:1.5;">
                Need to prepare? HireAI has tailored interview questions ready for you.
            </p>
            
            {self._button("Prepare for Interview", "https://hireai.app/interview", size="large")}
        """
        
        text_body = f"""Interview Reminder

{role} at {company}
{interview_time} (in {hours_until}h)

Prep here: https://hireai.app/interview

© {datetime.now().year} HireAI"""

        return self.send_email(
            email,
            f"Interview at {company} in {hours_until}h",
            content,
            text_body,
            preheader=f"Interview at {company} coming up"
        )


# ── Global Instance & Convenience Functions ────────────────────
_email_service = EmailService()

# Convenience functions (backward compatible)
def send_reset_password_email(email: str, reset_link: str) -> bool:
    return _email_service.send_reset_password_email(email, reset_link)

def send_welcome_email(email: str, full_name: str) -> bool:
    return _email_service.send_welcome_email(email, full_name)

def send_verification_email(email: str, full_name: str, verify_link: str) -> bool:
    return _email_service.send_verification_email(email, full_name, verify_link)

def send_interview_reminder(email: str, full_name: str, company: str, role: str,
                           interview_time: str, hours_until: int) -> bool:
    return _email_service.send_interview_reminder(
        email, full_name, company, role, interview_time, hours_until
    )


def get_email_service() -> EmailService:
    """Get the global email service instance."""
    return _email_service


if __name__ == "__main__":
    print("Email service initialized successfully.")
    print(f"SMTP configured: {_email_service.config.is_configured}")