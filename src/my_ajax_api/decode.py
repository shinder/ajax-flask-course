"""終端機工具：解開 JWT 或 session Cookie，印出內容並用 app 的金鑰驗簽章（講義 9-8、10-1）。

    uv run flask decode jwt <token>          # 第 9 章的 token
    uv run flask decode session <cookie 值>  # 第 10 章的 session Cookie

兩種東西的結構一樣：以 . 分隔的幾段 Base64Url，前面是可讀的內容、最後一段是簽章。
這支工具做的事和 login.html 的 decodePayload()、講義 10-1 的 Console 示範相同，
多了一步：拿 app.config 裡的金鑰重算簽章，看內容有沒有被改過。
放在套件裡、做成 Flask CLI 指令（和 db.py 的 init-db 同一套做法），就是為了拿得到金鑰。
"""

import base64
import hashlib
import hmac
import json
import zlib
from datetime import datetime, timezone

import click
from flask import current_app
from flask.cli import with_appcontext
from flask.sessions import SecureCookieSessionInterface
from itsdangerous import BadSignature


def base64url_decode(segment: str) -> bytes:
    """Base64Url → bytes。和標準 Base64 的差別：- _ 取代 + /，而且省略結尾的 = 補位。"""
    padding = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + padding)


def _pretty(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def _fmt_time(ts: int | float) -> str:
    """Unix 秒數 → 本地時間字串。"""
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def _fmt_remaining(exp: int | float) -> str:
    seconds = int(exp - datetime.now(timezone.utc).timestamp())
    if seconds < 0:
        return f"已過期 {-seconds // 60} 分鐘"
    return f"還有 {seconds // 60} 分 {seconds % 60} 秒"


def _verdict(ok: bool, detail: str = "") -> str:
    return click.style("正確", fg="green") if ok else click.style(f"不正確{detail}", fg="red")


@click.group("decode")
def cli():
    """解開 JWT 或 session Cookie，印出內容並驗簽章。"""


@cli.command("jwt")
@click.argument("token")
@with_appcontext
def decode_jwt(token: str):
    """解開 JWT：印出 Header、Payload、時間，並用 JWT_KEY 驗簽章。"""
    parts = token.strip().split(".")
    if len(parts) != 3:
        raise click.ClickException(f"JWT 應該有三段（以 . 分隔），收到 {len(parts)} 段")
    header_b64, payload_b64, signature_b64 = parts

    try:
        header = json.loads(base64url_decode(header_b64))
        payload = json.loads(base64url_decode(payload_b64))
    except (ValueError, json.JSONDecodeError) as exc:
        raise click.ClickException(f"前兩段不是 Base64Url 編碼的 JSON：{exc}") from None
    signature = base64url_decode(signature_b64)

    click.echo(click.style("Header", bold=True))
    click.echo(_pretty(header))
    click.echo(click.style("Payload", bold=True))
    click.echo(_pretty(payload))
    if "iat" in payload:
        click.echo(f"  iat = {_fmt_time(payload['iat'])}（簽發時間，本地時區）")
    if "exp" in payload:
        click.echo(f"  exp = {_fmt_time(payload['exp'])}，{_fmt_remaining(payload['exp'])}")

    # 簽章 = HMAC-SHA256(金鑰, "header.payload")。自己重算一次和第三段比對，
    # 和 tokens.py 用 jwt.decode() 驗證是同一件事，這裡拆開來看清楚每一步
    click.echo(click.style("Signature", bold=True) + f"  {len(signature)} bytes")
    if header.get("alg") != "HS256":
        click.echo(f"  alg 是 {header.get('alg')!r}，本專案只簽 HS256，略過驗證")
        return
    key = current_app.config["JWT_KEY"].encode()
    expected = hmac.new(key, f"{header_b64}.{payload_b64}".encode(), hashlib.sha256).digest()
    ok = hmac.compare_digest(signature, expected)
    click.echo(f"  用 JWT_KEY 驗證：{_verdict(ok, '（內容被改過，或簽發時用的不是這把金鑰）')}")


@cli.command("session")
@click.argument("cookie")
@with_appcontext
def decode_session(cookie: str):
    """解開 session Cookie：印出內容、簽發時間，並用 SECRET_KEY 驗簽章。"""
    cookie = cookie.strip()
    # 內容較長時 Flask 會先用 zlib 壓縮，並在最前面加一個 . 做記號
    compressed = cookie.startswith(".")
    parts = cookie.lstrip(".").split(".")
    if len(parts) != 3:
        raise click.ClickException(f"session Cookie 應該有三段（以 . 分隔），收到 {len(parts)} 段")
    payload_b64, timestamp_b64, signature_b64 = parts

    try:
        raw = base64url_decode(payload_b64)
        if compressed:
            raw = zlib.decompress(raw)
        payload = json.loads(raw)
    except (ValueError, zlib.error, json.JSONDecodeError) as exc:
        raise click.ClickException(f"第一段不是 Base64Url 編碼的 JSON：{exc}") from None
    # 第二段是 big-endian 的整數秒
    timestamp = int.from_bytes(base64url_decode(timestamp_b64), "big")

    click.echo(click.style("Payload", bold=True) + ("（zlib 壓縮過）" if compressed else ""))
    click.echo(_pretty(payload))
    click.echo(click.style("Timestamp", bold=True) + f"  {_fmt_time(timestamp)}（簽發時間，本地時區）")

    # 簽章交給 Flask 自己的 serializer 驗（itsdangerous 的 URLSafeTimedSerializer，
    # 金鑰是 SECRET_KEY 加上 salt "cookie-session"，HMAC-SHA1），和它讀取請求時做的事相同
    signature = base64url_decode(signature_b64)
    click.echo(click.style("Signature", bold=True) + f"  {len(signature)} bytes")
    interface = current_app.session_interface
    if not isinstance(interface, SecureCookieSessionInterface):
        click.echo("  session 不是內建的簽章 Cookie（例如換成了 Flask-Session），無法驗證")
        return
    serializer = interface.get_signing_serializer(current_app)
    if serializer is None:
        click.echo("  SECRET_KEY 未設定，無法驗證")
        return
    try:
        serializer.loads(cookie)
        ok = True
    except BadSignature:
        ok = False
    click.echo(f"  用 SECRET_KEY 驗證：{_verdict(ok, '（內容被改過，或簽發時用的不是這把金鑰）')}")


def init_app(app):
    """掛到 app 上：flask decode jwt / flask decode session。"""
    app.cli.add_command(cli)
