import json
import os
import ssl
from datetime import datetime
from html import escape
from typing import Any, Dict
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.db.master import get_master_connection



MAIL_AUTH_URL = os.getenv(
    "LOGIKLU_MAIL_AUTH_URL",
    "https://emailsendapi.zeetapro.com/mails.php?action=authorization",
)

MAIL_SEND_URL = os.getenv(
    "LOGIKLU_MAIL_SEND_URL",
    "https://emailsendapi.zeetapro.com/mails.php?action=sendemail",
)

LOGIKLU_ROOT_URL = os.getenv(
    "LOGIKLU_ROOT_URL",
    "https://logiklu.com/",
).rstrip("/") + "/"

DEFAULT_FROM_NAME = "LogiKlu Support"
DEFAULT_FROM_EMAIL = "info@logiklu.com"


class MailHelperError(Exception):
    pass


def _json_string(value: Any, default: Any) -> str:
    if value is None or value == "":
        return json.dumps(default, separators=(",", ":"))

    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return json.dumps(parsed, separators=(",", ":"))
        except Exception as exc:
            raise MailHelperError("Invalid JSON value supplied to mail helper") from exc

    return json.dumps(value, separators=(",", ":"), default=str)


def _post_form(url: str, payload: Dict[str, Any], timeout: int = 10) -> str:
    encoded = urlencode(
        {
            key: (
                json.dumps(value, separators=(",", ":"), default=str)
                if isinstance(value, (dict, list))
                else value
            )
            for key, value in payload.items()
        }
    ).encode("utf-8")

    request = Request(
        url,
        data=encoded,
        method="POST",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "LogiKlu-API-MailHelper/1.0",
        },
    )

    context = ssl.create_default_context()

    try:
        with urlopen(request, timeout=timeout, context=context) as response:
            return response.read().decode("utf-8")
    except Exception as exc:
        raise MailHelperError(f"Mail HTTP request failed: {exc}") from exc


def _get_email_db_connection():
    """
    Use the API server's existing master DB connection. The mail queue is
    addressed with its fully-qualified table name: email_send_db.email_send.
    """
    try:
        return get_master_connection()
    except Exception as exc:
        raise MailHelperError(f"Unable to connect to master database: {exc}") from exc


def prepare_mail_template(name: str = "", mail_content: str = "") -> str:
    now = datetime.now()
    today = f"{now.strftime('%B')} {now.day}, {now.year}"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{ margin: 0; padding: 0; font-size: 14px; }}
        p {{ font-family: Arial, Helvetica, sans-serif; font-size: 14px; margin: 0; padding: 0 10px; }}
        td {{ font-family: Arial, Helvetica, sans-serif; }}
        ul {{ padding: 0 0 0 25px; margin: 0; }}
        li {{ margin-left: 0; }}
        .hishab-table tr td table tr td {{ border-bottom: 0 !important; background-color: transparent !important; }}
        .total-price-tr td {{ font-family: Arial, Helvetica, sans-serif; background-color: transparent !important; border-top: 1px solid #000; font-weight: 600; }}
        .heading-of-td {{ letter-spacing: 1px; }}
        .total-price-tr td:nth-child(2n) {{ font-size: 19px; }}
        .logo-td a img {{ float: left; }}
        .logo-td a small {{ text-decoration: none; float: left; clear: both; font-family: Arial, Helvetica, sans-serif; color: #155e9b; font-weight: bold; position: relative; font-size: 13px; }}
        .mainTh-heading {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; color: #333; }}

        @media (max-width: 575.98px) {{
            .logo-td, .date-td {{ width: 100% !important; text-align: center; }}
            .left-td, .right-td {{ width: 100% !important; }}
            .left-td-padding, .right-td-padding {{ width: 100% !important; padding-top: 4px !important; }}
            .right-td, .right-td-padding {{ padding-left: 0 !important; border-left: 0 !important; }}
            .right-td {{ padding-top: 4px; }}
            .left-td p {{ margin-bottom: 20px; }}
            .border {{ display: none; }}
            tr td ul {{ padding-left: 20px; }}
            .align-right {{ text-align: right; }}
        }}

        @media (min-width: 576px) and (max-width: 767.98px) {{
            .left-td, .right-td {{ width: 100% !important; }}
            .left-td-padding, .right-td-padding {{ width: 100% !important; padding-top: 4px !important; }}
            .border {{ display: none; }}
            tr td ul {{ padding-left: 20px; }}
            .align-right {{ text-align: right; }}
            .right-td, .right-td-padding {{ padding-left: 0 !important; border-left: 0 !important; }}
            .right-td {{ padding-top: 4px; }}
            .left-td p {{ margin-bottom: 20px; }}
        }}
    </style>
</head>
<body>
    <table align="center" bgcolor="#fff" cellpadding="0" cellspacing="0"
           style="border: 10px solid #155e9b; width: 700px; max-width: 100%; padding: 10px"
           id="billingInvoice">
        <tbody style="background-color: #fff;">
            <tr>
                <td valign="top" align="left" style="padding: 0 10px">
                    <table cellpadding="0" cellspacing="0" style="width: 100%">
                        <tr><td style="width: 100%; padding: 7px 0;"></td></tr>
                        <tr>
                            <td class="logo-td" align="left" valign="top" style="padding: 0; width: 50%; float: left;">
                                <a href="#">
                                    <img src="{LOGIKLU_ROOT_URL}templates/creative/includes/images/newimages/logo.jpg" alt="logiklu" width="120">
                                    <small>Sales Intelligence Automation</small>
                                </a>
                            </td>
                            <td class="date-td" align="left" valign="top" style="width: 50%; float: left;">
                                <p style="padding: 0; text-align: right; color: #4a4848;">{today}</p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
            <tr><td style="width: 100%; padding: 7px 0; border-bottom: 1px solid #ddd;"></td></tr>
            <tr><td style="width: 100%; padding: 8px 0;"></td></tr>
            <tr>
                <td style="border-bottom: 1px solid #ddd; padding-bottom: 15px">[[MAINHTML]]</td>
            </tr>
            <tr>
                <td valign="top" align="center" style="padding: 15px 0; color: #444">
                    <p style="font-size: 12px;">&copy; {today} LogiKlu Inc. All rights reserved</p>
                </td>
            </tr>
        </tbody>
    </table>
    <a style="color:#FFF;font-size:0px;" href="{{unsubscribe:https://logiklu.com}}" target="_blank" title="Click to unsubscribe">a</a>
</body>
</html>"""

    html = html.replace("[[MAINHTML]]", mail_content or "")
    first_name = str(name or "").strip().split(" ")[0] if str(name or "").strip() else ""
    html = html.replace("[[NAME]]", first_name)
    return html


def send_email_postman(params: Dict[str, Any], timeout: int = 10) -> Dict[str, Any]:
    if not params:
        raise MailHelperError("Some parameters are missing")

    section = os.getenv("LOGIKLU_MAIL_SECTION", "LogiKlu").strip()
    auth_password = os.getenv("LOGIKLU_MAIL_AUTH_PASSWORD", "")

    if not auth_password:
        raise MailHelperError("LOGIKLU_MAIL_AUTH_PASSWORD is not configured")

    auth_raw = _post_form(
        MAIL_AUTH_URL,
        {
            "section": section,
            "authentication_password": auth_password,
        },
        timeout=timeout,
    )

    try:
        auth_response = json.loads(auth_raw)
    except Exception as exc:
        raise MailHelperError(
            f"Invalid authorization response from mail service: {auth_raw[:300]}"
        ) from exc

    if auth_response.get("status") != "success":
        return {
            "status": "error",
            "stage": "authorization",
            "response": auth_response,
        }

    token = None
    if isinstance(auth_response.get("data"), dict):
        token = auth_response["data"].get("token")

    if not token:
        raise MailHelperError("Mail authorization succeeded but no token was returned")

    to_json = _json_string(params.get("email_recepients_to"), [])
    cc_json = _json_string(params.get("email_recepients_cc"), [])
    bcc_json = _json_string(params.get("email_recepients_bcc"), [])
    attachments_json = _json_string(params.get("attachments"), [])
    client_info_json = _json_string(params.get("client_info"), [])
    from_json = _json_string(
        params.get("email_form"),
        {"name": DEFAULT_FROM_NAME, "email": DEFAULT_FROM_EMAIL},
    )
    reply_to_json = _json_string(
        params.get("in_reply_to"),
        {"name": DEFAULT_FROM_NAME, "email": DEFAULT_FROM_EMAIL},
    )

    subject = str(params.get("email_subject") or "").strip()
    body = str(params.get("email_body") or "")

    if to_json == "[]":
        raise MailHelperError("email_recepients_to is required")
    if not subject:
        raise MailHelperError("email_subject is required")
    if not body:
        raise MailHelperError("email_body is required")

    created_date = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    connection = _get_email_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO email_send_db.email_send
                (
                    token_section,
                    client_info,
                    email_recepients_to,
                    email_recepients_cc,
                    email_recepients_bcc,
                    email_subject,
                    email_body,
                    attachments,
                    email_form,
                    in_reply_to,
                    created_date
                )
                VALUES
                (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    section,
                    client_info_json,
                    to_json,
                    cc_json,
                    bcc_json,
                    subject,
                    body,
                    attachments_json,
                    from_json,
                    reply_to_json,
                    created_date,
                ),
            )
            mail_id = cursor.lastrowid
        connection.commit()
    except Exception as exc:
        try:
            connection.rollback()
        except Exception:
            pass
        raise MailHelperError(
            f"Unable to queue email in email_send_db.email_send: {exc}"
        ) from exc
    finally:
        connection.close()

    send_raw = _post_form(
        MAIL_SEND_URL,
        {"token": token, "mail_id": mail_id},
        timeout=timeout,
    )

    try:
        send_response = json.loads(send_raw)
    except Exception:
        send_response = {"raw_response": send_raw}

    return {
        "status": (
            "success"
            if isinstance(send_response, dict) and send_response.get("status") == "success"
            else "sent"
        ),
        "mail_id": mail_id,
        "authorization_status": auth_response.get("status"),
        "send_response": send_response,
    }



def prepare_otp_mail_template(mail_content: str = "") -> str:
    """
    Modern LogiKlu OTP-only email frame.

    Important:
    - This does NOT replace prepare_mail_template().
    - Password reset and other existing mail templates remain untouched.
    - OTP user/admin emails use this dedicated template.
    """
    now = datetime.now()
    today = f"{now.strftime('%B')} {now.day}, {now.year}"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body style="margin:0;padding:0;background:#f4f8fb;font-family:Arial,Helvetica,sans-serif;color:#082b55;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0"
           style="width:100%;background:#f4f8fb;margin:0;padding:0;">
        <tr>
            <td align="center" style="padding:46px 18px;">
                <table role="presentation" width="640" cellspacing="0" cellpadding="0" border="0"
                       style="
                           width:640px;
                           max-width:100%;
                           background:#ffffff;
                           border:1px solid #dfeaf2;
                           border-top:6px solid #149ed9;
                           border-radius:16px;
                           box-shadow:0 8px 24px rgba(24,75,112,0.10);
                           overflow:hidden;
                       ">
                    <tr>
                        <td style="padding:30px 28px 0 28px;">
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                                <tr>
                                    <td align="left" valign="middle" style="width:55%;">
                                        <img
                                            src="{LOGIKLU_ROOT_URL}templates/creative/includes/images/newimages/logo.jpg"
                                            alt="LogiKlu"
                                            width="150"
                                            style="display:block;width:150px;max-width:100%;height:auto;border:0;"
                                        >
                                    </td>
                                    <td align="right" valign="middle"
                                        style="
                                            width:45%;
                                            font-family:Arial,Helvetica,sans-serif;
                                            font-size:12px;
                                            color:#41658b;
                                            white-space:nowrap;
                                        ">
                                        {today}
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <tr>
                        <td style="padding:26px 28px 0 28px;">
                            <div style="height:1px;background:#d9e5ee;font-size:0;line-height:0;">&nbsp;</div>
                        </td>
                    </tr>

                    <tr>
                        <td style="
                            padding:28px;
                            font-family:Arial,Helvetica,sans-serif;
                            font-size:14px;
                            line-height:1.65;
                            color:#082b55;
                        ">
                            {mail_content}
                        </td>
                    </tr>

                    <tr>
                        <td style="padding:0 28px;">
                            <div style="height:1px;background:#d9e5ee;font-size:0;line-height:0;">&nbsp;</div>
                        </td>
                    </tr>

                    <tr>
                        <td align="center" style="
                            padding:24px 28px 28px 28px;
                            font-family:Arial,Helvetica,sans-serif;
                            color:#41658b;
                        ">
                            <div style="
                                font-size:12px;
                                line-height:1.5;
                                font-weight:700;
                                color:#074d8b;
                            ">
                                LogiKlu Inc.
                            </div>
                            <div style="
                                margin-top:8px;
                                font-size:11px;
                                line-height:1.5;
                                color:#637f9c;
                            ">
                                &copy; {now.year} LogiKlu Inc. All rights reserved.
                            </div>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>

    <a style="color:#ffffff;font-size:0;line-height:0;"
       href="{{unsubscribe:https://logiklu.com}}"
       target="_blank"
       title="Click to unsubscribe">a</a>
</body>
</html>"""

def send_logiklu_otp_email(
    recipient_name: str,
    recipient_email: str,
    otp: str,
    timeout: int = 10,
) -> Dict[str, Any]:
    """
    Send separate modern OTP emails to:
    1) the actual user
    2) LogiKlu OTP administrator mailbox

    The admin copy is a separate mail, not CC/BCC.
    """
    recipient_name = str(recipient_name or "").strip()
    recipient_email = str(recipient_email or "").strip()
    otp = str(otp or "").strip()

    if not recipient_email:
        raise MailHelperError("Recipient email is required")

    if not otp:
        raise MailHelperError("OTP is required")

    safe_name = escape(recipient_name or "User")
    safe_email = escape(recipient_email)
    safe_otp = escape(otp)
    otp_display = " ".join(list(otp))

    # ---------------------------------------------------------
    # USER EMAIL
    # ---------------------------------------------------------
    user_content = f"""
        <p style="
            margin:0 0 12px 0;
            padding:0;
            font-family:Arial,Helvetica,sans-serif;
            font-size:16px;
            line-height:1.5;
            font-weight:700;
            color:#082b55;
        ">
            Hi {safe_name.split(" ")[0]},
        </p>

        <p style="
            margin:0;
            padding:0;
            font-family:Arial,Helvetica,sans-serif;
            font-size:14px;
            line-height:1.7;
            color:#082b55;
        ">
            Use the verification code below to complete your LogiKlu sign-in.
        </p>

        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0"
               style="margin-top:24px;">
            <tr>
                <td align="center" style="
                    padding:25px 18px;
                    background:#eef8ff;
                    border:1px solid #a9dcfa;
                    border-radius:14px;
                ">
                    <div style="
                        font-family:Arial,Helvetica,sans-serif;
                        font-size:12px;
                        line-height:1.4;
                        font-weight:700;
                        letter-spacing:2px;
                        color:#5d7898;
                    ">
                        VERIFICATION CODE
                    </div>

                    <div style="
                        margin-top:11px;
                        font-family:Arial,Helvetica,sans-serif;
                        font-size:36px;
                        line-height:1.2;
                        font-weight:700;
                        letter-spacing:6px;
                        color:#064f8f;
                    ">
                        {escape(otp_display)}
                    </div>

                    <div style="
                        margin-top:10px;
                        font-family:Arial,Helvetica,sans-serif;
                        font-size:13px;
                        line-height:1.5;
                        color:#4f6f8e;
                    ">
                        This code expires in 5 minutes.
                    </div>
                </td>
            </tr>
        </table>
    """

    user_mail_html = prepare_otp_mail_template(
        user_content
    )

    user_result = send_email_postman(
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
            "email_body": user_mail_html,
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

    if str(user_result.get("status") or "").strip().lower() == "error":
        return user_result

    # ---------------------------------------------------------
    # ADMINISTRATOR EMAIL
    # ---------------------------------------------------------
    admin_content = f"""
        <p style="
            margin:0 0 12px 0;
            padding:0;
            font-family:Arial,Helvetica,sans-serif;
            font-size:16px;
            line-height:1.5;
            font-weight:700;
            color:#082b55;
        ">
            Hi Administrator,
        </p>

        <p style="
            margin:0;
            padding:0;
            font-family:Arial,Helvetica,sans-serif;
            font-size:14px;
            line-height:1.7;
            color:#082b55;
        ">
            <strong>{safe_name}</strong> ({safe_email}) is trying to sign in to
            LogiKlu. The user verification code is shown below.
        </p>

        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0"
               style="margin-top:24px;">
            <tr>
                <td align="center" style="
                    padding:25px 18px;
                    background:#eef8ff;
                    border:1px solid #a9dcfa;
                    border-radius:14px;
                ">
                    <div style="
                        font-family:Arial,Helvetica,sans-serif;
                        font-size:12px;
                        line-height:1.4;
                        font-weight:700;
                        letter-spacing:2px;
                        color:#5d7898;
                    ">
                        VERIFICATION CODE
                    </div>

                    <div style="
                        margin-top:11px;
                        font-family:Arial,Helvetica,sans-serif;
                        font-size:36px;
                        line-height:1.2;
                        font-weight:700;
                        letter-spacing:6px;
                        color:#064f8f;
                    ">
                        {escape(otp_display)}
                    </div>

                    <div style="
                        margin-top:10px;
                        font-family:Arial,Helvetica,sans-serif;
                        font-size:13px;
                        line-height:1.5;
                        color:#4f6f8e;
                    ">
                        This code expires in 5 minutes.
                    </div>
                </td>
            </tr>
        </table>
    """

    admin_mail_html = prepare_otp_mail_template(
        admin_content
    )

    try:
        admin_result = send_email_postman(
            {
                "client_info": {
                    "client_name": "LogiKlu",
                    "website": "https://logiklu.com",
                    "section": "OTP",
                },
                "email_recepients_to": [
                    {
                        "name": "LogiKlu OTP user",
                        "email": "logikluotp@gmail.com",
                    }
                ],
                "email_subject": (
                    f"OTP of user {recipient_name}({recipient_email}) "
                    "for login into LogiKlu"
                ),
                "email_body": admin_mail_html,
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
    except Exception as exc:
        # User OTP already succeeded; admin support copy must not block login.
        admin_result = {
            "status": "error",
            "message": str(exc),
        }

    return {
        "status": user_result.get("status", "success"),
        "user_mail": user_result,
        "admin_mail": admin_result,
    }


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
        <p style="font-size:1.1em">Hi [[NAME]],</p>
        <p>
            Please <a href="{safe_link}" target="_blank">click here</a>
            to reset your password. This link will expire in 48 hours.
        </p>
        <p>&nbsp;</p>
        <p style="font-size:0.9em;">Regards,<br />LogiKlu Support</p>
    """

    mail_html = prepare_mail_template(recipient_name, content)

    return send_email_postman(
        {
            "client_info": {
                "client_name": "LogiKlu",
                "website": "https://logiklu.com",
                "section": "Password Reset",
            },
            "email_recepients_to": [
                {"name": recipient_name, "email": recipient_email}
            ],
            "email_subject": "Reset Password for LogiKlu",
            "email_body": mail_html,
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
