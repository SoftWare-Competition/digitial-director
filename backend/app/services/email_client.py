"""QQ 邮箱 SMTP 客户端 — 发送验证码邮件."""

import smtplib
import random
import string
from email.header import Header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from datetime import datetime, timedelta, timezone

from app.config import settings


def generate_code(length: int = 6) -> str:
    """生成随机数字验证码"""
    return ''.join(random.choices(string.digits, k=length))


def send_verification_email(to_email: str, code: str) -> tuple[bool, str]:
    """
    通过 QQ 邮箱 SMTP 发送验证码邮件。

    返回: (成功标志, 消息)
    """
    subject = f"【灵山AI导游】邮箱验证码：{code}"

    html_body = f"""
    <div style="max-width:480px;margin:0 auto;padding:30px;font-family:'PingFang SC','Microsoft YaHei',sans-serif;
                background:linear-gradient(135deg,#f0f7f0 0%,#e8f4e8 100%);
                border-radius:16px;border:1px solid #c8e6c9;">
        <div style="text-align:center;margin-bottom:24px;">
            <h1 style="color:#1a6d4c;font-size:24px;margin:0;">🏯 灵山胜境 · AI导游</h1>
            <p style="color:#666;font-size:13px;margin:6px 0 0;">Lingshan AI Tour Guide</p>
        </div>

        <div style="background:#fff;border-radius:12px;padding:24px;text-align:center;">
            <p style="color:#333;font-size:15px;margin:0 0 8px;">您的邮箱验证码为：</p>
            <div style="font-size:36px;font-weight:700;letter-spacing:8px;color:#1a6d4c;
                        background:#f0f7f0;padding:12px 0;border-radius:8px;margin:12px 0;">
                {code}
            </div>
            <p style="color:#999;font-size:12px;margin:8px 0 0;">验证码 10 分钟内有效，请勿透露给他人</p>
        </div>

        <div style="margin-top:20px;text-align:center;">
            <p style="color:#aaa;font-size:11px;margin:0;">
                此邮件由系统自动发送，请勿回复<br/>
                © 2026 灵山胜境 AI 数字人导游
            </p>
        </div>
    </div>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = Header(subject, "utf-8")
    # 使用 formataddr + Header 正确编码中文发件人名称
    msg["From"] = formataddr((str(Header(settings.smtp_from_name, "utf-8")), settings.smtp_username))
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15)
        server.starttls()
        server.login(settings.smtp_username, settings.smtp_password)
        server.sendmail(settings.smtp_username, [to_email], msg.as_string())
        server.quit()
        print(f"[Email] 验证码已发送到 {to_email}")
        return True, "验证码已发送"
    except smtplib.SMTPAuthenticationError:
        print(f"[Email] SMTP 认证失败，请检查邮箱授权码")
        return False, "邮件服务配置错误"
    except smtplib.SMTPException as e:
        print(f"[Email] SMTP 发送失败: {e}")
        return False, f"邮件发送失败: {str(e)}"
    except Exception as e:
        print(f"[Email] 未知错误: {e}")
        return False, "邮件发送异常"
