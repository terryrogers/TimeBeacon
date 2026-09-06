"""Configured SMTP delivery; secrets stay encrypted in the identity database."""
import logging
import smtplib
import ssl
from email.message import EmailMessage
from urllib.parse import urlsplit
from fastapi import HTTPException, Request
from pydantic import BaseModel, Field, field_validator, model_validator
from security import IdentityStore

logger = logging.getLogger(__name__)


def valid_address(value):
    value = value.strip()
    if not value or '@' not in value or '.' not in value.split('@')[-1] or any(c.isspace() for c in value) or any(c in value for c in '\r\n<>;,'):
        raise ValueError('Enter a valid email address')
    return value


class EmailConfiguration(BaseModel):
    version: int
    hostname: str = Field(min_length=1, max_length=253, pattern=r'^[A-Za-z0-9_.:-]+$')
    port: int = Field(ge=1, le=65535)
    security: str = Field(pattern=r'^(starttls|ssl|none)$')
    username: str = Field(default='', max_length=254)
    password: str = Field(default='', max_length=2048)
    from_email: str = Field(max_length=254)
    from_name: str = Field(default='TimeBeacon', max_length=120)
    public_url: str = Field(max_length=500)

    @field_validator('from_email')
    @classmethod
    def email(cls, value):
        return valid_address(value)

    @field_validator('from_name', 'username')
    @classmethod
    def no_newlines(cls, value):
        if '\r' in value or '\n' in value:
            raise ValueError('Line breaks are not allowed')
        return value.strip()

    @field_validator('public_url')
    @classmethod
    def origin(cls, value):
        parsed = urlsplit(value)
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.path not in ('', '/') or parsed.query or parsed.fragment:
            raise ValueError('Enter the HTTPS dashboard origin without a path')
        return value.rstrip('/')

    @model_validator(mode='after')
    def encrypted_login(self):
        if self.username and self.security == 'none':
            raise ValueError('SMTP authentication requires STARTTLS or SSL/TLS')
        return self


class TestEmail(BaseModel):
    to_email: str = Field(max_length=254)
    _email = field_validator('to_email')(valid_address)


def configuration(monitor):
    return monitor.get_settings()['settings'].get('email', {})


def ready(monitor):
    config = configuration(monitor)
    return all(config.get(key) for key in ('hostname', 'port', 'from_email', 'public_url'))


def send_message(monitor, recipient, subject, text):
    config = configuration(monitor)
    if not ready(monitor):
        raise RuntimeError('Email is not configured')
    valid_address(recipient)
    message = EmailMessage()
    from email.utils import formataddr
    message['From'] = formataddr((config.get('from_name', 'TimeBeacon'), config['from_email']))
    message['To'] = recipient
    message['Subject'] = subject
    message.set_content(text)
    context = ssl.create_default_context()
    factory = smtplib.SMTP_SSL if config['security'] == 'ssl' else smtplib.SMTP
    options = {'timeout': 15}
    if config['security'] == 'ssl':
        options['context'] = context
    with factory(config['hostname'], config['port'], **options) as connection:
        connection.ehlo()
        if config['security'] == 'starttls':
            connection.starttls(context=context)
            connection.ehlo()
        if config.get('username'):
            password = IdentityStore(monitor).cipher().decrypt(config['password_encrypted'].encode()).decode()
            connection.login(config['username'], password)
        connection.send_message(message)


def safe_send(monitor, recipient, subject, text):
    try:
        send_message(monitor, recipient, subject, text)
    except Exception:
        # Do not log recipients, reset links, SMTP credentials or server replies.
        logger.warning('TimeBeacon recovery email delivery failed; check Administration Email configuration.')


def install(app, backend):
    def admin(request, mutation=False):
        store = IdentityStore(backend.monitor)
        user = store.authenticate(request)
        store.require(user, 'admin')
        if mutation:
            store.same_origin(request)
        return store

    @app.get('/administration/email', include_in_schema=False)
    def get_email(request: Request):
        admin(request)
        state = backend.monitor.get_settings()
        values = state['settings'].get('email', {}).copy()
        values['password_set'] = bool(values.pop('password_encrypted', ''))
        return {'version': state['version'], 'settings': values, 'configured': ready(backend.monitor)}

    @app.put('/administration/email', include_in_schema=False)
    def save_email(request: Request, body: EmailConfiguration):
        store = admin(request, True)
        values = body.model_dump(exclude={'version', 'password'})
        encrypted = configuration(backend.monitor).get('password_encrypted', '')
        if body.password:
            encrypted = store.cipher().encrypt(body.password.encode()).decode()
        if body.username and not encrypted:
            raise HTTPException(422, 'Enter the SMTP password')
        values['password_encrypted'] = encrypted if body.username else ''
        saved = backend.monitor.save_settings(body.version, {'email': values})
        if saved is None:
            raise HTTPException(409, 'Configuration changed. Reload and retry.')
        return {'success': True, 'version': saved['version']}

    @app.post('/administration/email/test', include_in_schema=False)
    def test_email(request: Request, body: TestEmail):
        admin(request, True)
        from auth_flows import throttle
        throttle(backend.monitor, 'email-test:'+str(IdentityStore(backend.monitor).authenticate(request)['id']), 5, 300)
        try:
            send_message(backend.monitor, body.to_email, 'TimeBeacon Test Email', 'This test confirms that TimeBeacon can submit email using the saved Email configuration.')
        except Exception:
            raise HTTPException(502, 'Email could not be sent. Check the saved hostname, port, encryption and credentials.')
        return {'message': 'Test email accepted by the mail server. Check the recipient inbox.'}
