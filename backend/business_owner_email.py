"""Transactional invite email for business-owner account access."""
from __future__ import annotations

import html
from datetime import datetime


EMAIL_SUBJECT = "Create your YourNotDown business account"


def _escape(value: str) -> str:
    return html.escape(value or "", quote=True)


def _friendly_expiration(value: str) -> str:
    if not value:
        return "7 days"
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return "7 days"
    return f"{dt.strftime('%b')} {dt.day}, {dt.year}"


def business_owner_invite_email_subject(_: dict) -> str:
    return EMAIL_SUBJECT


def business_owner_invite_email_content(payload: dict) -> tuple[str, str]:
    business_name = _escape(payload.get("business_name", "Your venue"))
    claim_url = _escape(payload.get("claim_url", ""))
    expires_label = _friendly_expiration(payload.get("expires_at", ""))
    text = "\n".join([
        "YOURNOTDOWN",
        "Business Account",
        "",
        f"{business_name} has been invited to create a YourNotDown business account.",
        "Use the link below to claim access:",
        payload.get("claim_url", ""),
        "",
        f"This link expires on {expires_label}.",
        "",
        "Built with YourNotDown",
    ])
    html_body = f"""
<!DOCTYPE html>
<html lang="en">
  <body style="margin:0;background:#020202;color:#ffffff;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
    <div style="padding:32px 16px;background:#020202;">
      <div style="max-width:600px;margin:0 auto;border:1px solid rgba(255,255,255,0.08);background:#0a0a0a;">
        <div style="padding:28px 28px 12px;">
          <div style="font-size:28px;letter-spacing:0.28em;font-weight:800;color:#C6FF00;">YND
            <span style="font-size:12px;letter-spacing:0.22em;color:rgba(255,255,255,0.55);font-weight:700;"> / EST. 26</span>
          </div>
          <div style="margin-top:10px;width:84px;height:2px;background:#C6FF00;"></div>
          <div style="margin-top:18px;font-size:11px;letter-spacing:0.26em;text-transform:uppercase;color:rgba(255,255,255,0.45);">Business Access</div>
          <h1 style="margin:12px 0 0;font-size:40px;line-height:0.95;text-transform:uppercase;">Create Account</h1>
          <p style="margin:16px 0 0;font-size:15px;line-height:1.7;color:rgba(255,255,255,0.72);">
            {business_name} has been invited to access its YourNotDown business portal.
          </p>
        </div>
        <div style="padding:0 28px 28px;">
          <div style="border:1px solid rgba(255,255,255,0.08);background:#121218;padding:20px;">
            <div style="font-size:11px;letter-spacing:0.24em;text-transform:uppercase;color:rgba(255,255,255,0.45);">Venue</div>
            <div style="margin-top:8px;font-size:24px;font-weight:800;color:#ffffff;">{business_name}</div>
            <p style="margin:14px 0 0;font-size:14px;line-height:1.7;color:rgba(255,255,255,0.72);">
              Claim access with the secure magic link below. No password is required for this MVP.
            </p>
            <div style="margin-top:22px;">
              <a href="{claim_url}" style="display:inline-block;padding:14px 22px;background:#C6FF00;color:#020202;text-decoration:none;font-size:11px;font-weight:800;letter-spacing:0.22em;text-transform:uppercase;">
                Create Account
              </a>
            </div>
            <p style="margin:18px 0 0;font-size:12px;line-height:1.6;color:rgba(255,255,255,0.5);">
              This link expires on {expires_label}.
            </p>
            <p style="margin:12px 0 0;font-size:12px;line-height:1.6;color:rgba(255,255,255,0.4);word-break:break-all;">
              {claim_url}
            </p>
          </div>
          <div style="margin-top:18px;font-size:12px;color:rgba(255,255,255,0.42);">
            Built with YourNotDown
          </div>
        </div>
      </div>
    </div>
  </body>
</html>
""".strip()
    return text, html_body
