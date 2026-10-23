"""Local SMTP server for end-to-end tests: requires STARTTLS + AUTH like Gmail, saves every message."""
import datetime
import ipaddress
import json
import ssl
import sys
import time
from pathlib import Path

from aiosmtpd.controller import Controller
from aiosmtpd.smtp import AuthResult, LoginPassword
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

HERE = Path(__file__).parent
MAIL_DIR = HERE / "mail"
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8587


def make_cert():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1)).not_valid_after(now + datetime.timedelta(days=2))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName("localhost"),
                                                    x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]), False)
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), True)
        .sign(key, hashes.SHA256())
    )
    (HERE / "cert.pem").write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    (HERE / "key.pem").write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                                     serialization.NoEncryption()))


def authenticator(server, session, envelope, mechanism, auth_data):
    ok = isinstance(auth_data, LoginPassword) and auth_data.login == b"me@kjs-e2e.com" and auth_data.password == b"apppassword"
    return AuthResult(success=ok)


class Handler:
    async def handle_RCPT(self, server, session, envelope, address, rcpt_options):
        if address.startswith("reject"):
            return "550 5.1.1 Mailbox not found"
        envelope.rcpt_tos.append(address)
        return "250 OK"

    async def handle_DATA(self, server, session, envelope):
        n = len(list(MAIL_DIR.glob("*.json"))) + 1
        (MAIL_DIR / f"{n:04d}.json").write_text(json.dumps({
            "mail_from": envelope.mail_from,
            "rcpt_tos": envelope.rcpt_tos,
            "tls": session.ssl is not None,
            "authenticated": session.authenticated,
            "data": envelope.content.decode("utf-8", "replace"),
        }))
        return "250 Message accepted"


if __name__ == "__main__":
    MAIL_DIR.mkdir(exist_ok=True)
    make_cert()
    ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ctx.load_cert_chain(HERE / "cert.pem", HERE / "key.pem")
    controller = Controller(Handler(), hostname="127.0.0.1", port=PORT, tls_context=ctx, require_starttls=True,
                            authenticator=authenticator, auth_require_tls=True, auth_required=True,
                            auth_exclude_mechanism=["LOGIN"])  # LOGIN hangs on bad passwords in aiosmtpd
    controller.start()
    print("SMTP ready", flush=True)
    while True:
        time.sleep(1)
