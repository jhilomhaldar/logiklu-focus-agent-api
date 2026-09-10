import os
from datetime import datetime
from html import escape
from typing import Any, Dict


LOGIKLU_ROOT_URL = os.getenv(
    "LOGIKLU_ROOT_URL",
    "https://logiklu.com/",
).rstrip("/") + "/"

DEFAULT_FROM_NAME = "LogiKlu Support"
DEFAULT_FROM_EMAIL = "info@logiklu.com"


class MailHelperError(Exception):
    pass


def prepare_mail_template(name: str = "", mail_content: str = "") -> str:
    """
    Modern LogiKlu transactional email wrapper.

    Brand direction:
    - Primary blue: #1797D7
    - Deep blue: #0F4C81
    - Navy text: #16324F
    - Soft background: #F4F8FB
    - Light border: #DCE8F2

    Current LogiKlu caption:
    
    """
    now = datetime.now()
    today = f"{now.strftime('%B')} {now.day}, {now.year}"

    first_name = (
        str(name or "").strip().split(" ")[0]
        if str(name or "").strip()
        else ""
    )

    content = (mail_content or "").replace("[[NAME]]", first_name)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="color-scheme" content="light">
    <meta name="supported-color-schemes" content="light">
    <title>LogiKlu</title>
</head>

<body style="margin:0;padding:0;background:#F4F8FB;font-family:Arial,Helvetica,sans-serif;color:#16324F;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
           style="width:100%;margin:0;padding:0;background:#F4F8FB;">
        <tr>
            <td align="center" style="padding:32px 16px;">

                <table role="presentation" width="640" cellpadding="0" cellspacing="0" border="0"
                       style="width:100%;max-width:640px;background:#FFFFFF;border:1px solid #DCE8F2;
                              border-radius:18px;overflow:hidden;
                              box-shadow:0 10px 30px rgba(15,76,129,0.08);">

                    <!-- Brand accent -->
                    <tr>
                        <td style="height:6px;background:#1797D7;font-size:0;line-height:0;">&nbsp;</td>
                    </tr>

                    <!-- Header -->
                    <tr>
                        <td style="padding:26px 30px 22px 30px;">
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                                <tr>
                                    <td valign="middle" style="width:52%;">
                                        <a href="https://logiklu.com/" target="_blank"
                                           style="text-decoration:none;border:0;">
                                            <img src="{LOGIKLU_ROOT_URL}templates/creative/includes/assets/img/logo.png"
                                                 alt="LogiKlu"
                                                 width="150"
                                                 style="display:block;width:150px;max-width:100%;height:auto;border:0;">
                                        </a>

                                        <div style="margin-top:9px;font-size:12px;line-height:18px;
                                                    color:#0F4C81;font-weight:700;letter-spacing:0.2px;">
                                            
                                        </div>
                                    </td>

                                    <td valign="top" align="right"
                                        style="width:48%;font-size:12px;line-height:18px;color:#6D8194;">
                                        {today}
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Divider -->
                    <tr>
                        <td style="padding:0 30px;">
                            <div style="height:1px;background:#E6EEF5;font-size:0;line-height:0;">&nbsp;</div>
                        </td>
                    </tr>

                    <!-- Main content -->
                    <tr>
                        <td style="padding:30px;font-size:15px;line-height:24px;color:#29465F;">
                            {content}
                        </td>
                    </tr>

                    <!-- Footer divider -->
                    <tr>
                        <td style="padding:0 30px;">
                            <div style="height:1px;background:#E6EEF5;font-size:0;line-height:0;">&nbsp;</div>
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td align="center" style="padding:22px 30px 26px 30px;">
                            <div style="font-size:12px;line-height:18px;color:#6D8194;">
                                <strong style="color:#0F4C81;">LogiKlu Inc.</strong><br>
                                
                            </div>

                            <div style="margin-top:9px;font-size:11px;line-height:17px;color:#8A9AAA;">
                                &copy; {now.year} LogiKlu Inc. All rights reserved.
                            </div>

                            <div style="margin-top:10px;font-size:11px;line-height:17px;">
                                <a href="https://logiklu.com/" target="_blank"
                                   style="color:#1797D7;text-decoration:none;font-weight:600;">
                                    logiklu.com
                                </a>
                            </div>
                        </td>
                    </tr>

                </table>

                <div style="max-width:640px;margin:14px auto 0 auto;
                            font-size:10px;line-height:15px;color:#A0AFBC;text-align:center;">
                    This is an automated message from LogiKlu.
                </div>

                <a style="color:#F4F8FB;font-size:0;line-height:0;"
                   href="{{unsubscribe:https://logiklu.com}}"
                   target="_blank"
                   title="Click to unsubscribe">unsubscribe</a>

            </td>
        </tr>
    </table>
</body>
</html>"""

    return html


def send_email_postman(
    params: Dict[str, Any],
    timeout: int = 10,
) -> Dict[str, Any]:
    """
    Compatibility wrapper for existing Device Auth code.

    It now calls the Python mail service directly.
    There is no HTTP request to logiklu.com/app/emailsendprocess.php.
    """
    try:
        from app.services.mail_service import send_email

        return send_email(
            params=params,
            timeout=timeout,
        )

    except Exception as exc:
        raise MailHelperError(str(exc)) from exc


def send_logiklu_otp_email(
    recipient_name: str,
    recipient_email: str,
    otp: str,
    timeout: int = 10,
) -> Dict[str, Any]:
    recipient_name = str(recipient_name or "").strip()
    recipient_email = str(recipient_email or "").strip()
    otp = str(otp or "").strip()

    if not recipient_email:
        raise MailHelperError("Recipient email is required")

    if not otp:
        raise MailHelperError("OTP is required")

    content = f"""
        <div style="font-size:15px;line-height:24px;color:#29465F;">
            <div style="font-size:16px;font-weight:700;color:#16324F;margin-bottom:8px;">
                Hi [[NAME]],
            </div>

            <div style="margin-bottom:20px;">
                Use the verification code below to complete your LogiKlu sign-in.
            </div>

            <div style="background:#F1F8FC;border:1px solid #CFE7F5;border-radius:14px;
                        padding:24px 18px;text-align:center;margin:0 0 20px 0;">
                <div style="font-size:11px;line-height:16px;color:#6D8194;
                            text-transform:uppercase;letter-spacing:1.2px;font-weight:700;">
                    Verification code
                </div>

                <div style="margin-top:8px;font-size:34px;line-height:42px;
                            letter-spacing:7px;font-weight:800;color:#0F4C81;">
                    {escape(otp)}
                </div>

                <div style="margin-top:8px;font-size:12px;line-height:18px;color:#6D8194;">
                    This code expires in 5 minutes.
                </div>
            </div>

            <div style="font-size:13px;line-height:20px;color:#6D8194;">
                If you did not request this sign-in, you can safely ignore this email.
            </div>
        </div>
    """

    return send_email_postman(
        {
            "client_info": {
                "client_name": "LogiKlu",
                "website": "https://logiklu.com",
                "section": "OTP",
            },
            "email_recepients_to": [
                {
                    "name": recipient_name,
                    "email": recipient_email,
                }
            ],
            "email_subject": "OTP for login into LogiKlu",
            "email_body": prepare_mail_template(
                recipient_name,
                content,
            ),
            "email_form": {
                "name": DEFAULT_FROM_NAME,
                "email": DEFAULT_FROM_EMAIL,
            },
            "in_reply_to": {
                "name": DEFAULT_FROM_NAME,
                "email": DEFAULT_FROM_EMAIL,
            },
        },
        timeout=timeout,
    )


def send_logiklu_password_reset_email(
    recipient_name: str,
    recipient_email: str,
    reset_link: str,
    timeout: int = 10,
) -> Dict[str, Any]:
    recipient_name = str(recipient_name or "").strip()
    recipient_email = str(recipient_email or "").strip()
    reset_link = str(reset_link or "").strip()

    if not recipient_email:
        raise MailHelperError("Recipient email is required")

    if not reset_link:
        raise MailHelperError("Password reset link is required")

    safe_link = escape(reset_link, quote=True)

    content = f"""
        <div style="font-size:15px;line-height:24px;color:#29465F;">
            <div style="font-size:16px;font-weight:700;color:#16324F;margin-bottom:8px;">
                Hi [[NAME]],
            </div>

            <div style="margin-bottom:22px;">
                We received a request to reset your LogiKlu password.
            </div>

            <div style="text-align:center;margin:0 0 22px 0;">
                <a href="{safe_link}" target="_blank"
                   style="display:inline-block;background:#1797D7;color:#FFFFFF;
                          text-decoration:none;font-size:14px;font-weight:700;
                          line-height:20px;padding:13px 24px;border-radius:9px;">
                    Reset Password
                </a>
            </div>

            <div style="font-size:13px;line-height:20px;color:#6D8194;margin-bottom:10px;">
                This reset link will expire in 48 hours.
            </div>

            <div style="font-size:13px;line-height:20px;color:#6D8194;">
                If you did not request a password reset, you can safely ignore this email.
            </div>
        </div>
    """

    return send_email_postman(
        {
            "client_info": {
                "client_name": "LogiKlu",
                "website": "https://logiklu.com",
                "section": "Password Reset",
            },
            "email_recepients_to": [
                {
                    "name": recipient_name,
                    "email": recipient_email,
                }
            ],
            "email_subject": "Reset Password for LogiKlu",
            "email_body": prepare_mail_template(
                recipient_name,
                content,
            ),
            "email_form": {
                "name": DEFAULT_FROM_NAME,
                "email": DEFAULT_FROM_EMAIL,
            },
            "in_reply_to": {
                "name": DEFAULT_FROM_NAME,
                "email": DEFAULT_FROM_EMAIL,
            },
        },
        timeout=timeout,
    )
